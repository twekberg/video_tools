#!/usr/bin/env python
"""
Calculation various statistics on video clips.
Also does a check on time values.
"""

import argparse
import sqlite3
import math
from os.path import isdir
import os
import sys
import shutil
from datetime import date
import json
import itertools
import re

activities = {
    'L': 'Lick',
    'O': 'Open',
    'S': 'Squirt',
    'T': 'Tongue',
    'U': 'Up',
    }


def build_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.strip())

    parser.add_argument('-d', '--database_file', default='example.db',
                        help='File name of the SQlite database file. '
                        'default: %(default)s')

    return parser


def main(args):
    con = db_open(args.database_file)
    #             0  1        2          3
    sql = 'SELECT id,video_id,start_time,duration FROM clips'
    cur = con.cursor()
    cur.execute(sql)
    bad_data = []
    fatal_error_count = 0
    while True:
        rs = cur.fetchone()
        if not rs:
            break
        if not check_start(rs[2]):
            bad_data.append((rs[0], rs[1], rs[2]))
        try:
            check_seconds(rs[3])
        except Exception as arg:
            (id, video_id, start_time, duration) = rs
            sql = 'SELECT filename FROM videos WHERE id=:video_id'
            cur.execute(sql, dict(video_id=video_id))
            rs = cur.fetchone()
            print(arg,(id, video_id, start_time, duration), rs[0])
            fatal_error_count += 1
    if fatal_error_count:
        exit(1)
    if bad_data:
        print('Bad data:')
        cur = con.cursor()
        sql = 'SELECT id,filename FROM videos WHERE id=:video_id'
        for (clip_id, video_id, start_time) in bad_data:
            cur.execute(sql, dict(video_id=video_id))
            rs = cur.fetchone()
            print(clip_id, video_id, start_time, rs[1])

    # Make sure duration_seconds and start_frame have values.
    sql = "SELECT id, start_time, duration FROM clips WHERE duration_seconds IS NULL OR start_frame IS NULL"
    cur.execute(sql)
    for rs in cur.fetchall():
        try:
            (id, start_time, duration) = rs
            start_frame = to_start_frame(start_time)
            duration_seconds = to_seconds(duration)
            sql = 'UPDATE clips SET start_frame=:start_frame, duration_seconds=:duration_seconds WHERE id=:id'
            cur.execute(sql, dict(id=id, start_frame=start_frame, duration_seconds=duration_seconds))
        except Exception as e:
            print('Exception %s: clip id=%s' % (e, id))
    con.commit()

    details = [['Act', 'Secs', 'Count', 'Min', 'Max', 'Avg',  'StdDev', 'Variance']]
    sql = """SELECT  activity, sum(duration_seconds) "Sum" ,count(duration_seconds) "Count",
  min(duration_seconds) "Min", max(duration_seconds) "Max",
  sum(duration_seconds) / count(duration_seconds) "Avg"
FROM clips GROUP BY activity ORDER BY 1"""
    cur.execute(sql)
    for rs in cur.fetchall():
        if not rs[1]:
            continue
        detail = [rs[0], format_time(rs[1])] + ['\t'.join(('%5.1f' % (r,)).lstrip() for r in rs[2:])]

        sql = """SELECT AVG((clips.duration_seconds - sub.a) * (clips.duration_seconds - sub.a))
                   FROM clips, 
                   (SELECT AVG(duration_seconds) AS a FROM clips) AS sub
                 WHERE activity = :activity"""
        cur.execute(sql, dict(activity = rs[0]))
        rs2 = cur.fetchone()
        details.append(detail + ['%5.1f' % (math.sqrt(rs2[0]),), '%5.1f' % (rs2[0],)])

    sql = """SELECT  activity, sum(duration_seconds) "Sum" ,count(duration_seconds) "Count",
  min(duration_seconds) "Min", max(duration_seconds) "Max",
  sum(duration_seconds) / count(duration_seconds) "Avg"
FROM clips ORDER BY 1"""
    cur.execute(sql)
    rs = cur.fetchone()
    total = rs[1]
    detail = ['Total', format_time(total)] + ['\t'.join(('%5.1f' % (r,)).lstrip() for r in rs[2:])]

    sql = """SELECT AVG((clips.duration_seconds - sub.a) * (clips.duration_seconds - sub.a))
               FROM clips, 
               (SELECT AVG(duration_seconds) AS a FROM clips) AS sub"""
    cur.execute(sql)
    rs2 = cur.fetchone()
    details.append(detail + ['%5.1f' % (math.sqrt(rs2[0]),), '%5.1f' % (rs2[0],)])

    for row in details:
        if len(row[1]) < 8:
            row[1] += '\t'
        sys.stdout.write('%-17s' % (activities[row[0]] if row[0] in activities else row[0]))
        sys.stdout.write('\t'.join(row[1:]))
        sys.stdout.write('\n')


def to_start_frame(start_time):
    """
    Convert start_time to start_frame.
    """
    m = [1, 30, 30 * 60, 30 * 60 * 60]
    i = 0
    start_frame = 0
    for part in reversed(start_time.split(':')):
        start_frame += int(part) * m[i]
        i += 1
    return start_frame


def to_seconds(s):
    #               s  s    f  f
    m = re.match('^(\d?\d):(\d\\d)$', s)
    if m:
        hour = 0
        min = 0
        sec = m.group(1)
        frame = m.group(2)
    else:
        #               m  m    s s    f  f
        m = re.match('^(\d?\d):(\d\d):(\d\\d)$', s)
        if m:
            hour = 0
            min = m.group(1)
            sec = m.group(2)
            frame = m.group(3)
        else:
            #               h  h    m  m    s s    f  f
            m = re.match('^(\d?\d):(\d?\d):(\d\d):(\d\\d)$', s)
            if m:
                hour = m.group(1)
                min = m.group(2)
                sec = m.group(3)
                frame = m.group(4)
            else:
                return "Didn't match proper syntax: %s" % (s,)
    if int(frame) >= 30:
        return 'Frame too large: %s in %s' % (frame, s)
    return (int(hour) * 60 + int(min)) * 60 + int(sec) + (int(frame) / 30.0)


def check_seconds(s):
    #               s  s    f  f
    m = re.match('^(\d?\d):(\d\\d)$', s)
    if m:
        hour = 0
        min = 0
        sec = m.group(1)
        frame = m.group(2)
    else:
        #               m  m    s s    f  f
        m = re.match('^(\d?\d):(\d\d):(\d\\d)$', s)
        if m:
            hour = 0
            min = m.group(1)
            sec = m.group(2)
            frame = m.group(3)
        else:
            #               h  h    m m    s s    f  f
            m = re.match('^(\d?\d):(\d\d):(\d\d):(\d\\d)$', s)
            if m:
                hour = m.group(1)
                min = m.group(2)
                sec = m.group(3)
                frame = m.group(4)
            else:
                raise Exception("Didn't match: %s" % (s,))
    if int(frame) >= 30:
        raise Exception('Frame too large: %s in %s' % (frame, s))
    return (int(hour) * 60 + int(min)) * 60 + int(sec) + (int(frame) / 30.0)


def check_start(t):
    #                   h    min    m  sec  s  fra  f
    return re.match('^(([123]:)?[0-5])?\d:[0-5]\d:[0-2]\d$', t)
    

def format_time(t):
    ms =int(100 * ( t - int(t) ))
    t = int(t)
    sec = t % 60
    t = t / 60
    min = t % 60
    h = t / 60
    if h:
        return '%d:%02d:%02d.%02d' % (h, min, sec, ms)
    return '%d:%02d.%02d' % (min, sec, ms)


def db_open(database_file):
    return sqlite3.connect(database_file)


if __name__ == '__main__':
    main(build_parser().parse_args(sys.argv[1:]))
