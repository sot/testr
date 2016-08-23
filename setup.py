from setuptools import setup

from ska_test import __version__

try:
    from ska_test import cmdclass
except ImportError:
    cmdclass = {}


setup(name='ska_test',
      author='Tom Aldcroft',
      description='Testing framework for Ska runtime environment',
      author_email='taldcroft@cfa.harvard.edu',
      version=__version__,
      zip_safe=False,
      packages=['ska_test'],
      tests_require=['pytest'],
      cmdclass=cmdclass,
      )
