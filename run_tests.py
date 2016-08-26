#! /usr/bin/env python

from __future__ import print_function, absolute_import, division

from glob import glob
from fnmatch import fnmatch
import sys
import os
import shutil

import Ska.File
from Chandra.Time import DateTime
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
                      default="packages_dir",
                      help="Directory containing package tests",
                      )
    parser.add_option("--outputs-dir",
                      default="outputs_dir",
                      help="Root directory containing all output package test runs",
                      )
    parser.add_option("--outputs-subdir",
                      help="Directory containing per-run output package test runs",
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


def get_packages():
    with Ska.File.chdir(opt.packages_dir):
        packages = [x for x in os.listdir('.') if os.path.isdir(x)]
    return packages


def include_test_file(package, test_file):
    path = os.path.join(package, test_file)
    include = any(fnmatch(path, x.strip()) for x in opt.include.split(','))
    exclude = any(fnmatch(path, x.strip()) for x in opt.exclude.split(','))
    return include and not exclude


def run_tests(package):
    # Collect test scripts in package and find the ones that are included
    in_dir = os.path.join(opt.packages_dir, package)
    with Ska.File.chdir(in_dir):
        test_files = glob('test*.py') + glob('test*.sh')
        include_test_files = [x for x in test_files if include_test_file(package, x)]

    skipping = '' if include_test_files else ': skipping - no included tests'
    box_output(['package {}{}'.format(package, skipping)])

    # If no included tests then print message and bail out
    if not include_test_files:
        logger.info('')
        return []

    # Make the output directory
    out_dir = os.path.join(opt.outputs_dir, opt.outputs_subdir, package)
    if os.path.exists(out_dir):
        raise IOError('output dir {} already exists'.format(out_dir))

    # Copy all files.  Excluded test scripts will be removed later.
    logger.info('Copying input tests {} to output dir {}'.format(in_dir, out_dir))
    shutil.copytree(in_dir, out_dir, symlinks=True, ignore=shutil.ignore_patterns('*~'))

    # Make a symlink 'last' to the most recent directory
    with Ska.File.chdir(opt.outputs_dir):
        if os.path.exists('last'):
            os.unlink('last')
        os.symlink(opt.outputs_subdir, 'last')

    # Now run the tests and collect test status
    statuses = []
    with Ska.File.chdir(out_dir):
        for test_file in test_files:
            if test_file not in include_test_files:
                os.unlink(test_file)
                statuses.append((test_file, 'skip'))
                continue

            interpreter = 'python' if test_file.endswith('.py') else 'bash'

            logger.info('Running {} {} script'.format(interpreter, test_file))
            logfile = Tee(test_file + '.log')

            try:
                bash('{} {}'.format(interpreter, test_file), logfile=logfile)
            except ShellError:
                # Test process returned a non-zero status => Fail
                statuses.append((test_file, 'fail'))
            else:
                statuses.append((test_file, 'success'))

    box_output(['{} Test Summary'.format(package)] +
               ['{:20s} {}'.format(test_file, status) for test_file, status in statuses])

    return statuses


def main():
    global opt
    opt = get_options()

    # Set up directories
    if opt.outputs_subdir is None:
        ska_version = bash('ska_version')[0]
        opt.outputs_subdir = '{}-{}'.format(DateTime().fits[:19], ska_version)

    os.makedirs(os.path.join(opt.outputs_dir, opt.outputs_subdir))

    results = []
    packages = get_packages()
    for package in sorted(packages):
        statuses = run_tests(package)
        for test_file, status in statuses:
            results.append((package, test_file, status))

    results = Table(rows=results, names=('Package', 'Script', 'Status'))
    box_output(results.pformat())

if __name__ == '__main__':
    main()
