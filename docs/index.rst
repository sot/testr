testr
===========

The ``testr`` package provides a framework for unit, regression, and integration
testing of a set of packages within a production runtime environment.  The
primary component of ``testr`` is lightweight testing script and file structure
definition that simple but can support complex testing as needed.  The secondary
component is a couple of helper functions that make it easier to define and run
Python package unit tests.  This includes a ``test_helper`` module with some
helper functions.

.. toctree::
   :maxdepth: 2

Package testing: unit, regression, integration
----------------------------------------------

The use case here is a production environment where one has the capability (and indeed
requirement) to build and test within a testing environment prior to deploying to
production.  The starting assumption is that the ``testr`` package is installed in the
test environment and that all new or updated packages have also been installed to the
environment.

Package testing and definition in the ``testr`` framework is done entirely by convention
rather than configuration.  What this means is that there is a certain directory structure
and file naming convention that must be followed and which controls how testing is done.
There are no configuration files at all.

The following definitions are provided to give a general feel for the different
styles of testing supported here.  The definitions are by no means
rigorous and there is certainly overlap.

**Unit** testing refers to dedicated tests of individual package functionality
that are conceptually independent of the environment and result in an immediate
pass/fail for each test.

**Regression** testing refers to tests that typically produce output files which are then
compared against reference outputs.  The ``testr`` package contains functions
to facilitate this process by munging the outputs to remove uninteresting
differences (like time stamps or the user who ran a script).

**Integration** testing refers to ensuring that the packages work within an
updated environment.  This overlaps with unit and regression testing, but
is linked to potential cross-package issues.  A key example is updating
a core package that may produce unexpected results or issue deprecation
warnings downstream that are not desirable.

Basic structure
^^^^^^^^^^^^^^^

When ``testr`` is installed it creates a console script ``run_testr`` that can
be run from the command line in your environment testing directory.  This
directory can be anywhere, but as we will see the ideal setup is to have this
be a git / GitHub repository.

A full-featured example of the environment testing setup is in the `ska_testr
<https://github.com/sot/ska_testr>`_ GitHub repository.  A more minimal example would be::

  get_version_id            # Executable script or program
  packages/
    py_package/             # py_package is a Python package
      helper_script.py      # Helper script called by test_regress.sh
      test_unit.py          # Run built-in unit tests for my
      test_regress.sh       # Additional regression tests for integration testing
      post_regress.py       # Copy regression output files to the regress/ directory
      post_check_logs.py    # Check logs for "warning" or "error"

    other_package/          # Some package without unit tests
      test_regress_long.sh  # Long-running regression test that isn't run every time
      post_regress_long.py  # Copy regression output files to the regress/ directory

get_version_id
""""""""""""""

The ``get_version_id`` file must be an executable script or program that produces
a single line of output corresponding to a unique version identifier for the
environment.  This is used to organize the outputs by version and later to
compare the regression outputs.  In the Ska runtime environment this script
produces a version identifier like ``0.18-r609-0d91665``.


Packages
""""""""

The ``packages`` directory must contain sub-directories corresponding to
each package being explicitly tested.  For Python packages the directory
name should be the same as the importable package name.  This allows the
simple unit testing idiom (shown later) to infer the package name to import.

Test scripts
""""""""""""

Test scripts are located within the package sub-directory.  The key concept to understand
here is that the tests consist entirely of scripts or executable files that have the
following properties:

- File name begins with ``test_``.
- File is either a Python script (``test_*.py``), Bash script (``test_*.sh``),
  or an executable file.
- When run the test file returns a successful exit status (0) for PASS and
  a non-successful exit status (not 0) for FAIL.
- Tests are run in alphabetical order.

Those are the only rules, so the testing can run the gamut from simple
to arbitrarily complex.

Post-processing scripts
"""""""""""""""""""""""

After the tests are run then any post-processing scripts in the package directory will be
run (again in alphabetical order).  These are exactly the same as test files except:

- File name begins with ``post_``.
- Post-processing scripts will be run *after* all the test scripts are done.

A key point is that the post-processing scripts can generate failures. For
instance a common task is checking the output log files for unexpected warnings
that do not generate a failure.

Environment variables
"""""""""""""""""""""

Several environment variables are defined prior to spawning jobs that run the
test or post-processing scripts.

=====================  =====================================================
Name                   Definition
=====================  =====================================================
TESTR_REGRESS_DIR      Regression output directory for this package
TESTR_INTERPRETER      Interpreter that will be used (python, bash, or None)
TESTR_PACKAGE          Package name
TESTR_PACKAGES_REPO    URL root for cloning package repo
TESTR_FILE             Script file name
TESTR_OUT_DIR          Testing output directory for this package
=====================  =====================================================

Filename conventions
""""""""""""""""""""

There are no *required* conventions beyond the previously mentioned rules, but
following some simple conventions will make life easier and more organized.  This
is especially true because of the way that tests are selected based on the
file name and the ``--include`` and ``--exclude`` arguments of ``run_testr``.
The table below shows keywords that are included in the file name, separated
by underscores.

============== ===========================================================
Keywords       Meaning
============== ===========================================================
unit           Run built-in unit tests
regress        Regression tests that compare to reference outputs
git            Test that requires cloning a git repo to run
long           Long-running test that does not need to be run every time
============== ===========================================================

Standard filenames and examples of the keywords are shown in the example
directory structure above.

Running the tests
^^^^^^^^^^^^^^^^^

The ``run_testr`` command has the following options::

  $ run_testr --help
  usage: run_testr [-h] [--test-spec TEST_SPEC] [--root ROOT]
                   [--packages-dir PACKAGES_DIR] [--outputs-dir OUTPUTS_DIR]
                   [--outputs-subdir OUTPUTS_SUBDIR] [--regress-dir REGRESS_DIR]
                   [--include INCLUDES] [--exclude EXCLUDES] [--collect-only]
                   [--packages-repo PACKAGES_REPO] [--overwrite]

  optional arguments:
    -h, --help            show this help message and exit
    --test-spec TEST_SPEC
                          Test include/exclude specification (default=None)
    --root ROOT           Directory containing standard testr configuration
    --packages-dir PACKAGES_DIR
                          Directory containing package tests. Absolute, or
                          relative to --root
    --outputs-dir OUTPUTS_DIR
                          Root directory containing all output package test
                          runs. Absolute, or relative to CWD
    --outputs-subdir OUTPUTS_SUBDIR
                          Directory containing per-run output package test runs.
                          Relative to --outputs-dir
    --regress-dir REGRESS_DIR
                          Directory containing per-run regression files.
                          Relative to CWD
    --include INCLUDES    Include tests that match glob pattern
    --exclude EXCLUDES    Exclude tests that match glob pattern
    --collect-only        Collect tests but do not run
    --packages-repo PACKAGES_REPO
                          Base URL for package git repos
    --overwrite           Overwrite existing outputs directory instead of
                          deleting
  usage: run_testr [-h] [--test-spec TEST_SPEC_FILE] [--packages-dir PACKAGES_DIR]
                   [--outputs-dir OUTPUTS_DIR] [--outputs-subdir OUTPUTS_SUBDIR]
                   [--regress-dir REGRESS_DIR] [--include INCLUDES]
                   [--exclude EXCLUDES] [--collect-only]
                   [--packages-repo PACKAGES_REPO] [--overwrite]


For the example directory structure, doing ``run_testr`` (with no custom options) would
run the tests, reporting test status for each test and then finish with a summary of test
status like so::

  *************************************************
  ***    Package           Script        Status ***
  *** ------------- -------------------- ------ ***
  *** other_package test_regress_long.sh   pass ***
  *** other_package post_regress_long.py   pass ***
  ***    py_package      test_regress.sh   pass ***
  ***    py_package         test_unit.py   pass ***
  ***    py_package   post_check_logs.py   pass ***
  ***    py_package      post_regress.py   pass ***
  *************************************************

The working directory would contain the following new sub-directories.  The first step in
processing is to copy the test and post-process scripts from ``packages`` into
``outputs/<version_id>``, where ``<version_id>`` is the output of ``get_version_id``.  The
scripts are then run from that directory, so they are free to write outputs directly into
the current directory or any sub-directories therein.  ::

  # Testing and post-process scripts and outputs
  outputs/
    0.18-r609-0d91665/
      test.log              # Master log file of test processing and results
      py_package/
        helper_script.py
        test_unit.py
        test_unit.py.log    # Log file from running test_unit.py
        test_regress.sh
        test_regress.sh.log # Log file
        post_regress.py
        post_regress.py.log # Log file
        post_check_logs.py
        post_check_logs.py.log
        out.dat             # Example data file from test_regress.sh
        index.html          # Example web page from test_regress.sh
      other_package/
        test_regress_long.sh
        test_regress_long.sh.log
        post_regress_long.py
        post_regress_long.py.log
        big_data.dat        # More data

  # Regression outputs, copied from outputs/ by post_regress* scripts
  regress/
    0.18-r609-0d91665/
      py_package/
        out.dat             # Example data file from test_regress.sh
        index.html          # Example web page from test_regress.sh
      other_package/
        big_data.dat        # More data

Selecting tests
^^^^^^^^^^^^^^^

The ``--include`` and ``--exclude`` options can be used to select specific tests and
post-process scripts.  The default is to include all files.

The values for both options are a comma-separated list of shell file "glob" patterns
that are used to match files.  The selection filtering first finds all files that
match the ``--include`` argument (which defaults to ``*``), and then removes any
files that match the ``--exclude`` argument (which defaults to ``None``).

The glob patterns are compared to the full filename that includes the package name
and test name, for instance ``py_package/test_regress.sh``.

For practical convenience, any specified values (e.g. ``py_package``) automatically
have a ``*`` appended.  Some examples::

  $ run_testr --include=py_package  # py_package (but also py_package_2)
  $ run_testr --include=py_package/  # py_package only
  $ run_testr --exclude=py_package/  # exclude py_package but run all others
  $ run_testr --exclude='*_long'    # exclude long tests
  $ run_testr --exclude='*_long,*_unit' # exclude long and unit tests

Comparing regression outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this example the 0.18-r609-0d91665 regress outputs might correspond to
the current production installation.  Then suppose you create a test
environment with version id ``0.19-r610-1b65555`` and run the full
test suite.  Then you can do::

  $ cd regress
  $ diff -r 0.18-r609-0d91665/ 0.19-r610-1b65555/
  ...

A key point is that effort should be made to clean the regression outputs
to strip them of uninteresting diffs like a date or the user that ran the
tests.  See the `post_regress.py`_ example for more discussion on that.

One option from here is to copy the regress outputs into a git-versioned repo
in a new branch and then use GitHub to do comparisons.

Test specification files
^^^^^^^^^^^^^^^^^^^^^^^^

One might like to maintain a set of unit and regression tests in a single
testing repository but to run somewhat different combinations of those tests in
different circumstances.  For instance one testing environment might not have
the necessary resources to run all tests.  The tests themselves might manage
this (i.e. pytest "skip") but it may be simpler and more explicit to
manage these lists of tests directly.

The ``--test-spec`` command line option provides a way to do this.  If you provide
an option like ``--test-spec=HEAD`` then the following happens:

- A file in the current directory named ``HEAD`` is opened and read:

  - It must contain a list of include / exclude specifications like those for
    the ``-include`` and ``-exclude`` options.
  - The exclude specifications are preceded by a minus sign (``-``).
  - Blank lines or those starting with ``#`` are ignored.

- The test specification file include and exclude files are appended to any
  provided on the command line.

- The regression outputs are put into a sub-directory ``HEAD`` within the
  ``regress`` directory.

Example test specification file::

  # Includes
  acisfp_check
  dpa_check

  # Excludes
  -*_long*


File recipes
^^^^^^^^^^^^

Here we show some example testing files taken from `ska_testr
<https://github.com/sot/ska_testr>`_ GitHub repository in order to
illustrate some useful recipes or idioms.

test_unit.py
""""""""""""

Python packages that have built-in (inline) unit tests (see `Python testing helpers`_)
can be tested with the following::

  import testr
  testr.testr()

This uses pytest to run the included tests for the package.  By default
it provides flags to run in verbose mode with all test code output copied
to the console.  This allows any stray warnings to be emitted.

You can do the same thing without using the ``testr.testr()`` function as follows.
The important thing is to raise an exception if there were test failures::

  import xija
  n_fail = xija.test('-v', '-s', '-k not test_minusz')
  if n_fail > 0:
      raise ValueError(str(n_fail) + ' test failures')

test_unit_git.sh
""""""""""""""""
Python packages that do not have inline unit tests or for other reasons
require the source repo for unit testing can use the following recipe::

  /usr/bin/git clone ${TESTR_PACKAGES_REPO}/${TESTR_PACKAGE}
  cd ${TESTR_PACKAGE}
  git checkout master
  py.test -v -s

This illustrates some environment variables that are always defined when
running test code.

post_regress.py
"""""""""""""""
Here is an example from the Ska `dpa_check test
<https://github.com/sot/ska_testr/tree/master/packages/dpa_check>`_ that copies a few
key outputs into the ``regress`` directory after stripping out the
user name and run time.

::

  from testr.packages import make_regress_files

  regress_files = ['out/index.rst',
                   'out/run.dat',
                   'out/states.dat',
                   'out/temperatures.dat']

  clean = {'out/index.rst': [(r'^Run time.*', '')],
           'out/run.dat': [(r'#.*py run at.*', '')]}

  make_regress_files(regress_files, clean=clean)


post_check_logs.py
""""""""""""""""""
Here is an example again from the Ska `dpa_check test
<https://github.com/sot/ska_testr/tree/master/packages/dpa_check>`_ that checks the
test processing log files for any occurrences of ``warning`` or ``error``.
In this case there are a couple of lines where this is expected, so those
matches are ignored.  Any other matches will raise an exception and signal
a FAIL for this package::

  from testr.packages import check_files

  check_files('test_*.log',
              checks=['warning', 'error'],
              allows=['99% quantile value of', 'in output at out'])

test_regress_long.sh
""""""""""""""""""""

This is an example that is not really a recipe but a demonstration of
doing a complex regression test that requires some setup and uses
several scripts to regenerate database tables from scratch.  It then
uses a helper script those to write a subset of database contents
in a clean ASCII format for regression comparisons.  This is in the
`kadi <https://github.com/sot/ska_testr/tree/master/packages/kadi>`_ package.
::

  # Get three launcher scripts manage.py update_events and update_cmds
  /usr/bin/git clone ${TESTR_PACKAGES_REPO}/kadi

  # Copy some scripts to the current directory
  cd kadi
  cp manage.py update_events update_cmds ltt_bads.dat ../
  cd ..
  rm -rf kadi

  export KADI=$PWD
  ./manage.py syncdb --noinput

  START='2015:001'
  STOP='2015:030'

  ./update_events --start=$START --stop=$STOP
  ./update_cmds --start=$START --stop=$STOP

  # Write event and commands data using test database
  ./write_events_cmds.py --start=$START --stop=$START --data-root=events_cmds

Another complicated example is in the
`Ska.engarchive <https://github.com/sot/ska_testr/tree/master/packages/Ska.engarchive>`_
package.  This one is slightly different because it generates new database
values and then immediately compares with the current production database.


Summary Logs
^^^^^^^^^^^^

Testr produces a summary log which includes all tests run. It parses the logs produced by pytest, and tests are grouped
in suites following the test hierarchy. Tests that do not use pytest are grouped in a test suite at the top level.
The log is written in JSON format and looks something like the following:

.. code-block:: JSON

    {
      "test_suite": {
        "name": "Quaternion-tests",
        "package": "Quaternion",
        "test_cases": [
          {
            "name": "post_check_logs.py",
            "file": "Quaternion/post_check_logs.py",
            "timestamp": "2020:06:16T09:43:13",
            "log": "Quaternion/post_check_logs.py.log",
            "status": "fail",
            "failure": {
              "message": "post_check_logs.py failed",
              "output": null
            }
          }
        ],
        "timestamp": "2020:06:16T09:43:13",
        "properties": {
          "system": "Darwin",
          "architecture": "64bit",
          "hostname": "saos-MacBook-Pro.local",
          "platform": "Darwin-19.5.0",
          "package": "Quaternion",
          "package_version": "3.5.2.dev9+g7ee8b10.d20200616",
          "t_start": "2020:06:16T09:43:13",
          "t_stop": "2020:06:16T09:43:14",
          "regress_dir": null,
          "out_dir": "Quaternion"
        }
      },
      "test_suites": [
        {
          "test_cases": [
            {
              "name": "test_shape",
              "classname": "Quaternion.tests.test_all",
              "file": "Quaternion/tests/test_all.py",
              "line": "43",
              "status": "pass"
            },
            {
              "name": "test_init_exceptions",
              "classname": "Quaternion.tests.test_all",
              "file": "Quaternion/tests/test_all.py",
              "line": "50",
              "failure": {
                "message": "Exception: Unexpected exception here",
                "output": "def test_init_exceptions():\n>       raise Exception('Unexpected exception here')\nE       Exception: Unexpected exception here\n\nQuaternion/tests/test_all.py:52: Exception"
              },
              "status": "fail"
            },
            {
              "name": "test_from_q",
              "classname": "Quaternion.tests.test_all",
              "file": "Quaternion/tests/test_all.py",
              "line": "83",
              "skipped": {
                "message": "no way of currently testing this",
                "output": "Quaternion/tests/test_all.py:83: <py._xmlgen.raw object at 0x7f9ca044fb38>"
              },
              "status": "skipped"
            }
          ],
          "name": "Quaternion-pytest",
          "properties": {
            "system": "Darwin",
            "architecture": "64bit",
            "hostname": "saos-MacBook-Pro.local",
            "platform": "Darwin-19.5.0",
            "package": "Quaternion",
            "package_version": "3.5.2.dev9+g7ee8b10.d20200616",
            "t_start": "2020:06:16T09:43:11",
            "t_stop": "2020:06:16T09:43:13",
            "regress_dir": null,
            "out_dir": "Quaternion"
          },
          "log": "Quaternion/test_unit.py.log",
          "hostname": "saos-MacBook-Pro.local",
          "timestamp": "2020:06:16T09:43:11",
          "package": "Quaternion",
          "file": "Quaternion/test_unit.py"
        }
      ]
    }


Python testing helpers
-----------------------

The modules ``testr.runner`` and ``testr.setup_helper`` provide the infrastructure
to enable easy and uniform running of pytest test functions in two ways:

- By importing the package (locally or installed) and doing ``<package>.test(*args, **kwargs)``
- Within a local development repo using ``python setup.py test --args='arg1 kwarg2=val2'`` where
  ``arg1`` and ``kwarg2`` are valid pytest arguments.

``__init__.py``
^^^^^^^^^^^^^^^^

Typical usage within the package ``__init__.py`` file::

  def test(*args, **kwargs):
      '''
      Run py.test unit tests.
      '''
      import testr
      return testr.test(*args, **kwargs)

This will run any tests that included as a ``test`` sub-package in the package
distribution.  The following package layout shows an example of such inlined tests::

  setup.py   # your setuptools Python package metadata
  mypkg/
      __init__.py
      appmodule.py
      ...
      tests/
          test_app.py
          ...

A key advantage of providing inline tests is that they can be run post-install
in the production environment, providing positive confirmation that the actual
installed package is working as expected.  See the next section for an example
``setup.py`` file which shows including this inline test sub-package.


``setup.py``
^^^^^^^^^^^^

Typical usage in ``setup.py``::

  from setuptools import setup

  try:
      from testr.setup_helper import cmdclass
  except ImportError:
      cmdclass = {}

  setup(name='my_package',
        packages=['my_package', 'my_package.tests'],
        tests_require=['pytest'],
        cmdclass=cmdclass,
        )


API
---

testr.runner
^^^^^^^^^^^^^^^

.. automodule:: testr.runner
   :members:

testr.setup_helper
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: testr.setup_helper
   :members:

testr.test_helper
^^^^^^^^^^^^^^^^^

.. automodule:: testr.test_helper
   :members:
