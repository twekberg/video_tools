#!/usr/bin/env python
"""
File: listboxdemo.py
Author: Kenneth A. Lambert

Derived from video_clip_editor.py. This one uses the database and uses
the produced flag to determine the next video to be searched for.

Notes:
Run MobaXterm and start an xterm session. Look at $DISPLAY
In the cygwin window enter:
    $ export DISPLAY=127.0.0.1:0.0
assuming $DISPLAY is that. Then run

    $ python video_clip_editor.py

A dialog should appear on the screen.

TODO:

DONE:
"""

import argparse
import sys
from breezypythongui import EasyFrame
versionNumber = sys.version_info.major
if versionNumber == 3:
    from tkinter import END, NORMAL, DISABLED, LEFT
else:
    from Tkinter import END, NORMAL, DISABLED, LEFT
import sqlite3
import math
from os.path import isdir
import os
import pyperclip
import shutil
import time
from datetime import date
import json
import itertools
import re


INITIAL_TIME = '0:'

def build_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__.strip())

    parser.add_argument('-d', '--database_file', default='example.db',
                        help='File name of the SQlite database file. '
                        'default: %(default)s')

    parser.add_argument('--debug', action='store_true',
                        default=False,
                        help='Turn on debug output. '
                        'default: %(default)s')
    return parser


class Video(object):
    """
    Object that maps to the videos table.
    """
    def __init__(self, filename, con):
        """
        Use the filename to retrieve the other values
        """
        values = dict(filename=filename)
        sql = 'SELECT id, comment, edited, produced FROM videos WHERE filename=:filename'
        cur = con.cursor()
        cur.execute(sql, values)
        rs = cur.fetchone()
        if rs:
            (self.id, self.comment, self.edited, self.produced) = rs
            self.edited   = bool(self.edited)
            self.produced = bool(self.produced)
        else:
            self.id = -1
            self.edited = False
            self.produced = False
        self.filename  = filename


class Clips(object):
    """
    Object that maps to the clips table. Collects all clips for a
    specific video.
    """
    def __init__(self, video_id, con):
        """
        Use the video_id to retrieve all related clips.
        """
        values = dict(video_id = video_id)
        sql = 'SELECT id, start_time, duration, activity, mag FROM clips WHERE video_id=:video_id'
        cur = con.cursor()
        cur.execute(sql, values)
        rs = cur.fetchone()
        self.clips = []
        self.len = 0
        while rs:
            (id, start_time, duration, activity, mag) = rs
            self.len += 1
            self.clips.append(dict(id = id,
                                   start_time = start_time,
                                   duration = duration,
                                   activity = activity,
                                   mag = mag,))
            rs = cur.fetchone()



class VideoClipEditor(EasyFrame):
    """Allows the user to add items to a list box, remove them,
    and select them. Backend is a database."""

    def __init__(self, args):
        """Sets up the window and the widgets."""
        self.debug = args.debug
        self.setup_frame()
        db = args.database_file
        self.con = sqlite3.connect(db)

        # Retrieve the available videos.
        sql = 'SELECT id, filename FROM videos ORDER BY 2'
        cur = self.con.cursor()
        cur.execute(sql)
        self.available_videos = []
        while True:
            rs = cur.fetchone()
            if not rs:
                break
            id = rs[0]
            filename = rs[1]
            video = Video(filename, self.con)
            clips = Clips(video.id, self.con)
            # Ignore videos with no clips.
            if clips.len:
                self.available_videos.append([video, clips])

        self.available_videos_index = -1
        self.next_avail()
        print(len(self.available_videos))
        print('\n'.join(['%4d %s' % (video.id, video.filename) for (video, clips)
                         in self.available_videos
                         if not video.produced][:20]))


    def setup_frame(self):
        EasyFrame.__init__(self, title = "Video Clip Producer",
                           width = 1100, height = 400)


        panel = self.addPanel(0, 0, columnspan=4)
        panel.addButton(text = "Next File", row = 0, column = 0, command = self.next_video)
        panel.addButton(text = "Next Avail", row = 0, column = 1, command = self.next_avail)
        panel.addLabel(text = "Filename:", row = 0, column = 2)
        self.filenameField = panel.addTextField(text = "", row = 0, column = 3, width = 100, columnspan = 2, sticky = 'nw')

        panel = self.addPanel(1, 0, columnspan=4)
        panel.addButton(text = "Prev File", row = 0, column = 0, command = self.prev_video)
        panel.addButton(text = "Prev Avail", row = 0, column = 1, command = self.prev_avail)
        panel.addLabel(text = "Comment:", row = 0, column = 2)
        self.commentField = panel.addTextField(text = "", row = 0, column = 3, width = 100, columnspan = 2, sticky = 'nw')

        panel = self.addPanel(2, 0, columnspan=3)
        panel.addButton(text = "100--", row = 0, column = 0, command = self.prev_100)
        panel.addButton(text = "100++", row = 0, column = 1, command = self.next_100)
        self.producedButton = panel.addCheckbutton(text = "Produced", row = 0, column = 2)
        panel.addButton(text = "censored", row = 0, column = 3, command = lambda: self.bad_comment('censored'))
        panel.addButton(text = "bad video", row = 0, column = 4, command = lambda: self.bad_comment('bad video'))

        self.videoEditedLabel = self.addLabel(text = "", row = 3, column = 0, sticky = 'nw')

        self.addLabel(text = "Clip", row = 4, column = 0, font = 'Courier 12 bold')
        self.clipListBox = self.addListbox(row = 4, column = 3, rowspan = 6, width=8)

        self.addButton(text = "Produced", row = 5, column = 1, command = self.set_produced)

        self.addButton(text = "Exit", row = 6, column = 0, command = self.exit)
        self.was_produced = False


    def set_video(self, video, clips):
        self.filenameField.setText(video.filename)
        self.add_to_clipboard(video.filename.rsplit('.', 1)[0] + '.')
        self.video = video
        self.commentField.setText('')
        self.clipListBox.clear()
        if self.video.edited:
            self.videoEditedLabel.config(text=('Edited',))
            
            (self.producedButton.select if self.video.produced else self.producedButton.deselect)()
            clips = Clips(self.video.id, self.con)
            for clip in clips.clips:
                self.add_clip(clip)
        else:
            self.videoEditedLabel['text'] = ''


    def add_to_clipboard(self, text):
        """
        Put the text in the clipboard, removing whitespace from either end. What actually
        happens is that an extra character is appended to the clipboard which needs to be
        deleted to get the text.
        """
        pyperclip.copy(text.strip())



    # Event handling methods
    def next_video(self, display=True):
        """
        Position to the next video.
        """
        self.available_videos_index += 1
        video = self.available_videos[self.available_videos_index]
        if display:
            print(video[0].id, self.available_videos_index)
            self.set_video(*video)


    def next_avail(self):
        """
        Position to the next video that hasn't been produced.
        """
        self.available_videos_index += 1
        for (video, clips) in self.available_videos[self.available_videos_index:]:
            if not video.produced:
                break
            self.available_videos_index += 1
        print(video.id, self.available_videos_index)
        self.set_video(video, clips)


    def prev_video(self, display=True):
        """
        Position to the previous video.
        """
        self.available_videos_index = max(self.available_videos_index - 1, 0)
        video = self.available_videos[self.available_videos_index]
        if display:
            print(video[0].id, self.available_videos_index)
            self.set_video(*video)


    def prev_avail(self):
        """
        Position backwards for the previous video that hasn't been produced.
        """
        self.available_videos_index = max(self.available_videos_index - 1, 0)
        # Add 1 to get the video we are pointing to (inclusive).
        for (video, clips) in reversed(self.available_videos[:self.available_videos_index+1]):
            if not video.produced:
                break
            self.available_videos_index -= 1
        print(video.id, self.available_videos_index)
        self.set_video(video, clips)


    def prev_100(self):
        for x in range(99):
            self.prev_video(False)
        self.prev_video()


    def next_100(self):
        for x in range(99):
            self.next_video(False)
        self.next_video()

    def bad_comment(self, comment):
        self.commentField.setText(comment)


    def show_error(self, message):
        self.messageBox(title = "ERROR", message = message)


    def set_produced(self):
        """
        Mark this video as produced, presistently.
        """
        sql = """UPDATE videos SET produced = 1, produced_date = :produced_date WHERE id = :id"""
        values = dict(id = self.video.id,
                      produced_date = date.today().strftime('%Y-%m-%d'))
        try:
            self.con.execute(sql, values)
            self.commit()
            self.video.produced = True
            self.producedButton.select()
            print('Produced %s' % (self.video.id,))
        except sqlite3.OperationalError:
            self.show_error("Got an OperationalError. Fix and try to save again.")


    def add_clip(self, c):
        """
        Format a clip and put in the clipListBox.
        """
        item = ('%s  ' * 4) % (c['start_time'], c['duration'], c['activity'], c['mag'])
        self.clipListBox.insert(END, item)


    def commit(self):
        self.con.commit()


    def exit(self, *args):
        self.quit()
        #self.destroy()


def main(args):
    VideoClipEditor(args).mainloop()


# Instantiate and pop up the window."""
if __name__ == "__main__":
    main(build_parser().parse_args())
