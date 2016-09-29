#!/usr/bin/env python

from __future__ import print_function

import os
import argparse

import kadi.events
import kadi.cmds
import kadi.paths
from Chandra.Time import DateTime


def get_opt(args=None):
    parser = argparse.ArgumentParser(description='Update the events database')
    parser.add_argument("--stop",
                        help="Processing stop date")
    parser.add_argument("--start",
                        help=("Processing start date"))
    parser.add_argument("--data-root",
                        help="Root data directory")
    opt = parser.parse_args(args)
    return opt


def write_events(start, stop):
    print('Using events file {}'.format(kadi.paths.EVENTS_DB_PATH()))

    for attr in dir(kadi.events):
        evt = getattr(kadi.events, attr)
        if type(evt) is not kadi.events.EventQuery:
            continue

        # These event types are frequently updated after ingest.  See
        # https://github.com/sot/kadi/issues/85.  For now just ignore.
        if attr in ('caps', 'dsn_comms', 'major_events'):
            continue

        dat = evt.filter(start, stop).table

        filename = os.path.join(opt.data_root, attr + '.ecsv')
        print('Writing event {}'.format(filename))
        dat.write(filename, format='ascii.ecsv')


def write_cmds(start, stop):
    print('Using commands file {}'.format(kadi.paths.IDX_CMDS_PATH()))
    cmds = kadi.cmds.filter(start, stop)
    out = repr(cmds)
    filename = os.path.join(opt.data_root, 'cmds.txt')
    print('Writing commands {}'.format(filename))
    with open(filename, 'w') as fh:
        fh.write(out)


if __name__ == '__main__':
    opt = get_opt()
    if not os.path.exists(opt.data_root):
        os.makedirs(opt.data_root)
    start = DateTime(opt.start) + 3
    stop = DateTime(opt.stop) - 3

    write_events(start, stop)
    write_cmds(start, stop)
