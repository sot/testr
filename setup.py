from setuptools import setup

from testr import __version__

try:
    from testr import cmdclass
except ImportError:
    cmdclass = {}


setup(name='testr',
      author='Tom Aldcroft',
      description='Framework for unit and integration testing of packages',
      author_email='taldcroft@cfa.harvard.edu',
      version=__version__,
      zip_safe=False,
      packages=['testr'],
      entry_points={'console_scripts': ['run_testr=testr.packages:main']},
      tests_require=['pytest'],
      cmdclass=cmdclass,
      )
 
