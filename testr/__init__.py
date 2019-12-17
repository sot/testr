# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Testing framework for Ska runtime environment.
"""

import ska_helpers

__version__ = ska_helpers.get_version(__package__)

from .runner import test, testr  # noqa
