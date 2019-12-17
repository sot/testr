# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup

try:
    from testr import cmdclass
except ImportError:
    cmdclass = {}


setup(name='testr',
      author='Tom Aldcroft',
      description='Framework for unit and integration testing of packages',
      author_email='taldcroft@cfa.harvard.edu',
      url='http://cxc.harvard.edu/mta/ASPECT/tool_doc/testr',
      use_scm_version=True,
      setup_requires=['setuptools_scm', 'setuptools_scm_git_archive'],
      zip_safe=False,
      packages=['testr'],
      entry_points={'console_scripts': ['run_testr=testr.packages:main']},
      tests_require=['pytest'],
      cmdclass=cmdclass,
      )
