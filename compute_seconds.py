#!/usr/bin/env python
"""
Run theough the clips table computing seconds from the duration field.
"""

import argparse
import sqlite3
import sys
import re


def build_parser():
    """
    Command line parser.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.strip())

    parser.add_argument('-d', '--database_file', default='example.db',
                        help='File name of the SQlite database file. '
                        'default: %(default)s')

    return parser


def main(args):
    """
    Main processing function.
    """
    con = db_open(args.database_file)
    sql = 'SELECT id,duration FROM clips WHERE duration_seconds IS NULL'
    cur = con.cursor()
    cur.execute(sql)
    pairs = []
    while True:
        results = cur.fetchone()
        if not results:
            break
        pairs.append((results[0], to_seconds(results[1])))

    sql = 'UPDATE clips SET duration_seconds = :seconds WHERE id = :id'
    for (clip_id, seconds) in pairs:
        con.execute(sql, {'id': clip_id, 'seconds': seconds})
    con.commit()
    print(len(pairs))


def to_seconds(time_string):
    """
    Convert string time to seconds.
    """
    #                     s  s    f f
    match = re.match(r'^(\d?\d):(\d\d)$', time_string)
    if match:
        hour = 0
        minute = 0
        sec = match.group(1)
        frame = match.group(2)
    else:
        #                     m  m    s s    f f
        match = re.match(r'^(\d?\d):(\d\d):(\d\d)$', time_string)
        if match:
            hour = 0
            minute = match.group(1)
            sec = match.group(2)
            frame = match.group(3)
        else:
            #                     h  h    m m    s s    f f
            match = re.match(r'^(\d?\d):(\d\d):(\d\d):(\d\d)$', time_string)
            if match:
                hour = match.group(1)
                minute = match.group(2)
                sec = match.group(3)
                frame = match.group(4)
            else:
                print(f"Didn't match: {time_string}")
                sys.exit(1)
    if int(frame) >= 30:
        print(f'Frame too large: {frame} in {time_string}')
        sys.exit(1)
    return (int(hour) * 60 + int(minute)) * 60 + int(sec) + (int(frame) / 30.0)


def db_open(db_file):
    """
    Open the database and return a connection object.
    """
    return sqlite3.connect(db_file)


if __name__ == '__main__':
    main(build_parser().parse_args(sys.argv[1:]))
