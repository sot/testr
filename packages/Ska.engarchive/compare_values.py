#!/usr/bin/env python

"""
Compare locally generated eng archive data store with flight (/proj/sot/ska)
values.  This is assumed to be run as part of eng_archive regression testing
and requires that the local data store is in the current working directory
as ``data``.
"""

import os

import numpy as np
from Ska.engarchive import fetch
import argparse


def get_options(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--start",
                        help="Start time")
    parser.add_argument("--stop",
                        help="Stop time")
    parser.add_argument("--flight-root",
                        default='/proj/sot/ska',
                        help="Flight root directory (default=/proj/sot/ska")
    parser.add_argument("--content",
                        action='append',
                        help="Content type to process")
    return parser.parse_args(args)


def compare_msid(msid, stat):
    """
    Compare ``stat`` data for ``msid``: locally generated vs. flight in /proj/sot/ska.
    """
    # Start with the local version which is generated over a small slice of time
    # (a few days).
    fetch.msid_files.basedir = os.getcwd()
    local = fetch.Msid(msid, opt.start, opt.stop, stat=stat)

    # Now use definitive Ska flight data as reference for comparison.
    # Fetch over an interval which is just slightly longer.
    tstart = local.times[0] - 0.0001
    tstop = local.times[-1] + 0.0001
    fetch.msid_files.basedir = os.path.join(opt.flight_root, 'data', 'eng_archive')
    flight = fetch.Msid(msid, tstart, tstop, stat=stat)

    fails = []

    if len(local) != len(flight):
        fails.append(' length local:{} flight{}'.format(len(local), len(flight)))
    else:
        for colname in local.colnames:
            local_value = getattr(local, colname)
            flight_value = getattr(flight, colname)

            # Do not explicitly test bads, this is done implicitly by virtue of
            # the bad filtering already applied.
            if colname is 'bads':
                continue

            # Extend the colname for reporting purposes
            if stat:
                colname = colname + '[{}]'.format(stat)

            # Check dtype equality
            if local_value.dtype != flight_value.dtype:
                fails.append('.{} dtype local:{} flight{}'
                             .format(colname, local.dtype, flight.dtype))
                continue

            # Define comparison operator based on type
            if local_value.dtype.kind in ('i', 'u', 'S', 'U', 'b'):  # int, str, unicode, bool
                compare = lambda x, y: np.all(x == y)
            elif local_value.dtype.kind == 'f':  # float
                compare = np.allclose
            else:
                fails.append('.{} unexpected dtype {}'.format(colname, local_value.dtype))
                continue

            if not compare(local_value, flight_value):
                fails.append('.{} local != flight'.format(colname))

    fails = [msid + fail for fail in fails]
    return fails


opt = get_options()

any_fail = False

for content in opt.content:
    # Get all the MSIDs for this content type
    msids = [msid for msid, msid_content in fetch.content.items()
             if content == msid_content]

    for msid in msids:
        print('{} {}'.format(content, msid))
        for stat in (None, '5min', 'daily'):
            fails = compare_msid(msid, stat)
            if fails:
                print('\n'.join(fails))
                any_fail = True

if any_fail:
    raise RuntimeError('some comparisons failed')
