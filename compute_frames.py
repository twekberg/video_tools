#!/usr/bin/env python
"""
Run theough the clips table computing start_frame from the start_time field.
"""

import argparse
import sqlite3


def build_parser():
    """
    Part command line.
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
    con = db_open(args.dtatbase_file)
    sql = 'SELECT id,start_time FROM clips WHERE start_frame IS NULL'
    cur = con.cursor()
    cur.execute(sql)
    pairs = []
    while True:
        results = cur.fetchone()
        if not results:
            break
        pairs.append((results[0], to_start_frame(results[1])))

    sql = 'UPDATE clips SET start_frame = :start_frame WHERE id = :id'
    for (clips_id, start_frame) in pairs:
        con.execute(sql, {'id': clips_id, 'start_frame': start_frame})
    con.commit()
    print(len(pairs))


m = [1, 30, 30 * 60, 30 * 60 * 60]

def to_start_frame(start_time):
    """
    Convert start_time to start_frame.
    """
    i = 0
    start_frame = 0
    for part in reversed(start_time.split(':')):
        start_frame += int(part) * m[i]
        i += 1
    return start_frame


def db_open(db_file):
    """
    Open the database and return a connection object.
    """
    return sqlite3.connect(db_file)


if __name__ == '__main__':
    main(build_parser().parse_args())
