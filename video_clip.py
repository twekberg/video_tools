#!/usr/bin/env python
"""
This program can be used to manage clips in video files. View the help
string with this:

    $ python video_clip.py -h

It displays a list of at most 20 videos available for editing, then for each
video, puts the filename of the video in the cut buffer, and allows specifying
start time, duration and activity for each clip. Putting the video file name in
the cut buffer makes it easier to view the video in video editor.

Look at the README file for usage instructions.
"""

# Note: a video can be converted to a thumbnail. This is useful because
# VisiPics can be used to detect duplicates. A sample command is:
#
# magick convert 'input.mpg[5]' -resize 400x400 thumbnail.jpg

import argparse
from datetime import date, datetime, timedelta
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

import pyperclip


# ffprobe generates the duration with decimal fractions .00 - .99.
# We need frames instead. This maps a decimal fraction to a frame number.
fraction_to_frame = {
    .00: '00', .01: '00', .02: '00', .03: '01', .04: '01',
    .05: '01', .06: '02', .07: '02', .08: '02', .09: '03',
    .10: '03', .11: '03', .12: '03', .13: '04', .14: '04',
    .15: '04', .16: '05', .17: '05', .18: '05', .19: '06',
    .20: '06', .21: '06', .22: '06', .23: '07', .24: '07',
    .25: '07', .26: '07', .27: '08', .28: '08', .29: '08',
    .30: '09', .31: '09', .32: '10', .33: '10', .34: '10',
    .35: '10', .36: '10', .37: '11', .38: '11', .39: '11',
    .40: '12', .41: '12', .42: '12', .43: '13', .44: '13',
    .45: '13', .46: '13', .47: '14', .48: '14', .49: '14',
    .50: '15', .51: '15', .52: '15', .53: '15', .54: '16',
    .55: '16', .56: '16', .57: '16', .58: '17', .59: '17',
    .60: '17', .61: '18', .62: '18', .63: '18', .64: '19',
    .65: '19', .66: '19', .67: '19', .68: '20', .69: '20',
    .70: '21', .71: '21', .72: '22', .73: '22', .74: '22',
    .75: '22', .76: '23', .77: '23', .78: '23', .79: '24',
    .80: '24', .81: '24', .82: '24', .83: '25', .84: '25',
    .85: '25', .86: '26', .87: '26', .88: '26', .89: '26',
    .90: '27', .91: '27', .92: '27', .93: '27', .94: '28',
    .95: '28', .96: '29', .97: '29', .98: '29', .99: '29',
}


def build_parser():
    """
    Parse command line.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.strip())

    parser.add_argument('-a', '--activity', default='BELOW',
                        help='Activity, default: %(default)s')
    parser.add_argument('-d', '--database_file', default='example.db',
                        help='File name of the SQlite database file. '
                        'default: %(default)s')
    parser.add_argument('-v', '--videos_dir',
                        default='F:/N/O/SPELLSNO/IMAGES/xxxbunker',
                        help='Directory where videos are located. '
                        'default: %(default)s')

    return parser


class Video():
    """
    Holds data related to a video
    """
    def __init__(self, filename, con):
        """
        Use the filename to retrieve the other values
        """
        values = {'filename': filename}
        sql = 'SELECT id, comment, edited FROM videos WHERE filename=:filename'
        cur = con.cursor()
        cur.execute(sql, values)
        results = cur.fetchone()
        if results:
            (self.id, self.comment, self.edited) = results
            self.edited = bool(self.edited)
        else:
            self.id = -1
            self.edited = False
        self.filename  = filename


class Clips():
    """
    Holds detail related to clips for a video.
    Stored in self.clips.
    """
    def __init__(self, video_id, con):
        """
        Use the video_id to retrieve all related clips.
        """
        values = {'video_id': video_id}
        sql = 'SELECT id, start_time, duration, activity, mag FROM clips WHERE video_id=:video_id'
        cur = con.cursor()
        cur.execute(sql, values)
        results = cur.fetchone()
        self.clips = []
        self.len = 0
        while results:
            (id, start_time, duration, activity, mag) = results
            self.len += 1
            self.clips.append({'id': id,
                               'start_time': start_time,
                               'duration': duration,
                               'activity': activity,
                               'mag': mag})
            results = cur.fetchone()


class VideoClipData():
    """
    Retrieve data from the user and store in the database.
    """

    def __init__(self, args):
        """Initializes the data structures."""
        self.activity = args.activity
        self.videos_dir = args.videos_dir
        self.con = sqlite3.connect(args.database_file)
        db_files = self.get_files_from_db()
        self.disk_files = self.get_files_from_disk()
        self.available_files = [(file, self.disk_files.index(file))
                                for file in sorted(list(set(self.disk_files) - set(db_files)))]
        print('\n'.join([str(x) for x in self.available_files[:20]]))
        self.disk_files_index = -1

        sql = 'SELECT DISTINCT activity FROM clips ORDER BY 1'
        cur = self.con.cursor()
        cur.execute(sql)
        self.activities = [row[0] for row in cur.fetchall()]
        # pylint wants these initialized here.
        self.filename = None
        self.video = None


    def get_files_from_db(self):
        """
        Get the list of files from the database.
        """
        sql = 'SELECT filename from VIDEOS'
        cur = self.con.cursor()
        cur.execute(sql)
        db_files = []
        while True:
            results = cur.fetchone()
            if not results:
                break
            db_files.append(results[0])
        return db_files


    def get_files_from_disk(self):
        """
        Get the list of files from the disk.
        """
        return [file for file in os.listdir(self.videos_dir)
                if file[-3:] in ['gif', 'mpg', 'mp4', 'wmv']]


    def set_filename(self, name):
        """
        Set filename to the file being edited.
        """
        self.add_to_clipboard(name)
        self.video = Video(name, self.con)
        if self.video.edited:
            print(f'Error: file {name} already edited.')
            sys.exit()
        self.filename = name



    def add_to_clipboard(self, text):
        """
        Put the text in the clipboard, removing whitespace from either end. What actually
        happens is that an extra character is appended to the clipboard which needs to be
        deleted to get the text.
        """
        pyperclip.copy(text.strip())


    def next_avail(self):
        """
        Get the next available video.
        """
        self.disk_files_index += 1
        for (file, index) in self.available_files:
            if index >= self.disk_files_index:
                self.disk_files_index = index
                break
        else:
            if len(self.available_files) == 0:
                print('No files available')
                sys.exit(0)
            # Didn't find it. Point to the last one
            (file, self.disk_files_index) = self.available_files[-1]
        print(self.disk_files_index)
        self.set_filename(file)


    def add_video(self):
        """
        Retrieve values from the user and store into the DB.

        Returning 1 indicates to look for another video,
        -1 indicates to stop.
        """
        # This is a new video. Need to create the video
        self.next_avail()
        print(f'Editing: {self.filename}')
        sys.stdout.write('Comment: ')
        sys.stdout.flush()
        comment = sys.stdin.readline().strip()
        if len(comment) > 0 and (comment[0].lower() in ['e', 'q']):
            return -1
        if len(comment) > 0 and comment.lower().startswith('skip'):
            # skip this video for now.
            return 1
        if len(comment) > 0 and comment[0].isdigit():
            # Entering the start_time
            start_time = comment
            comment = ''
        else:
            start_time = ''
        sql = """INSERT INTO videos (filename, comment, edited, created_date) VALUES (
:filename, :comment, :edited, :created_date)"""
        values = {'filename': self.filename,
                  'comment': comment,
                  'edited': True,
                  'created_date': date.today().strftime('%Y-%m-%d')}
        self.con.execute(sql, values)
        sql = 'SELECT id FROM videos WHERE filename=:filename'
        cur = self.con.cursor()
        cur.execute(sql, values)
        results = cur.fetchone()
        self.video.id = results[0]
        self.video.comment = comment
        self.video.edited = True
        self.commit()
        self.get_clips(start_time)
        return 1


    def get_clips(self, initial_start_time):
        """
        Get all clips for this video.
        If the user entered a digit as the first character of a comment,
        treat it as the initial start time.
        """
        activity = self.activity
        sql = """INSERT INTO clips (video_id, start_time, duration, activity, mag) VALUES (
    :video_id, :start_time, :duration, :activity, :mag)"""
        clip_number = 1
        # Auto fill for MM: or HH:MM:
        auto_fill_time = '0:'
        time_remaining = get_clip_length(str(Path(self.videos_dir) / self.filename))
        print(f'{time_remaining=}')
        while True:
            if initial_start_time:
                # Set start time (was a comment) and fix common data entry errors.
                start_time = initial_start_time.strip().replace(';', ':')
                sys.stdout.write(f'start_time clip {clip_number} ({auto_fill_time}): {start_time}\n')
                sys.stdout.flush()
                initial_start_time = ''
            else:
                sys.stdout.write(f'start_time clip {clip_number} ({auto_fill_time}): ')
                sys.stdout.flush()
                # Fix common data entry errors.
                start_time = sys.stdin.readline().strip().replace(';', ':')

            if start_time == '':
                break
            if start_time == '0':
                start_time = '0:00:00'
            if start_time.count(':') == 1:
                if match := re.match(r'(\d+):(\d+)$', start_time):
                    start_time  = f'{int_safe(match.group(1)):02d}:' \
                                  f'{int_safe(match.group(2)):02d}'
                    # Now nn:nn
                    start_time = auto_fill_time + start_time

            end_duration = subtract_time(time_remaining, start_time)
            sys.stdout.write(f'duration ({end_duration}): ')
            sys.stdout.flush()
            duration   = sys.stdin.readline().strip()
            if not duration:
                # Default to end of this clip.
                duration = end_duration
            duration = duration.replace(';', ':')
            duration = ':'.join([f'{int_safe(part):02d}'
                                 for part in duration.split(':')]).lstrip('0')

            # compute using start_time + duration adding ':'
            auto_parts = from_frame(to_frame(start_time) + to_frame(duration)).rsplit(':', 2)
            print(f'{auto_parts=}, {start_time=}, {duration=}')
            if len(auto_parts) > 2:
                auto_fill_time = ':'.join(auto_parts[0:len(auto_parts) - 2]) + ':'
            #else leave as 0:0

            while True:
                sys.stdout.write(f'activity ({activity},?): ')
                sys.stdout.flush()
                new_activity   = sys.stdin.readline().strip()
                if new_activity != '?':
                    break
                print(self.activities)
            if new_activity:
                activity = new_activity
            if activity not in self.activities:
                # Not there. See if it is an abbrev of an existing
                matches = [act for act in self.activities if act.startswith(activity)]
                if len(matches) == 1:
                    activity = matches[0]
                    print(activity)

            mag = '1'
            sys.stdout.write(f'mag ({mag}): ')
            sys.stdout.flush()
            new_mag        = sys.stdin.readline().strip()
            if new_mag:
                mag = new_mag

            values = {'start_time': start_time,
                      'duration': duration,
                      'activity': activity,
                      'mag': mag,
                      'video_id': self.video.id}
            retry = True
            while retry:
                try:
                    self.con.execute(sql, values)
                    self.commit()
                    retry = False
                except:
                    sys.stdout.write('Got an error with the database - probably locked. Retry? ')
                    sys.stdout.flush()
                    answer = sys.stdin.readline().strip()
                    if answer[0].upper() == 'N':
                        retry = False
            clip_number += 1


    def commit(self):
        """
        Commit the changes to the database.
        """
        self.con.commit()


def int_safe(value):
    """
    Safe version of int, always returns a value.
    """
    try:
        integer = int(value)
    except ValueError:
        print(f"Bad value: {value}, using 0")
        integer = 0
    return integer


def to_frame(time):
    """
    Convert a time in h:mm:ss:ff or m:ss:ff format to a frame int.
    """
    time_splits = time.split(':')
    time_splits.reverse()
    #                        F  S   M        H
    zips = zip(time_splits, [1, 30, 30 * 60, 30 * 60 * 60])
    return sum(int_safe(factor) * value for (factor, value) in zips if factor != '')


def from_frame(frames):
    """
    Convert frames to HH:MM:SS with leading 0s removed.
    """
    hhmmss = (datetime(2000, 1, 2) + timedelta(seconds=int(frames / 30))).strftime('%H:%M:%S')
    return hhmmss.lstrip('0:') + f':{(frames % 30):02d}'


def get_clip_length(filename):
    """
    Use ffprobe to get the length of a clip. Returns a time string.
    """
    result = subprocess.Popen(["C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/ffprobe",
                               filename],
                              stdout = subprocess.PIPE,
                              text=True,
                              stderr = subprocess.STDOUT)
    # Look for a line like this:
    #   Duration: 00:00:24.03, start: 0.000000, bitrate: 3485 kb/s
    raw_time = [x.split(',')[0].split()[1] for x in result.stdout.readlines() if "Duration" in x][0]
    parts = raw_time.replace('.', ':').split(':')
    # Use fraction_to_frame to convert decimal fractions to frame numbers.
    frame = fraction_to_frame[float(f'0.{parts[-1]}')]
    parts[-1] = frame
    almost = ':'.join(parts).replace('00:', '').lstrip('0')
    if not almost:
        almost = '0:00'
    if ':' not in almost:
        almost = f'0.{int(almost):02d}'
    return almost


def normalize_time(time_string):
    """
    Take a time string and convert to HH:MM:SS:FF format,
    two digits for each time element.
    """
    if time_string[1] == ':':
        time_string = '0' + time_string
    while time_string.count(':') < 3:
        time_string = '00:' + time_string
    return time_string


def subtract_time(minuend, subtrahend):
    """
    Compute minuend - subtrahend, both strings.
    Returns a string.
    """
    minuend = [int_safe(x) for x in normalize_time(minuend).split(':')]
    subtrahend = [int_safe(x) for x in normalize_time(subtrahend).split(':')]
    # Do frames first
    frame_diff = minuend[-1] - subtrahend[-1]
    if frame_diff < 0:
        # have to borrow from seconds.
        minuend[-2] -= 1
        frame_diff += 30
    diffs = [frame_diff]
    for index in [2, 1, 0]:
        diff = minuend[index] - subtrahend[index]
        if diff < 0:
            if index == 0:
                # Nothing to borrow from.
                raise ArithmeticError(f'underflow {minuend} - {subtrahend}')
            diff += 60
            minuend[index - 1] -= 1
        diffs = [diff] + diffs
    return array_to_time(diffs)


def array_to_time(array):
    """
    Convert array to a time string, removing leading 0s.
    """
    time_string = ':'.join([f'{element:02d}' for element in array]) \
                     .replace(':0', ':') \
                     .replace('00:', '')
    if time_string.startswith('0'):
        time_string = time_string[1:]
    if time_string[-2] == ':':
        # last time element must have 2 digits, add leading 0.
        time_string = time_string[0:-2] + ':0' + time_string[-1]
    return time_string.lstrip(':')


def main(args):
    """
    Main processing function.
    """
    data = VideoClipData(args)
    while True:
        if data.add_video() < 0:
            break


# Instantiate and pop up the window."""
if __name__ == "__main__":
    main(build_parser().parse_args(sys.argv[1:]))
