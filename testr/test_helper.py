# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Provide helper functions that are useful for unit testing.
"""

import sys
import os
from pathlib import Path
import socket
import platform

__all__ = ['has_paths', 'has_dirs', 'has_sybase', 'on_head_network', 'is_32_bit',
           'is_windows', 'is_mac', 'is_linux']


def has_paths(*paths):
    """All of the ``paths`` exist

    Input path(s) can contain ~ (home dir) or environment variables like $SKA or
    ${SKA}.
    """
    for path in paths:
        path = os.path.expanduser(os.path.expandvars(path))
        path = Path(path)
        if not path.exists():
            return False
    return True


def has_dirs(*paths):
    """All of the ``paths`` exist and each is a directory

    Input path(s) can contain ~ (home dir) or environment variables like $SKA or
    ${SKA}.
    """
    for path in paths:
        path = os.path.expanduser(os.path.expandvars(path))
        path = Path(path)
        if not (path.exists() and path.is_dir()):
            return False
    return True


def is_windows():
    return platform.system() == 'Windows'


def is_mac():
    return platform.system() == 'Darwin'


def is_linux():
    return platform.system() == 'Linux'


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


def is_32_bit():
    return sys.maxsize <= 2 ** 32


def has_internet(host="8.8.8.8", port=53, timeout=3):
    """Return True if internet is available by trying to reach ``host``.

    Adapted from https://stackoverflow.com/questions/3764291
    
    Parameters
    ----------
    host : str
        Host IP to reach (default=8.8.8.8 (google-public-dns-a.google.com))
    port : int
        Port to use (default=53)
    timeout : int, float
        Timeout in seconds (default=3)

    Returns
    -------
    has_internet : bool
    """
    import socket
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False
