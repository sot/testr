ska_test
===========

The ska_test package provides a Testing framework for the Ska runtime environment.

.. toctree::
   :maxdepth: 2

Testing helpers
---------------

The modules ``ska_test.runner`` and ``ska_test.setup_helper`` provide the infrastructure
to enable easy and uniform running of pytest test functions in two ways:

- By importing the package (locally or installed) and doing ``<package>.test(*args, **kwargs)``
- Within a local repo using ``python setup.py test --args='arg1 kwarg2=val2'`` where
  ``arg1`` and ``kwarg2`` are valid pytest arguments.

``__init__.py``
^^^^^^^^^^^^^^^^

Typical usage within the package ``__init__.py`` file::

  def test(*args, **kwargs):
      '''
      Run py.test unit tests.
      '''
      import ska_test
      return ska_test.test(*args, **kwargs)


``setup.py``
^^^^^^^^^^^^

Typical usage in ``setup.py``::

  from setuptools import setup

  try:
      from ska_test.setup_helper import cmdclass
  except ImportError:
      cmdclass = {}

  setup(name='my_package',
        packages=['my_package'],
        tests_require=['pytest'],
        cmdclass=cmdclass,
        )


API
---

ska_test.runner
^^^^^^^^^^^^^^^

.. automodule:: ska_test.runner
   :members:

ska_test.setup_helper
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: ska_test.setup_helper
   :members:
