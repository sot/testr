from __future__ import print_function, absolute_import, division

import re
from glob import glob
from fnmatch import fnmatch
import sys
import os
import shutil

import Ska.File
from Ska.Shell import bash, ShellError, Spawn
from pyyaks.logger import get_logger
from astropy.table import Table

opt = None
logger = None


def get_options():
    """
    Get options.

    :returns: options (argparse object)
    """
    from optparse import OptionParser
    parser = OptionParser()
    parser.set_defaults()

    parser.add_option("--packages-dir",
                      default="packages",
                      help="Directory containing package tests",
                      )
    parser.add_option("--outputs-dir",
                      default="outputs",
                      help="Root directory containing all output package test runs",
                      )
    parser.add_option("--outputs-subdir",
                      help="Directory containing per-run output package test runs",
                      )
    parser.add_option("--regress-dir",
                      default="regress",
                      help="Directory containing per-run regression files",
                      )
    parser.add_option("--include",
                      default='*',
                      help=("Include tests that match comma-separated "
                            "list of glob pattern(s) (default='*')"),
                      )
    parser.add_option("--exclude",
                      default='*_long',
                      help=("Exclude tests that match comma-separated "
                            "list of glob pattern(s) (default='*_long')"),
                      )
    parser.add_option("--collect-only",
                      action="store_true",
                      help=('Collect tests but do not run'),
                      )
    parser.add_option("--packages-repo",
                      default='https://github.com/sot',
                      help=("Base URL for package git repos"),
                      )
    parser.add_option("--overwrite",
                      action="store_true",
                      help=('Overwrite existing outputs directory instead of deleting'),
                      )
    return parser.parse_args()[0]


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
    include = any(fnmatch(path, x.strip() + '*') for x in opt.include.split(','))
    if opt.exclude:
        exclude = any(fnmatch(path, x.strip() + '*') for x in opt.exclude.split(','))
    else:
        exclude = False
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

        in_dir = os.path.join(opt.packages_dir, package)
        out_dir = os.path.abspath(os.path.join(opt.outputs_dir, opt.outputs_subdir, package))
        regress_dir = os.path.abspath(os.path.join(opt.regress_dir, opt.outputs_subdir, package))

        with Ska.File.chdir(in_dir):
            test_files = sorted(glob('test_*')) + sorted(glob('post_*'))

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
                        'package': package}

                tests[package].append(test)

    return tests


def run_tests(package, tests):
    # Collect test scripts in package and find the ones that are included
    in_dir = os.path.join(opt.packages_dir, package)

    include_tests = [test for test in tests if test['status'] != '----']
    skipping = '' if include_tests else ': skipping - no included tests'
    box_output(['package {}{}'.format(package, skipping)])

    # If no included tests then print message and bail out
    if not include_tests:
        logger.info('')
        return []

    # Copy all files for package tests.
    out_dir = os.path.join(opt.outputs_dir, opt.outputs_subdir, package)
    if not opt.overwrite and os.path.exists(out_dir):
        logger.info('Removing existing output dir {}'.format(out_dir))
        shutil.rmtree(out_dir)

    logger.info('Copying input tests {} to output dir {}'.format(in_dir, out_dir))
    Spawn().run(['rsync', '-a', in_dir + '/', out_dir, '--exclude=*~'])

    # Now run the tests and collect test status
    with Ska.File.chdir(out_dir):
        for test in include_tests:
            # Make the test keys available in the environment
            env = {'TESTR_{}'.format(str(key).upper()): val
                   for key, val in test.items()}

            interpreter = test['interpreter']

            logger.info('Running {} {} script'.format(interpreter, test['file']))
            logfile = Tee(test['file'] + '.log')

            # Set up the right command for bash.  In the case of a bash script the
            # cmd is the actual bash lines as a single string.  In this way each one
            # gets echoed and run so that an intermediate failure is caught.  For
            # no interpreter assume the file is executable.
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

    box_output(['{} Test Summary'.format(package)] +
               ['{:20s} {}'.format(test['file'], test['status']) for test in tests])


def get_results_table(tests):
    results = []
    for package in sorted(tests):
        for test in tests[package]:
            results.append((package, test['file'], test['status']))
    out = Table(rows=results, names=('Package', 'Script', 'Status'))
    return out


def make_test_dir():
    test_dir = os.path.join(opt.outputs_dir, opt.outputs_subdir)
    if os.path.exists(test_dir):
        print('WARNING: reusing existing output directory {}'.format(test_dir))
        # TODO: maybe make this a raw_input confirmation in production.  Note:
        # logger doesn't exist yet since it logs into test_dir.
    else:
        os.makedirs(test_dir)

    # Make a symlink 'last' to the most recent directory
    with Ska.File.chdir(opt.outputs_dir):
        if os.path.exists('last'):
            os.unlink('last')
        os.symlink(opt.outputs_subdir, 'last')

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

    # Make the top-level directory where files go
    if not os.path.exists(regress_dir):
        os.makedirs(regress_dir)

    for regress_file in regress_files:
        with open(os.path.join(out_dir, regress_file), 'r') as fh:
            lines = fh.readlines()

        if regress_file in clean:
            for sub_in, sub_out in clean[regress_file]:
                lines = [re.sub(sub_in, sub_out, x) for x in lines]

        # Might need to make output directory since regress_file can
        # contain directory prefix.
        regress_path = os.path.join(regress_dir, regress_file)
        regress_path_dir = os.path.dirname(regress_path)
        if not os.path.exists(regress_path_dir):
            os.makedirs(regress_path_dir)

        with open(regress_path, 'w') as fh:
            fh.writelines(lines)


def main():
    global opt, logger
    opt = get_options()

    # Set up directories
    if opt.outputs_subdir is None:
        ska_version = bash('ska_version')[0]
        opt.outputs_subdir = ska_version

    test_dir = make_test_dir()

    # TODO: back-version existing test.log file to test.log.N where N is the first
    # available number.
    logger = get_logger(name='run_tests', filename=os.path.join(test_dir, 'test.log'))

    tests = collect_tests()  # dict of (list of tests) keyed by package

    if not opt.collect_only:
        for package in sorted(tests):
            run_tests(package, tests[package])  # updates tests[package] in place

    results = get_results_table(tests)
    box_output(results.pformat())
