# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import print_function, absolute_import, division

import re
from glob import glob
from fnmatch import fnmatch
import sys
import os
import shutil
import subprocess
from pathlib import Path
from xml.dom import minidom
import collections
import json
import datetime
import platform
import yaml


import Ska.File
from Ska.Shell import bash, ShellError
from pyyaks.logger import get_logger
from astropy.table import Table
from cxotime import CxoTime

from . import test_helper
from . import __version__

opt = None
logger = None


def get_options():
    """
    Get options.

    :returns: options (argparse object)
    """
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument("--test-spec",
                        help="Test include/exclude specification (default=None)",
                        )
    parser.add_argument("--root",
                        default=".",
                        help="Directory containing standard testr configuration",
                        )
    parser.add_argument("--outputs-dir",
                        default="outputs",
                        help="Root directory containing all output package test runs."
                             " Absolute, or relative to CWD",
                        )
    parser.add_argument('--include',
                        action='append',
                        default=[],
                        dest='includes',
                        help=("Include tests that match glob pattern"),
                        )
    parser.add_argument('--exclude',
                        action='append',
                        default=[],
                        dest='excludes',
                        help=("Exclude tests that match glob pattern"),
                        )
    parser.add_argument("--collect-only",
                        action="store_true",
                        help=('Collect tests but do not run'),
                        )
    parser.add_argument("--packages-repo",
                        default='https://github.com/sot',
                        help=("Base URL for package git repos"),
                        )
    parser.add_argument('--version', action='version', version=__version__)
    parser.set_defaults()

    return parser.parse_args()


class Tee(object):
    def __init__(self, name, mode='w'):
        self.fh = open(name, mode)

    def __del__(self):
        self.fh.close()

    def write(self, data):
        self.fh.write(data)
        sys.stdout.write(data)

    def flush(self):
        self.fh.flush()
        sys.stdout.flush()

    def fileno(self):
        return sys.stdout.fileno()


def box_output(lines, min_width=40):
    width = max(min_width, 8 + max([len(x) for x in lines]))
    logger.info('*' * width)
    fmt = '*** {:' + str(width - 8) + 's} ***'
    for line in lines:
        logger.info(fmt.format(line))
    logger.info('*' * width)
    logger.info('')


def include_test_file(package, test_file):
    path = os.path.join(package, test_file)
    include = any(fnmatch(path, x.strip() + '*') for x in opt.includes)
    exclude = any(fnmatch(path, x.strip() + '*') for x in opt.excludes)

    return include and not exclude


def collect_tests():
    """
    Collect tests
    """
    with Ska.File.chdir(opt.packages_dir):
        packages = [x for x in os.listdir('.') if os.path.isdir(x)]

    tests = {}
    for package in packages:
        tests[package] = []

        try:
            import ska_helpers
            version = ska_helpers.get_version(package)
        except Exception:
            version = 'unknown'
        in_dir = opt.packages_dir / package
        out_dir = (opt.log_dir / package).absolute()
        regress_dir = (opt.regress_dir / package).absolute()

        with Ska.File.chdir(in_dir):
            test_files = sorted(glob('test_*')) + sorted(glob('post_*'))
            test_files = [x for x in test_files if x.endswith('.py') or x.endswith('.sh')]

            for test_file in test_files:
                status = 'not run' if include_test_file(package, test_file) else '----'

                if test_file.endswith('.py'):
                    interpreter = 'python'
                elif test_file.endswith('.sh'):
                    interpreter = 'bash'
                else:
                    interpreter = None

                test = {'file': test_file,
                        'status': status,
                        'interpreter': interpreter,
                        'out_dir': out_dir,
                        'regress_dir': regress_dir,
                        'packages_repo': opt.packages_repo,
                        'package': package,
                        'package_version': version}

                tests[package].append(test)

    return tests


def get_skip_tests():
    """Read skip.yml file that specifies tests in this directory to skip.

    The file should be in the form::

        fileglob1:
          check_func: test_helper_function_name
          check_args: ['arg1', 'arg2']  # optional args
          reason: Reason for skipping  # optional reason
        fileglob2:
          check_func: NOT test_helper_function_name  # Negate with "not" or "NOT"
          reason: Reason for skipping

    The ``test_helper_function_name`` is the name of a function in the
    ``test_helper`` module to run. E.g. ``check: is_windows`` will run
    ``test_helper.is_windows()``.
    """
    skip_file = Path('skip.yml')
    skip_tests = yaml.safe_load(open(skip_file)) if skip_file.exists() else {}

    return skip_tests


def check_skip_test(test, skip_tests):
    """Check if the current ``test`` should be skipped.

    Returns string reason if test should be skipped, otherwise None.
    """
    for file_glob, spec in skip_tests.items():
        if fnmatch(test['file'], file_glob):
            check_func = spec['check_func'].split()[-1]
            try:
                check_func = getattr(test_helper, check_func)
            except AttributeError:
                raise ValueError(f'{check_func} must be a function in testr.test_helper')

            negate = re.match(r'not\s', spec['check_func'], re.IGNORECASE)
            check_args = spec.get('check_args', [])
            skip_check = check_func(*check_args)
            if negate:
                skip_check = not skip_check
            if skip_check:
                arg_str = ', '.join(repr(arg) for arg in check_args)
                reason = spec['check_func'] + f'({arg_str})'
                return spec.get('reason', reason)

    # No checks matched
    return None


def run_tests(package, tests):
    # Collect test scripts in package and find the ones that are included
    in_dir = opt.packages_dir / package

    include_tests = [test for test in tests if test['status'] != '----']
    skipping = '' if include_tests else ': skipping - no included tests'
    box_output(['package {}{}'.format(package, skipping)])

    # If no included tests then print message and bail out
    if not include_tests:
        logger.info('')
        return []

    # Copy all files for package tests.
    out_dir = opt.log_dir / package
    if out_dir.exists():
        logger.info('Removing existing output dir {}'.format(out_dir))
        shutil.rmtree(out_dir)

    logger.info(f'Copying input tests {in_dir} to output dir {out_dir}')
    shutil.copytree(in_dir, out_dir)

    # Now run the tests and collect test status
    with Ska.File.chdir(out_dir):
        skip_tests = get_skip_tests()

        for test in include_tests:
            if skip_reason := check_skip_test(test, skip_tests):
                logger.info(f'Skipping {test["file"]}: {skip_reason}')
                test['status'] = 'skip'
                continue

            # Make the test keys available in the environment
            env = {'TESTR_{}'.format(str(key).upper()): str(val)
                   for key, val in test.items()}

            interpreter = test['interpreter']

            logger.info('Running {} {} script'.format(interpreter, test['file']))
            logfile = Tee(Path(test['file']).with_suffix('.log'))

            # Set up the right command for bash.  In the case of a bash script the
            # cmd is the actual bash lines as a single string.  In this way each one
            # gets echoed and run so that an intermediate failure is caught.  For
            # no interpreter assume the file is executable.
            test['t_start'] = datetime.datetime.now().strftime('%Y:%m:%dT%H:%M:%S')

            if test_helper.is_windows():
                # Need full environment in the subprocess run
                env.update(os.environ)

                cmds = [sys.executable, test['file']]
                try:
                    sub = subprocess.run(cmds, env=env, capture_output=True)
                    logfile.write(sub.stdout.decode('ascii')
                                  + sub.stderr.decode('ascii'))
                except Exception:
                    test['status'] = 'FAIL'
                else:
                    test['status'] = 'pass' if sub.returncode == 0 else 'FAIL'
            else:
                if interpreter == 'bash':
                    with open(test['file'], 'r') as fh:
                        cmd = fh.read()
                elif interpreter is None:
                    cmd = './' + test['file']
                else:
                    cmd = interpreter + ' ' + test['file']

                try:
                    bash(cmd, logfile=logfile, env=env)
                except ShellError:
                    # Test process returned a non-zero status => Fail
                    test['status'] = 'FAIL'
                else:
                    test['status'] = 'pass'

            test['t_stop'] = datetime.datetime.now().strftime('%Y:%m:%dT%H:%M:%S')

    box_output(['{} Test Summary'.format(package)] +
               ['{:20s} {}'.format(test['file'], test['status']) for test in tests])


def get_results_table(tests):
    results = []
    for package in sorted(tests):
        for test in tests[package]:
            results.append((package, test['file'], test['status']))
    if len(results) == 0:
        return
    out = Table(rows=results, names=('Package', 'Script', 'Status'))
    return out


def _parse_xml_testsuite(node):
    attributes = collections.defaultdict(lambda: None)
    attributes.update({k: node.getAttribute(k) for k in node.attributes.keys()})

    for k in ['system-err', 'system-out']:
        if node.getElementsByTagName('system-err'):
            child = node.getElementsByTagName('system-err')[0]
            text_nodes = [t.wholeText for t in child.childNodes
                          if t.nodeType in [node.TEXT_NODE, node.CDATA_SECTION_NODE]]
            attributes[k] = ''.join(text_nodes)

    test_suite = dict(
        test_cases=[],
        name=attributes['name'],
        hostname=attributes['hostname'],
        id=attributes['id'],
        package=attributes['package'],
        timestamp=attributes['timestamp'],
        stdout=attributes['system-out'],
        stderr=attributes['system-err'],
        # properties =
        file=attributes['file'],
        log=None,
        url=None,
    )
    test_suite = {k: v for k, v in test_suite.items() if v is not None}
    for child in node.getElementsByTagName('testcase'):
        test_suite['test_cases'].append(_parse_xml_testcase(child))
    return test_suite


def _parse_xml_testcase(node):
    attributes = collections.defaultdict(lambda: None)
    attributes.update({k: node.getAttribute(k) for k in node.attributes.keys()})

    for k in ['system-err', 'system-out']:
        if node.getElementsByTagName('system-err'):
            child = node.getElementsByTagName('system-err')[0]
            text_nodes = [t.wholeText for t in child.childNodes
                          if t.nodeType in [node.TEXT_NODE, node.CDATA_SECTION_NODE]]
            attributes[k] = ''.join(text_nodes)

    test_case = dict(
        name=attributes['name'],
        classname=attributes['classname'],
        elapsed_sec=attributes['elapsed_sec'],
        timestamp=attributes['timestamp'],
        stdout=attributes['system-out'],
        stderr=attributes['system-err'],
        file=attributes['file'],
        line=attributes['line'],
        log=None,
        url=None,
    )
    test_case = {k: v for k, v in test_case.items() if v is not None}

    def node_text(n):
        content = [t.wholeText for t in n.childNodes
                   if t.nodeType in [node.TEXT_NODE, node.CDATA_SECTION_NODE]]
        return ''.join(content)

    test_status = {'failure': 'fail', 'error': 'error', 'skipped': 'skipped'}
    for k in ['failure', 'error', 'skipped']:
        if node.getElementsByTagName(k):
            err = node.getElementsByTagName(k)[0]
            test_case[k] = {
                'message': err.getAttribute('message') if err.hasAttribute('message') else None,
                'output': node_text(err)
            }
    test_case['status'] = 'pass'
    for k in ['failure', 'error', 'skipped']:
        if k in test_case:
            test_case['status'] = test_status[k]
            break

    return test_case


def _parse_xml(filename):
    dom = minidom.parse(filename)
    test_suites = [_parse_xml_testsuite(s) for s in
                   dom.getElementsByTagName('testsuite')]
    return test_suites


def _rel_path_if_descendant(path, root):
    """
    Take a path and return either an absolute path or a path relative to root.
    If the path does not exists, it returns None.

    :param path:
    :param root:
    :return:
    """
    real_root = os.path.realpath(root)
    real_path = os.path.realpath(path)
    if real_path.startswith(real_root + os.path.sep) or real_path == real_root:
        p = os.path.relpath(real_path, real_root)
    else:
        p = path
    # The following line exploits a feature of os.path.join: If a component is an absolute path, all
    # previous components are thrown away and joining continues from the absolute path component.
    # In other words: if p is absolute, real_root is ignored.
    if os.path.exists(os.path.join(real_root, p)):
        return str(p)


def write_log(tests, include_stdout=False):
    all_test_suites = []
    outputs_subdir = opt.log_dir

    uname = platform.uname()
    architecture, _ = platform.architecture()
    sys_info = {
        'system': uname.system,
        'architecture': architecture,
        'hostname': uname.node,
        'platform': platform.platform(True, True)
    }

    for package in sorted(tests):
        top_testsuite = None
        package_test_suites = []
        for test in tests[package]:
            test_props = {k: (test[k] if k in test else None)
                          for k in ['package', 'package_version', 't_start', 't_stop']}
            for k in ['regress_dir', 'out_dir']:
                test_props[k] = _rel_path_if_descendant(test[k], outputs_subdir)

            stdout = None
            test_file = _rel_path_if_descendant(test['out_dir'] / test['file'],
                                                outputs_subdir)
            log_file = _rel_path_if_descendant((test['out_dir'] / test['file']).with_suffix('.log'),
                                               outputs_subdir)
            if include_stdout and log_file:
                with open(log_file) as f:
                    stdout = f.read()

            xml_file = _rel_path_if_descendant((test['out_dir'] / test['file']).with_suffix('.xml'),
                                               outputs_subdir)
            if xml_file and (outputs_subdir / xml_file).exists():
                properties = sys_info.copy()
                properties.update(test_props)
                test_suites = _parse_xml(outputs_subdir / xml_file)
                for ts in test_suites:
                    ts['properties'] = properties
                    ts.update({
                        'name': f"{package}-{ts['name']}",
                        'log': log_file,
                        'hostname': properties['hostname'],
                        'timestamp': properties['t_start'],
                        'package': properties['package'],
                        'file': test_file,
                    })
                if stdout:
                    # If len(test_suites) > 1, stdout is in the first suite
                    test_suites[0]['stdout'] = stdout
                package_test_suites += test_suites
            else:
                if top_testsuite is None:
                    properties = sys_info.copy()
                    properties.update(test_props)
                    top_testsuite = dict(
                        name=f"{package}-tests",
                        package=package,
                        test_cases=[],
                        timestamp=test_props['t_start'],
                        properties=properties
                    )
                test_status = {'pass': 'pass', 'fail': 'fail',
                               '----': 'skipped', 'skip': 'skipped'}
                test_case = dict(
                    name=test['file'],
                    file=str(test_file),
                    timestamp=test_props['t_start'],
                    log=str(log_file),
                    status=test_status[test['status'].lower()]
                )
                if stdout:
                    test_case['stdout'] = stdout
                if test['status'].lower() == 'fail':
                    test_case['failure'] = {
                        'message': f'{test["file"]} failed',
                        'output': None
                    }
                elif test['status'].lower() in ('----', 'skip'):
                    test_case['skipped'] = {
                        'message': f'{test["file"]} skipped',
                        'output': None
                    }
                top_testsuite['test_cases'].append(test_case)

        if len(package_test_suites) == 1:
            package_test_suites[0]['test_cases'] += top_testsuite['test_cases']
        else:
            package_test_suites.append(top_testsuite)

        all_test_suites += package_test_suites

    try:
        ska_version = subprocess.check_output(['ska_version']).decode().strip()
    except FileNotFoundError:
        ska_version = 'None'
    test_suites = {
        'run_info': {
            'date': datetime.datetime.now().strftime('%Y:%m:%dT%H:%M:%S'),
            'argv': sys.argv,
            'ska_version': ska_version,
            'test_spec': opt.test_spec.name if opt.test_spec else 'None'
        }
    }
    if all_test_suites:
        t_stops = [ts['properties']['t_stop'] for ts in all_test_suites
                   if ts['properties']['t_start'] is not None]
        t_starts = [ts['properties']['t_start'] for ts in all_test_suites
                    if ts['properties']['t_start'] is not None]
        test_suites['run_info']['t_stop'] = min(t_stops) if t_stops else None
        test_suites['run_info']['t_start'] = min(t_starts) if t_starts else None
        test_suites['run_info'].update({
            k: sorted(set([ts['properties'][k] for ts in all_test_suites]))
            for k in ['architecture', 'hostname', 'system', 'platform']
        })
        test_suites['test_suites'] = all_test_suites
    outfile = outputs_subdir / 'all_tests.json'
    with open(outfile, 'w') as f:
        json.dump(test_suites, f, indent=2)


def make_test_dir():
    test_dir = opt.log_dir
    if test_dir.exists():
        print('WARNING: reusing existing output directory {}\n'.format(test_dir))
        # TODO: maybe make this a raw_input confirmation in production.  Note:
        # logger doesn't exist yet since it logs into test_dir.
    else:
        os.makedirs(test_dir)

    # Make a symlink 'last' to the most recent directory
    with Ska.File.chdir(opt.log_dir.parent):
        if os.path.lexists('last'):
            os.unlink('last')
        os.symlink(opt.log_dir.name, 'last')

    return test_dir


def make_regress_files(regress_files, out_dir=None, regress_dir=None, clean=None):
    """
    Copy ``regress_files`` from ``out_dir`` to ``regress_dir``, maintaining the
    relative directory structure.

    The ``clean`` parameter specifies a dict of rules for "cleaning" files so that
    uninteresting diffs are eliminated.  Each dict key is the path name (corresponding
    to ``regress_files``) and the value is a 2-tuple of (match_regex, substitution_string).

    :param regress_files: list of relative path names
    :param out_dir: top-level directory for source of files
    :param regress_dir: top-level directory where files are copied
    :param clean: dict of regex substitution rules

    :returns: None
    """
    if clean is None:
        clean = {}

    # Fall back on environment variables that are defined during package testing.
    if out_dir is None:
        out_dir = os.environ.get('TESTR_OUT_DIR')
    if regress_dir is None:
        regress_dir = os.environ.get('TESTR_REGRESS_DIR')

    # make sure these are paths
    regress_dir = Path(regress_dir)
    out_dir = Path(out_dir)

    # Make the top-level directory where files go
    if not regress_dir.exists():
        os.makedirs(regress_dir)

    for regress_file in regress_files:
        with open(out_dir / regress_file, 'r') as fh:
            lines = fh.readlines()

        if regress_file in clean:
            for sub_in, sub_out in clean[regress_file]:
                lines = [re.sub(sub_in, sub_out, x) for x in lines]

        # Might need to make output directory since regress_file can
        # contain directory prefix.
        regress_path = regress_dir / regress_file
        regress_path_dir = regress_path.parent
        if not regress_path_dir.exists():
            os.makedirs(regress_path_dir)

        with open(regress_path, 'w') as fh:
            fh.writelines(lines)


def check_files(filename, checks, allows=None, out_dir=None):
    """
    Search for ``checks`` regexes in the output ``filename`` (which may be a glob).

    The ``allows`` parameter specifies a list of regexes that are known/accepted check
    failures and can be ignored even if the line matches a check.  The default bash prompt
    Bash-HH:MM:SS> is always allowed, so no lines that are part of the source bash
    commanding will be flagged.

    If any matches are found then a ValueError exception is raised.

    :param filename: relative path name (glob allowed)
    :param checks: list of regexes to try matching
    :param allows: list of regexes that override checks

    :returns: None
    """
    if allows is None:
        allows = []

    allows.append(r'^Bash-\d\d')

    if out_dir is None:
        out_dir = os.environ.get('TESTR_OUT_DIR')

    matches = []
    for filename in glob(filename):
        with open(Path(out_dir) / filename, 'r') as fh:
            lines = fh.readlines()

        for check in checks:
            for index, line in enumerate(lines):
                if re.search(check, line, re.IGNORECASE):
                    if not any(re.search(allow, line, re.IGNORECASE) for allow in allows):
                        matches.append('{!r} matched at {}:{} :: {}'
                                       .format(check, filename, index, line.strip()))

    if matches:
        raise ValueError('Found matches in check_files:\n{}'.format('\n'.join(matches)))


def get_version_id():
    hostname = platform.uname().node
    cmds = ['python', Path(sys.prefix, 'bin', 'ska_version')]
    version = subprocess.check_output(cmds).decode('ascii').strip()
    time = CxoTime.now()
    time.format = 'isot'
    time.precision = 0
    version_id = f'{platform.system()}_{time}_{version}_{hostname}'
    # Colon in file name is bad for Windows and also fails cheta long regress test
    version_id = version_id.replace(':', '-')
    return version_id


def process_opt():
    """
    Process options and make various inplace replacements for downstream
    convenience.
    """
    # Set up directories
    opt.root = Path(opt.root).absolute()
    opt.outputs_dir = Path(opt.outputs_dir)
    opt.packages_dir = opt.root / 'packages'
    outputs_subdir = get_version_id()
    opt.log_dir = (opt.outputs_dir / 'logs' / outputs_subdir).absolute()
    opt.regress_dir = (opt.outputs_dir / 'regress' / outputs_subdir).absolute()

    if opt.test_spec:
        opt.test_spec = Path(opt.test_spec)
        if not opt.test_spec.exists():
            if (opt.root / opt.test_spec).exists():
                opt.test_spec = opt.root / opt.test_spec
            else:
                get_logger().error(f'test_spec file {opt.test_spec} does not exist')
                sys.exit(1)
        # This puts regression outputs into a separate sub-directory
        # and reads additional test file include/excludes.
        opt.regress_dir = opt.regress_dir / opt.test_spec.name

        with open('{}'.format(opt.test_spec), 'r') as fh:
            specs = (line.strip() for line in fh)
            specs = [spec for spec in specs if spec and not spec.startswith('#')]

        for spec in specs:
            if spec:
                if spec.startswith('-'):
                    opt.excludes.append(spec[1:])
                else:
                    opt.includes.append(spec)

    # If opt.includes is not explicitly initialized after processing test_spec (which is
    # optional) then use ['*'] to include all tests
    opt.includes = opt.includes or ['*']


def main():
    global opt, logger
    opt = get_options()
    process_opt()

    test_dir = make_test_dir()

    # TODO: back-version existing test.log file to test.log.N where N is the first
    # available number.
    logger = get_logger(name='run_tests', filename=(test_dir / 'test.log'))

    tests = collect_tests()  # dict of (list of tests) keyed by package

    if not opt.collect_only:
        for package in sorted(tests):
            run_tests(package, tests[package])  # updates tests[package] in place

    results = get_results_table(tests)
    if results:
        box_output(results.pformat(max_lines=-1, max_width=-1))

    write_log(tests)


if __name__ == '__main__':
    main()
