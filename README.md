# video_tools
Various programs related to video editing and producing.

# Overview

This is a collection of tools I use to manage the 100s of videos. I
use CyberLink PowerDirector to actually do the video editing. I use
the tools here to manage the clips.

video_clip.py - used in conjunction with PowerDirector to mark each
clip in a video. A clip has a start time, duration, activity and
optional magnification. I don't use the last field anymore. This
Python program collects that data for each clip and stores it into an
SQlite database.

# Dependencies

I use the following tools, which are assumed to be installed:

 - CyberLink PowerDirector video editor. Buy it here:
     https://www.cyberlink.com/. actually any video editor will work. 
 - ffprobe - download from here: https://ffmpeg.org/download.html
 - DB Browser for SQlite - download from here: https://sqlitebrowser.org/dl/


# First Step

First capture or create videos that look interesting. Store them in
you hard drive.

# video_clip.py

On startup this program detects new videos that are not in the
database. Next it will::
  1. display a short list of videos that can be processed,
  2. display the filename of the current video to be processed,
  3. Put that filename in the cut/paste buffer.
  4. Display the 'Comment: ' prompt.
  
At this prompt, one of several things can be entered::
  1. a string that starts with e or q (exit or quit). This causes the
     program to stop.
  2. the string 'skip' (without quotes). This causes processing of
     the current video to be skipped and processing on the next video
     to start. Nothing is written to the database. 
  3. a string that starts with a digit. This is the start time for the
     first clip of the video. Note that at this point the
     auto_fill_time variable it set to '0:'. If '0' is entered, the
     start_time becomes 0:00:00. If SS:FF (seconds and frames are
     digits (leading insignificant '0's can be omitted) is
     entered, the auto_fill_time is prepended setting start_time to
     '0:SS:FF'. a new auto_fill_file is calculated after every clip is
     procces by adding start_time and duration, truncating the seconds
     and frames part.
  4. If none of the above match the string becomes the comment field
     in the database for this video. This normally is an empty
     string.

If a comment was entered, the following are displayed::
  1. the length of the video in HH:MM:SS:FF format. Note that this may
     be off slightly because the time is calculated using a program
     that computes the fractional part as 2 digits to the right of the
     decimal point. Normally this may be off by at most 1 frame. This
     fraction converted to a frame number which is used by this and
     other programs.
  2. the 'Start_time' prompt is displays which shows the clip number
     (starts with 1) and the auto_time_fill. Several things happen
     depending on what is entered::
       1. If <CR> (the Enter key) is entered this signifies the end of
		  this video and processing begins on the next video.
	   2. If the start time is entered as SS:FF, the auto_time_fill is
          prepended to form a complete HH:MM:SS:FF start time. This is
          intended to save time whcn several clips in the video are on
          the same minute.
	   3. If none of those cases match the start_time ie entered as
          HH:MM:SS:FF format. Again, non-significant leading digits
          can be omitted.
  3. The following are displayed::
	 1. The default duration is displayed by calculating the
        difference between the video length and the start time. This
        is useful when the last clip ends at the end of the video. 
     2. The 'duration (HH:MM:SS:FF): ' prompt is dosplayed. If <CR> is
        entered then the default duration is used. Otherwise the duration
        should entered in HH:MM:SS:FF. If HH:MM: is 0:00 then it can
        be omitted if only SS:FF is entered, leading 0's can be
        omitted.

) run video_clip.py to detect the new videos and record them in the
    database. this program has a default activity that you can see
    when displaying the help string. You can change it to another
    default activity to minimize typing needed
