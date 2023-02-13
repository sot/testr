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
        import pytest
        import shlex

        args = []
        if self.args:
            args += shlex.split(self.args)
        errno = pytest.main(args)
        sys.exit(errno)


# setup() cmdclass keyword for testing with py.test
cmdclass = {'test': PyTest}
