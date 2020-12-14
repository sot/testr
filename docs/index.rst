testr
===========

The ``testr`` package provides lightweight functions for unit testing. It also
includes a ``test_helper`` module with functions that help with configuration
issues like whether the host operating system is Windows or if the machine is
on the HEAD network.

.. toctree::
   :maxdepth: 2

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
