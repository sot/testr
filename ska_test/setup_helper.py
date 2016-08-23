import sys
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.args = []

    def run_tests(self):
        # Import here because outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.args)
        sys.exit(errno)

# setup() cmdclass keyword for testing with py.test
cmdclass = {'test': PyTest}
