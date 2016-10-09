"""
Provide a test() function that can be called from package __init__.
"""

import os
import re


class TestError(Exception):
    pass


def test(*args, **kwargs):
    """
    Run py.test unit tests for the calling package with specified
    ``args`` and ``kwargs``.

    This temporarily changes to the directory above the installed package
    directory and effectively runs ``py.test <packagename> <args> <kwargs>``.

    If the kwarg ``raise_exception=True`` is provided then any test
    failures will result in an exception being raised.  This can be
    used to make shell-level failure.

    :returns: number of test failures
    """
    # Local imports so that imports only get done when really needed.
    import os
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

    calling_frame_record = inspect.stack()[1]  # Only works for stack-based Python
    calling_func_file = calling_frame_record[1]

    if package_from_dir:
        # In this case it is assumed that the module which called this function is
        # located in a directory named by the package that is to be tested.  I.e.
        # chandra_aca/test.py.  However, this is NOT the actual package directory
        # so we have to import the package to get its parent directory.
        import importlib
        package = os.path.basename(os.path.dirname(os.path.abspath(calling_func_file)))
        print('package', package)
        module = importlib.import_module(package)
        calling_func_file = module.__file__
        calling_func_module = module.__name__
    else:
        # In this case the module that called this function is the package __init__.py.
        # We get the module directly without doing another import.
        calling_frame = calling_frame_record[0]
        calling_func_name = calling_frame_record[3]
        calling_func_module = calling_frame.f_globals[calling_func_name].__module__

    pkg_names = calling_func_module.split('.')
    pkg_paths = [os.path.dirname(calling_func_file)] + ['..'] * len(pkg_names)
    pkg_dir = os.path.join(*pkg_names)

    with chdir(os.path.join(*pkg_paths)):
        n_fail = pytest.main([pkg_dir] + list(args), **kwargs)

    if n_fail and raise_exception:
        raise TestError('got {} failure(s)'.format(n_fail))

    return n_fail


def make_regress_files(regress_files, out_dir=None, regress_dir=None, clean=None):
    def get_options():
        """Get options.
        Output: optionns"""
        from optparse import OptionParser
        parser = OptionParser()
        parser.set_defaults()
        parser.add_option("--out-dir")
        parser.add_option("--regress-dir")
        return parser.parse_args()[0]

    if clean is None:
        clean = {}

    if out_dir is None or regress_dir is None:
        # This is being run via a custom script that is called by run_tests with
        # --out-dir and --regress-dir options specified.
        opt = get_options()
        out_dir = opt.out_dir
        regress_dir = opt.regress_dir

    # Make the top-level directory where files go
    if not os.path.exists(regress_dir):
        os.makedirs(regress_dir)

    for regress_file in regress_files:
        with open(os.path.join(out_dir, regress_file), 'r') as fh:
            lines = fh.readlines()

        if regress_file in clean:
            for sub_in, sub_out in clean[regress_file]:
                lines = [re.sub(sub_in, sub_out, x) for x in lines]

        # Might need to make output directory since regress_file can
        # contain directory prefix.
        regress_path = os.path.join(regress_dir, regress_file)
        regress_path_dir = os.path.dirname(regress_path)
        if not os.path.exists(regress_path_dir):
            os.makedirs(regress_path_dir)

        with open(regress_path, 'w') as fh:
            fh.writelines(lines)
