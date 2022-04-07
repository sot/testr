
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Provide a test() function that can be called from package __init__.
"""

import os


# Pytest args for main() to ignore several warnings that show up regularly in
# testing but can be ignored.
PYTEST_IGNORE_WARNINGS = (
    # See https://github.com/numpy/numpy/issues/11788 for why the numpy.ufunc
    # warning is apparently OK.
    '-Wignore:numpy.ufunc size changed:RuntimeWarning',

    # Shows up in upstream packages including ipyparallel
    '-Wignore:the imp module is deprecated in favour of importlib:DeprecationWarning',

    # Shows up in setuptools_scm
    '-Wignore:parse functions are required to provide a named:PendingDeprecationWarning',

    # Shows up in sparkles from importing bleach
    '-Wignore:Using or importing the ABCs:DeprecationWarning',

    # Shows up in several places from importing PyTables
    '-Wignore:`np.object` is a deprecated alias for the builtin `object`',

    # This warning comes about when running with the latest version MarksupSafe (>=2.0) but an old
    # version of Jinja2<3.0.
    "-Wignore: 'soft_unicode' has been renamed to 'soft_str'",

    # annie/telem.py:18
    #  (which is a list-or-tuple of lists-or-tuples-or ndarrays with different lengths or shapes)
    # is deprecated. If you meant to do this, you must specify 'dtype=object' when creating the
    # ndarray.
    "-Wignore:  Creating an ndarray from ragged nested sequences",
)


class TestError(Exception):
    pass


def testr(*args, **kwargs):
    r"""
    Run py.test unit tests for the calling package.  This just calls the ``test()``
    function but includes defaults that are more appropriate for integrated package
    testing using run_testr.

    :param \*args: positional args to pass to pytest
    :param raise_exception: test failures raise an exception (default=True)
    :param package_from_dir: set package name from parent directory name (default=True)
    :param verbose: run pytest in verbose (-v) mode (default=True)
    :param show_output: run pytest in show output (-s) mode (default=True)
    :param \*\*kwargs: additional keyword args to pass to pytest

    :returns: number of test failures
    """
    for kwarg in ('raise_exception', 'package_from_dir', 'verbose', 'show_output'):
        kwargs.setdefault(kwarg, True)

    # test() function looks up the calling stack to find the calling package name.
    # It will be two levels up.
    kwargs['stack_level'] = 2

    return test(*args, **kwargs)


def test(*args, **kwargs):
    r"""
    Run py.test unit tests for the calling package with specified
    ``args`` and ``kwargs``.

    This temporarily changes to the directory above the installed package
    directory and effectively runs ``py.test <packagename> <args> <kwargs>``.

    If the kwarg ``raise_exception=True`` is provided then any test
    failures will result in an exception being raised.  This can be
    used to make a shell-level failure.

    :param \*args: positional args to pass to pytest
    :param raise_exception: test failures raise an exception (default=False)
    :param package_from_dir: set package name from parent directory name (default=False)
    :param verbose: run pytest in verbose (-v) mode (default=False)
    :param show_output: run pytest in show output (-s) mode (default=False)
    :param \*\*kwargs: additional keyword args to pass to pytest

    :returns: number of test failures
    """
    # Local imports so that imports only get done when really needed.
    import os
    import sys
    import subprocess
    import inspect
    import pytest
    import contextlib

    # Copied from Ska.File to reduce import footprint and limit to only standard
    # modules.
    @contextlib.contextmanager
    def chdir(dirname=None):
        """
        Context manager to run block within `dirname` directory.  The current
        directory is restored even if the block raises an exception.

        :param dirname: Directory name
        """
        curdir = os.getcwd()
        try:
            if dirname is not None:
                os.chdir(dirname)
            yield
        finally:
            os.chdir(curdir)

    raise_exception = kwargs.pop('raise_exception', False)
    package_from_dir = kwargs.pop('package_from_dir', False)
    get_version = kwargs.pop('get_version', False)

    with_coverage = (os.environ.get('TESTR_COVERAGE', '').lower().strip() in ['true'])
    coverage_config = os.environ.get('TESTR_COVERAGE_CONFIG', 'no-coverage-config')
    if with_coverage and not os.path.exists(coverage_config):
        if raise_exception:
            raise TestError(f'Coverage config is not found {coverage_config}')
        return

    if 'TESTR_PYTEST_ARGS' in os.environ:
        args = args + tuple(os.environ['TESTR_PYTEST_ARGS'].split())

    arg_names = [a.split('=')[0] for a in args]
    if kwargs.pop('verbose', False) and '-v' not in args and '-q' not in arg_names:
        args = args + ('-v',)
    if kwargs.pop('show_output', False) and '-s' not in args and '--capture' not in arg_names:
        args = args + ('-s',)

    args = args + PYTEST_IGNORE_WARNINGS

    if 'TESTR_OUT_DIR' in os.environ and 'TESTR_FILE' in os.environ:
        report_file = os.path.join(os.environ['TESTR_OUT_DIR'], f"{os.environ['TESTR_FILE']}.xml")
        args += (f'--junit-xml={report_file}',)
        args += ('-o', 'junit_family=xunit2')

    # Disable caching of test results to prevent users trying to write into
    # flight directory if tests fail running on installed package.
    args = args + ('-p', 'no:cacheprovider')

    if 'TESTR_ALLOW_HYPOTHESIS' not in os.environ:
        # Disable autoload of hypothesis plugin which causes warnings due to
        # trying to write to .hypothesis dir from the cwd of test runner. See
        # slack #aspect-team "falling back to an in-memory database for this
        # session" for more info.
        args += ('-p', 'no:hypothesispytest')  # current name for disabling
        args += ('-p', 'no:hypothesis')  # possible future name

    stack_level = kwargs.pop('stack_level', 1)
    calling_frame_record = inspect.stack()[stack_level]  # Only works for stack-based Python
    calling_func_file = calling_frame_record[1]

    if package_from_dir:
        # In this case it is assumed that the module which called this function is
        # located in a directory named by the package that is to be tested.  I.e.
        # chandra_aca/test.py.  However, this is NOT the actual package directory
        # so we have to import the package to get its parent directory.
        import importlib
        package = os.path.basename(os.path.dirname(os.path.abspath(calling_func_file)))
        module = importlib.import_module(package)
        calling_func_file = module.__file__
        calling_func_module = module.__name__
    else:
        # In this case the module that called this function is the package __init__.py.
        # We get the module directly without doing another import.
        calling_frame = calling_frame_record[0]
        calling_frame_filename = calling_frame_record[1]
        calling_func_name = calling_frame_record[3]
        calling_func_module = calling_frame.f_globals[calling_func_name].__module__
        if get_version:
            return get_full_version(calling_frame.f_globals,
                                    calling_frame_filename)

    pkg_names = calling_func_module.split('.')
    pkg_paths = [os.path.dirname(calling_func_file)] + ['..'] * len(pkg_names)
    pkg_dir = os.path.join(*pkg_names)

    with chdir(os.path.join(*pkg_paths)):
        if with_coverage:
            coverage_file = os.path.join(
                os.environ['TESTR_OUT_DIR'],
                '.coverage'
            )
            cmd = [
                'coverage', 'run',
                f'--rcfile={coverage_config}',
                f'--data-file={coverage_file}',
                '-m', 'pytest', pkg_dir
            ] + list(args) + [f'{k}={v}' for k, v in kwargs]
            process = subprocess.run(cmd, stdout=sys.stdout, stderr=subprocess.STDOUT)
            rc = process.returncode
        else:
            rc = pytest.main([pkg_dir] + list(args), **kwargs)

    if rc and raise_exception:
        raise TestError('Failed')

    return bool(rc)


def get_full_version(calling_frame_globals, calling_frame_filename):
    """
    Return a full version which includes git info if the module was imported
    from the git repo source directory.
    """
    release_version = calling_frame_globals.get('__version__', 'unknown')

    try:
        from subprocess import Popen, PIPE
        filedir = os.path.dirname(os.path.abspath(calling_frame_filename))

        p = Popen(['git', 'rev-list', 'HEAD'],
                  cwd=filedir,
                  stdout=PIPE, stderr=PIPE, stdin=PIPE)
        stdout, stderr = p.communicate()
        stdout = stdout.decode('ascii')

        if p.returncode == 0:
            revs = stdout.split('\n')
            out = release_version + '-r{}-{}'.format(len(revs), revs[0][:7])
        else:
            out = release_version
    except Exception:
        out = release_version

    return out
