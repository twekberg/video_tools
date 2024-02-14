#!/usr/bin/env python
"""
Use ffprobe from http://ffmpeg.org/ffprobe.html to determine the duration of a video.
"""


import argparse
import subprocess


def build_parser():
    """
    Get command line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('filename', nargs='*',
                        help = 'Compute the length of this video file. '
                        'Specify a drive using drive: format')
    return parser


def main(args):
    """
    Main processing loop.
    """
    for filename in args.filename:
        print(get_length(filename), filename)


def get_length(filename):
    """
    Get the length of the video.
    """
    result = subprocess.Popen(["C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/ffprobe",
                               filename],
                              stdout = subprocess.PIPE,
                              text=True,
                              stderr = subprocess.STDOUT)
    return '\t'.join([x.split(',')[0].split()[1]
                      for x in result.stdout.readlines() if "Duration" in x])


if __name__ == '__main__':
    main(build_parser().parse_args())
