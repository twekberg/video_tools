#!/usr/bin/env python
"""
Calculation various statistics on video clips.
Also does a check on time values.
"""

import argparse
import sqlite3
import math
import sys
import re

activities = {
    'L': 'Lick',
    'O': 'Open',
    'S': 'Squirt',
    'T': 'Tongue',
    'U': 'Up',
    }


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
    #             0  1        2          3
    sql = 'SELECT id,video_id,start_time,duration FROM clips'
    cur = con.cursor()
    cur.execute(sql)
    bad_data = []
    fatal_error_count = 0
    while True:
        results = cur.fetchone()
        if not results:
            break
        if not check_start(results[2]):
            bad_data.append((results[0], results[1], results[2]))
        try:
            check_seconds(results[3])
        except Exception as arg:
            (id, video_id, start_time, duration) = results
            sql = 'SELECT filename FROM videos WHERE id=:video_id'
            cur.execute(sql, {'video_id': video_id})
            results = cur.fetchone()
            print(arg,(id, video_id, start_time, duration), results[0])
            fatal_error_count += 1
    if fatal_error_count:
        sys.exit(1)
    if bad_data:
        print('Bad data:')
        cur = con.cursor()
        sql = 'SELECT id,filename FROM videos WHERE id=:video_id'
        for (clip_id, video_id, start_time) in bad_data:
            cur.execute(sql, {'video_id': video_id})
            results = cur.fetchone()
            print(clip_id, video_id, start_time, results[1])

    # Make sure duration_seconds and start_frame have values.
    sql = "SELECT id, start_time, duration FROM clips " \
          "WHERE duration_seconds IS NULL OR start_frame IS NULL"
    cur.execute(sql)
    for results in cur.fetchall():
        try:
            (id, start_time, duration) = results
            start_frame = to_start_frame(start_time)
            duration_seconds = to_seconds(duration)
            sql = 'UPDATE clips SET start_frame=:start_frame, ' \
                  'duration_seconds=:duration_seconds WHERE id=:id'
            cur.execute(sql, {'id': id, 'start_frame': start_frame,
                              'duration_seconds': duration_seconds})
        except Exception as exception:
            print(f'{exception=}: clip id={id}')
    con.commit()

    details = [['Act', 'Secs', 'Count', 'Min', 'Max', 'Avg',  'StdDev', 'Variance']]
    sql = """SELECT  activity, sum(duration_seconds) "Sum" ,count(duration_seconds) "Count",
  min(duration_seconds) "Min", max(duration_seconds) "Max",
  sum(duration_seconds) / count(duration_seconds) "Avg"
FROM clips GROUP BY activity ORDER BY 1"""
    cur.execute(sql)
    for results in cur.fetchall():
        if not results[1]:
            continue
        detail = [results[0], format_time(results[1])] + \
                 ['\t'.join(f'{r:5.1f}'.lstrip() for r in results[2:])]

        sql = """SELECT AVG((clips.duration_seconds - sub.a) * (clips.duration_seconds - sub.a))
                   FROM clips, 
                   (SELECT AVG(duration_seconds) AS a FROM clips) AS sub
                 WHERE activity = :activity"""
        cur.execute(sql, {'activity': results[0]})
        results2 = cur.fetchone()
        details.append(detail + [f'{math.sqrt(results2[0]):5.1f}',
                                 f'{results2[0]:5.1f}'])
    sql = """SELECT  activity, sum(duration_seconds) "Sum" ,count(duration_seconds) "Count",
  min(duration_seconds) "Min", max(duration_seconds) "Max",
  sum(duration_seconds) / count(duration_seconds) "Avg"
FROM clips ORDER BY 1"""
    cur.execute(sql)
    results = cur.fetchone()
    total = results[1]
    detail = ['Total', format_time(total)] + \
             ['\t'.join(f'{r:5.1f}'.lstrip() for r in results[2:])]

    sql = """SELECT AVG((clips.duration_seconds - sub.a) * (clips.duration_seconds - sub.a))
               FROM clips, 
               (SELECT AVG(duration_seconds) AS a FROM clips) AS sub"""
    cur.execute(sql)
    results2 = cur.fetchone()
    details.append(detail + [f'{math.sqrt(results2[0]):5.1f}',
                             f'{results2[0]:5.1f}'])

    for row in details:
        if len(row[1]) < 8:
            row[1] += '\t'
        sys.stdout.write(f'{activities[row[0]]:<17s}' if row[0] in activities else
                         f'{row[0]:<17s}')
        sys.stdout.write('\t')
        sys.stdout.write('\t'.join(row[1:]))
        sys.stdout.write('\n')


def to_start_frame(start_time):
    """
    Convert start_time string to start_frame.
    """
    times = [1, 30, 30 * 60, 30 * 60 * 60]
    time_index = 0
    start_frame = 0
    for part in reversed(start_time.split(':')):
        start_frame += int(part) * times[time_index]
        time_index += 1
    return start_frame


def to_seconds(string):
    """
    Look at a seconds string to pull off the components.
    Returns the number seconds with fractional frames.
    """
    #                s  s    f  f
    match = re.match(r'^(\d?\d):(\d\d)$', string)
    if match:
        hour = 0
        minutes = 0
        sec = match.group(1)
        frame = match.group(2)
    else:
        #                m  m    s s    f  f
        match = re.match(r'^(\d?\d):(\d\d):(\d\d)$', string)
        if match:
            hour = 0
            minutes = match.group(1)
            sec = match.group(2)
            frame = match.group(3)
        else:
            #                     h  h    m  m    s s    f  f
            match = re.match(r'^(\d?\d):(\d?\d):(\d\d):(\d\d)$', string)
            if match:
                hour = match.group(1)
                minutes = match.group(2)
                sec = match.group(3)
                frame = match.group(4)
            else:
                return f"Didn't match proper syntax: {string=}"
    if int(frame) >= 30:
        return f'Frame too large: {frame} in {string}' % (frame, string)
    return (int(hour) * 60 + int(minutes)) * 60 + int(sec) + (int(frame) / 30.0)


def check_seconds(string):
    """
    Look at a seconds string to pull off the components.
    This only does validation
    """
    #                s  s    f  f
    match = re.match(r'^(\d?\d):(\d\d)$', string)
    if match:
        hour = 0
        minutes = 0
        sec = match.group(1)
        frame = match.group(2)
    else:
        #                     m  m    s s    f  f
        match = re.match(r'^(\d?\d):(\d\d):(\d\d)$', string)
        if match:
            hour = 0
            minutes = match.group(1)
            sec = match.group(2)
            frame = match.group(3)
        else:
            #                     h  h    m m    s s    f  f
            match = re.match(r'^(\d?\d):(\d\d):(\d\d):(\d\d)$', string)
            if match:
                hour = match.group(1)
                minutes = match.group(2)
                sec = match.group(3)
                frame = match.group(4)
            else:
                raise SyntaxError(f"Didn't match: {string=}")
    if int(frame) >= 30:
        raise SyntaxError(f'Frame too large: {frame} in {string}')
    return (int(hour) * 60 + int(minutes)) * 60 + int(sec) + (int(frame) / 30.0)


def check_start(time):
    """
    Runs re.match on the start time string.
    """
    #                       h    min    m  sec  s  fra  f
    return re.match(r'^(([123]:)?[0-5])?\d:[0-5]\d:[0-2]\d$', time)


def format_time(time):
    """
    Convert time in msec to a formatted string.
    """
    msec =int(100 * ( time - int(time) ))
    time = int(time)
    sec = time % 60
    time = time / 60
    minutes = int(time % 60)
    hour = int(time / 60)
    if hour:
        return f'{hour}:{minutes:02d}:{sec:02d}.{msec:02d}'
    return f'{minutes}:{sec:02d}.{msec:02d}'


def db_open(database_file):
    """
    Open the database and return a connection object.
    """
    return sqlite3.connect(database_file)


if __name__ == '__main__':
    main(build_parser().parse_args(sys.argv[1:]))
