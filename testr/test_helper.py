# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Provide helper functions that are useful for unit testing.
"""

import os
from pathlib import Path
import socket

__all__ = ['has_sybase', 'on_head_network']


def has_sybase():
    """
    Return True if the system apparently can run Sybase queries from Python.

    In detail, this is True if the SYBASE and SYBASE_OCS env variables are set
    and the correct Python shared object library exists on the system.
    """
    try:
        path = Path(os.environ['SYBASE'],
                    os.environ['SYBASE_OCS'],
                    'python', 'python34_64r', 'lib', 'sybpydb.so')
    except KeyError:
        # If either env var not defined then there is no Sybase
        out = False
    else:
        out = path.exists()

    return out


def on_head_network():
    """
    Return True if the system is apparently on the HEAD network.

    This looks for subnets 52 (e.g. fido, lato) and 184 (kadi) on 131.142.xxx.
    """
    try:
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
    except Exception:
        # If we cannot get a host_ip by this method then definitely not on HEAD.
        out = False
    else:
        ips = host_ip.split('.')
        out = (ips[0] == '131' and
               ips[1] == '142' and
               ips[2] in ('52', '184'))  # 60 Garden, CDP respectively
    return out
