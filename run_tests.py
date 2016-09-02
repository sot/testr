#! /usr/bin/env python

from __future__ import print_function, absolute_import, division

from glob import glob
from fnmatch import fnmatch
import sys
import os
import shutil

import Ska.File
from Ska.Shell import bash, ShellError
from pyyaks.logger import get_logger
from astropy.table import Table

opt = None
logger = get_logger(name='run_tests')


def get_options():
    """Get options.
    Output: optionns"""
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
    exclude = any(fnmatch(path, x.strip() + '*') for x in opt.exclude.split(','))
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
            test_files = glob('test*.py') + glob('test*.sh') + glob('copy_regress_files.py')
            for test_file in test_files:
                status = 'not run' if include_test_file(package, test_file) else 'skip'
                interpreter = 'python' if test_file.endswith('.py') else 'bash'
                test = {'file': test_file,
                        'status': status,
                        'interpreter': interpreter,
                        'args': []}

                if test_file == 'copy_regress_files.py':
                    test['args'] = ['--out-dir={}'.format(out_dir),
                                    '--regress-dir={}'.format(regress_dir)]

                tests[package].append(test)

    return tests


def run_tests(package, tests):
    # Collect test scripts in package and find the ones that are included
    in_dir = os.path.join(opt.packages_dir, package)

    include_tests = [test for test in tests if test['status'] != 'skip']
    skipping = '' if include_tests else ': skipping - no included tests'
    box_output(['package {}{}'.format(package, skipping)])

    # If no included tests then print message and bail out
    if not include_tests:
        logger.info('')
        return []

    # Copy all files for package tests.
    out_dir = os.path.join(opt.outputs_dir, opt.outputs_subdir, package)
    logger.info('Copying input tests {} to output dir {}'.format(in_dir, out_dir))
    shutil.copytree(in_dir, out_dir, symlinks=True, ignore=shutil.ignore_patterns('*~'))

    # Now run the tests and collect test status
    with Ska.File.chdir(out_dir):
        for test in include_tests:
            interpreter = test['interpreter']

            logger.info('Running {} {} script'.format(interpreter, test['file']))
            logfile = Tee(test['file'] + '.log')

            try:
                cmd = ' '.join([interpreter, test['file']] + test['args'])
                bash(cmd, logfile=logfile)
            except ShellError:
                # Test process returned a non-zero status => Fail
                test['status'] = 'fail'
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
        answer = raw_input('Removing existing output directory {} (y/N)?'.format(test_dir))
        if answer.lower() == 'y':
            logger.info('Removing existing output directory {}'.format(test_dir))
            shutil.rmtree(test_dir)

    if os.path.exists(test_dir):
        raise IOError('output dir {} already exists'.format(test_dir))

    os.makedirs(test_dir)

    # Make a symlink 'last' to the most recent directory
    with Ska.File.chdir(opt.outputs_dir):
        if os.path.exists('last'):
            os.unlink('last')
        os.symlink(opt.outputs_subdir, 'last')


def main():
    global opt
    opt = get_options()

    # Set up directories
    if opt.outputs_subdir is None:
        ska_version = bash('ska_version')[0]
        opt.outputs_subdir = ska_version

    tests = collect_tests()  # dict of (list of tests) keyed by package

    if not opt.collect_only:
        make_test_dir()
        for package in sorted(tests):
            run_tests(package, tests[package])  # updates tests[package] in place

    results = get_results_table(tests)
    box_output(results.pformat())

if __name__ == '__main__':
    main()