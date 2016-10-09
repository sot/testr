testr
===========

The testr package provides a Testing framework for the Ska runtime environment.

.. toctree::
   :maxdepth: 2

Testing helpers
---------------

The modules ``testr.runner`` and ``testr.setup_helper`` provide the infrastructure
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
      import testr
      return testr.test(*args, **kwargs)


``setup.py``
^^^^^^^^^^^^

Typical usage in ``setup.py``::

  from setuptools import setup

  try:
      from testr.setup_helper import cmdclass
  except ImportError:
      cmdclass = {}

  setup(name='my_package',
        packages=['my_package'],
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
