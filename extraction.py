#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SYNOPSIS

	python plt2staypoints.py [-h,--help] [-v,--verbose]


DESCRIPTION

	Extract staypoints from a collection of .plt GPS trajectory files.


ARGUMENTS

	-h, --help          show this help message and exit
	-v, --verbose       verbose output


AUTHOR

	Doug McGeehan <djmvfb@mst.edu>


LICENSE

	Copyright 2017 Doug McGeehan - GNU GPLv3

"""
# Extract stay points from a GPS log file, specifically the GeoLife GPS
# trajectory dataset. Available for download here:
#   https://www.microsoft.com/en-us/download/details.aspx?id=52367
#
# Implementation of the staypoint extraction algorithm in
# [1] Q. Li, Y. Zheng, X. Xie, Y. Chen, W. Liu, and W.-Y. Ma,
#       "Mining user similarity based on location history", in the Proceedings
#       of the 16th ACM SIGSPATIAL International Conference on Advances in
#       Geographic Information Systems, New York, NY, USA, 2008,
#       pp. 34:1--34:10.
#       https://doi.org/10.1145/1463434.1463477

# Forked from code written by RustingSword on GitHub
# https://gist.github.com/RustingSword/5215046

import dateutil.parser

__appname__ = "plt2staypoints"
__author__ = "Doug McGeehan"
__version__ = "0.0pre0"
__license__ = "GNU GPLv3"

import progressbar
progressbar.streams.wrap_stderr()

import logging
logger = logging.getLogger(__appname__)

import argparse
import sys
import os
import time

from datetime import datetime
from ctypes import c_double
from ctypes import c_uint64
from ctypes import Structure
from math import radians
from math import cos
from math import sin
from math import asin
from math import sqrt
#from scipy.spatial import distance
#from geopy.distance import vincenty


DEFAULT_GEOLIFE_DIRECTORY = os.path.join(
    os.path.expanduser('~'),
    'Desktop',
    'Research',
    'Geolife Trajectories 1.3'
)


def main(args):
    plt_files = []
    for directory, subdirectories, filenames in os.walk(args.input_directory):
        if 'StayPoint' in directory:
            # Skip any files within the previously created StayPoint directory
            continue

        plt_files_within_directory = filter(lambda p: p.endswith('plt'),
                                            filenames)
        plt_file_paths = map(lambda p: os.path.join(directory, p),
                             plt_files_within_directory)
        plt_files.extend(plt_file_paths)

    plt_file_count = len(plt_files)
    with progressbar.ProgressBar(max_value=plt_file_count) as progress:
        for i, plt_file in enumerate(plt_files, start=1):
            logger.info(plt_file)

            staypoints = StayPointExtractor(plt_file)
            if staypoints:
                spfile = plt_file.replace('Data', 'StayPoint')
                os.makedirs(os.path.dirname(spfile), exist_ok=True)

                spfile_handle = open(spfile, 'w+')
                print(('Extracted stay points:\n'
                       'longitude\t'
                       'laltitude\t'
                       'arriving time\t'
                       'leaving time'),
                      file=spfile_handle)
                for sp in staypoints:
                    print('\t'.join(map(
                        lambda v: str(v),
                        [
                            sp.latitude, sp.longitude,
                            str(time.localtime(sp.arrivTime)),
                            str(time.localtime(sp.leaveTime))
                        ]
                    )),
                        file=spfile_handle
                    )

                spfile_handle.close()

            progress.update(i)

    """
        for filename in filenames:
            if filename.endswith('plt'):
                gpsfile = os.path.join(dirname, filename)
                
    """


class StayPoint(Structure):
    _fields_ = [
        ("longitude", c_double),
        ("latitude", c_double),
        ("arrivTime", c_uint64),
        ("leaveTime", c_uint64)
    ]


# calculate distance between two points from their coordinate
def getDistance(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    m = 6371000 * c
    return m


def computMeanCoord(gpsPoints):
    lon = 0.0
    lat = 0.0
    for point in gpsPoints:
        lon += float(point[0][0])
        lat += float(point[0][1])
    return (lon / len(gpsPoints), lat / len(gpsPoints))


class StayPointExtractor(object):
    # Extract stay points from a GPS log file
    # Input:
    #        file: the name of a GPS log file
    #        distThres: distance threshold
    #        timeThres: time span threshold
    # Default values of distThres and timeThres are 200 m and 30 min respectively,
    #  according to [1]

    def __init__(self, path, distance_threshold=200, time_threshold=20*60):
        staypoints = []
        with open(path) as gps_log:
            # Map raw lines in the GPS log into a tuple of lat, long,
            # and timestamp.
            # e.g.
            # '39.89,116.45,0,157,39925.448611,2009-04-22,10:46:00\n'
            #       is mapped to
            # [(39.89, 116.45), datetime.datetime(2009, 4, 22, 10, 46)]
            points = self.point_extractor(gps_log)
            point_count = len(points)

            i = 0
            while i < point_count - 1:
                point_i = points[i]
            # for i, point_i in enumerate(points):
            #     if i == point_count - 1:
            #         break
            #
            #     for j, point_j in enumerate(points[i+1:]):
                    # distance = vincenty(point_i, point_j).meters
                j = i + 1
                while j < point_count:
                    point_j = points[j]
                    dist = getDistance(*point_i[0],
                                       *point_j[0])

                    if dist > distance_threshold:
                        deltaT = (point_j[1] - point_i[1]).total_seconds()
                        if deltaT > time_threshold:
                            sp = StayPoint()
                            sp.latitude, sp.longitude = computMeanCoord(
                                points[i:j + 1])
                            sp.arrivTime = int(
                                time.mktime(point_i[1].timetuple())
                            )
                            sp.leaveTime = int(
                                time.mktime(point_j[1].timetuple())
                            )
                            staypoints.append(sp)
                        i = j
                        break
                    j += 1
                # Algorithm in [1] lacks following line
                i += 1
        self.staypoints = staypoints

    def point_extractor(self, gps_log):
        # Ignore the first six lines of each file
        valid_lines = filter(lambda x: x[0] >= 6,
                             enumerate(gps_log))
        # Split the lines into seperate fields
        # '39.890275,116.453691,0,157,39925.4486111111,2009-04-22,10:46:00'
        #       mapped to
        # ['39.890275', '116.453691', '0', '157', '39925.4486111111',
        #  '2009-04-22', '10:46:00']
        raw_points = map(lambda line: line[1].rstrip().split(','),
                         valid_lines)
        # Extract only the lat, long, date, and time fields, merging the
        #   date and time fields, and convert to the appropriate data types
        # ['39.890275', '116.453691', '0', '157', '39925.4486111111',
        #  '2009-04-22', '10:46:00']
        #       mapped to
        # [(39.890275, 116.453691), datetime.datetime(2009, 4, 22, 10, 46)]
        LATITUDE_INDEX = 0
        LONGITUDE_INDEX = 1
        DATE_INDEX = -2
        TIME_INDEX = -1
        points = map(
            lambda raw_point: (
                (float(raw_point[LATITUDE_INDEX]),
                 float(raw_point[LONGITUDE_INDEX])),
                dateutil.parser.parse(' '.join([raw_point[DATE_INDEX],
                                                raw_point[TIME_INDEX]]))
            ),
            raw_points
        )
        return list(points)

    def __iter__(self):
        for staypoint in self.staypoints:
            yield staypoint

    def __bool__(self):
        return len(self.staypoints) > 0


def setup_logger(args):
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    # todo: place them in a log directory, or add the time to the log's
    # filename, or append to pre-existing log
    log_file = os.path.join('/tmp', __appname__ + '.log')
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()

    if args.verbose:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)

    # create formatter and add it to the handlers
    line_numbers_and_function_name = logging.Formatter(
        "%(levelname)s [%(filename)s:%(lineno)s - %(funcName)20s() ]"
        "%(message)s")
    fh.setFormatter(line_numbers_and_function_name)
    ch.setFormatter(line_numbers_and_function_name)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)


def existing_directory(path):
    assert os.path.isdir(path), 'The directory {} does not exist. ' \
                                'Aborting.'.format(path)
    return os.path.abspath(path)


def get_arguments():
    parser = argparse.ArgumentParser(
        description="Extract staypoints from a collection of .plt "
                    "GPS trajectory files."
    )
    # during development, I set default to False so I don't have to keep
    # calling this with -v
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False, help='verbose output')
    parser.add_argument('-i', '--input-directory', type=existing_directory,
                        help='directory containing .plt files',
                        required=True)

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    try:
        start_time = datetime.now()

        args = get_arguments()
        setup_logger(args)
        logger.debug('Command-line arguments:')
        for arg in vars(args):
            value = getattr(args, arg)
            logger.debug('\t{argument_key}:\t{value}'.format(argument_key=arg,
                                                           value=value))

        logger.debug(start_time)

        main(args)

        finish_time = datetime.now()
        logger.debug(finish_time)
        logger.debug('Execution time: {time}'.format(
            time=(finish_time - start_time)
        ))
        logger.debug("#" * 20 + " END EXECUTION " + "#" * 20)

        sys.exit(0)

    except KeyboardInterrupt as e:  # Ctrl-C
        raise e

    except SystemExit as e:  # sys.exit()
        raise e

    except Exception as e:
        logger.exception("Something happened and I don't know what to do D:")
        sys.exit(1)
