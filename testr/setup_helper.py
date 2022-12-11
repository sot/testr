# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Define a test runner command class suitable for use in ``setup.py`` so
that ``python setup.py test`` runs tests via pytest.
"""

import sys

from setuptools.command.test import test as TestCommand

__all__ = ['cmdclass', 'PyTest']


class PyTest(TestCommand):
    """
    Test runner command class suitable for use in ``setup.py`` so
    that ``python setup.py test`` runs tests via pytest.
    """
    user_options = [('args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.args = []

    def run_tests(self):
        # Import here because outside the eggs aren't loaded
        import shlex

        import pytest

        from .runner import PYTEST_IGNORE_WARNINGS

        args = list(PYTEST_IGNORE_WARNINGS)
        if self.args:
            args += shlex.split(self.args)
        errno = pytest.main(args)
        sys.exit(errno)


# setup() cmdclass keyword for testing with py.test
cmdclass = {'test': PyTest}


def duplicate_package_info(vals, name_in, name_out):
    """
    Duplicate a list or dict of values inplace, replacing ``name_in`` with ``name_out``.

    Normally used in setup.py for making a namespace package that copies a flat one.
    For an example see setup.py in the ska_sun or Ska.Sun repo.

    :param vals: list or dict of values
    :param name_in: string to replace at start of each value
    :param name_out: output string
    """
    import re

    for name in list(vals):
        new_name = re.sub(f"^{name_in}", name_out, name)
        if isinstance(vals, dict):
            vals[new_name] = vals[name]
        else:
            vals.append(new_name)


