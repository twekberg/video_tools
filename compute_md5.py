#!/usr/bin/env python
"""
Run through the videos table computing the md5 checksum for the file and store it.
"""

import argparse
import hashlib
from pathlib import Path
import sqlite3
import sys


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

    parser.add_argument('-v', '--videos_dir',
                        default='F:/N/O/SPELLSNO/IMAGES/xxxbunker',
                        help='Directory where videos are located. '
                        'default: %(default)s')

    return parser


def main(args):
    """
    Main processing function.
    """
    con = db_open(args.database_file)
    # Make sure every video has an MD5 value.
    sql = "SELECT id,filename FROM videos WHERE md5 IS NULL OR md5 =''"
    cur = con.cursor()
    cur.execute(sql)
    count = 0
    bad_ids = []
    for results in cur.fetchall():
        count += 1
        if count % 100 == 0:
            sys.stderr.write('.')
        (video_id, filename) = results
        try:
            path = Path(args.videos_dir) / filename
            with open(str(path)) as in_file:
                pass
        except:
            if not bad_ids:
                print('No such file:')
            print(video_id,filename)
            bad_ids.append(video_id)
    sys.stderr.write('\n')
    if bad_ids:
        print(f"Mismatched counts: {len(bad_ids)}")
    cur.execute(sql)
    count = 0
    for results in cur.fetchall():
        count += 1
        if count % 100 == 0:
            sys.stderr.write('.')
            con.commit()
        (video_id, filename) = results
        if id in bad_ids:
            print('skipping',video_id,filename)
            continue
        path = Path(args.videos_dir) / filename
        with open(str(path)) as in_file:
            md5_hash = hashlib.md5()
            for line in in_file:
                md5_hash.update(line)
        md5 = md5_hash.hexdigest()
        sql = 'SELECT id,filename FROM videos WHERE md5 = :md5'
        cur.execute(sql, {'md5':  md5})
        for results in cur.fetchall():
            (dup_id, dup_filename) = results
            print(f'while processing {filename}')
            print(f'duplicate MD5 {md5} for {dup_id}, file {dup_filename}')
        args = {'id': id, 'md5': md5}
        sql = 'UPDATE videos SET md5 = :md5 WHERE id = :id'
        con.execute(sql, args)
        con.commit()
    sys.stderr.write('\n')

    # Look for the videos with duplicate md5 values.
    sql = 'SELECT md5,count(*) FROM videos GROUP BY md5 HAVING count(*)>1'
    cur.execute(sql)
    first_time = True
    for (md5, _) in cur.fetchall():
        if first_time:
            print('Duplicate md5')
            first_time = False
        sql = "SELECT id,filename,comment FROM videos WHERE md5 = :md5 and comment NOT LIKE 'dup%'"
        cur.execute(sql, {'md5': md5})
        dups = []
        for (dup_id, dup_filename, dup_comment) in cur.fetchall():
            dups.append([dup_id, dup_filename, dup_comment])
        if len(dups) > 1:
            for (dup_id, dup_filename, dup_comment) in dups:
                print('|'.join([str(field) for field in [dup_id, dup_comment, dup_filename]]))


def db_open(db_file):
    """
    Open the database and return a connection object.
    """
    return sqlite3.connect(db_file)


if __name__ == '__main__':
    main(build_parser().parse_args())
