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
import csv

import dateutil.parser
import numpy
import simplekml as simplekml
import termcolor as termcolor
from geopy import distance

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

        # Only consider .plt files
        plt_files_within_directory = filter(lambda p: p.endswith('.plt'),
                                            filenames)

        # Prepend a file's directory to each filename
        plt_file_paths = map(lambda p: os.path.join(directory, p),
                             plt_files_within_directory)

        plt_files.extend(plt_file_paths)

    plt_file_count = len(plt_files)
    with progressbar.ProgressBar(max_value=plt_file_count) as progress:
        # Iterate over each plt file
        for i, plt_file_path in enumerate(plt_files, start=1):
            logger.info(plt_file_path)
            plt = PLTFileReader(path=plt_file_path)

            # Extract the staypoints from the GPS trajectory of this file
            staypoints = StayPointExtractor(trajectory=plt)

            if staypoints:

                # Write out staypoints to a new file
                staypoint_file_path = plt_file_path.replace('Data', 'StayPoint')
                os.makedirs(os.path.dirname(staypoint_file_path), exist_ok=True)

                with open(staypoint_file_path, 'w+') as staypoint_file:
                    staypoint_file_writer = csv.DictWriter(
                        staypoint_file,
                        fieldnames=staypoints.keys()
                    )
                    staypoint_file_writer.writeheader()
                    staypoint_file_writer.writerows(staypoints)

                if args.kml:
                    kml_file_path = staypoint_file_path.replace('.plt', '.kml')
                    kml = StaypointKML(staypoints=staypoints,
                                       raw_plt_file=plt_file_path)
                    kml.save_to(path=kml_file_path)

            logger.info('')
            progress.update(i)


class StayPoint(object):
    def __init__(self, points):
        constituent_points = list(map(lambda p: p[0],
                                      points))
        staypoint_location = numpy.mean(constituent_points,
                                        axis=0)
        latitude = staypoint_location[0]
        longitude = staypoint_location[1]

        arrival_timestamp = points[0][1]
        arrival_timestamp_epoch = int(
            time.mktime(arrival_timestamp.timetuple())
        )

        departure_timestamp = points[-1][1]
        departure_timestamp_epoch = int(
            time.mktime(departure_timestamp.timetuple())
        )
        self.latitude = latitude
        self.longitude = longitude
        self.arrival_time = arrival_timestamp
        self.arrival_time_epoch = arrival_timestamp_epoch

        self.departure_time = departure_timestamp
        self.departure_time_epoch = departure_timestamp_epoch

    @property
    def duration(self):
        return self.departure_time - self.arrival_time

    def __str__(self):
        return ('({0.latitude}, {0.longitude})'
                ' for {0.duration}'
                ' ({0.arrival_time} to'
                ' {0.departure_time})').format(self)

    def dict(self):
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'arrival_time': self.arrival_time_epoch,
            'departure_time': self.departure_time_epoch
        }


class PLTFileReader(object):
    def __init__(self, path):
        with open(path) as gps_log:
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
            self.timestamped_locations = list(points)

    def __getitem__(self, key):
        # if isinstance(key, slice):
        #     pass
        #
        # else:
        #     pass
        return self.timestamped_locations[key]

    @property
    def point_count(self):
        return len(self.timestamped_locations)

    def long_lat_pairs(self):
        return list(map(lambda p: (p[0][1], p[0][0]),
                        self.timestamped_locations))


class StaypointKML(object):
    def __init__(self, staypoints, raw_plt_file):
        logger.info('Creating KML file')
        plt = PLTFileReader(path=raw_plt_file)

        self.kml = simplekml.Kml()
        self.add_raw_gps_trajectory(plt_file=plt)
        self.add_staypoints(staypoints)

    def save_to(self, path):
        logger.info('Saving KML to {}'.format(path))
        self.kml.save(path)

    def add_raw_gps_trajectory(self, plt_file):
        trajectory = self.kml.newlinestring(
            name='Trajectory',
            description='Raw GPS trajectory',
            coords=plt_file.long_lat_pairs())
        return trajectory

    def add_staypoints(self, staypoints):
        pass


class StayPointExtractor(object):
    # Extract stay points from a GPS log file
    # Default values of distance_threshold and time_threshold are 200m and
    #  30 min, respectively, according to [1].

    fields = ['latitude', 'longitude',
              'arrival_time', 'departure_time']

    def __init__(self, trajectory, distance_threshold=200,
                 time_threshold=20*60):
        staypoints = []
        # # Map raw lines in the GPS trajectory into a tuple of lat, long,
        # # and timestamp.
        # # e.g.
        # # '39.89,116.45,0,157,39925.448611,2009-04-22,10:46:00\n'
        # #       is mapped to
        # # [(39.89, 116.45), datetime.datetime(2009, 4, 22, 10, 46)]
        # points = self.point_extractor(trajectory=trajectory)
        # point_count = len(points)

        point_count = trajectory.point_count
        i = 0
        while i < point_count - 1:
            candidate_arrival = trajectory[i]

            j = i + 1
            while j < point_count:
                candidate_departure = trajectory[j]
                dist = distance.vincenty(candidate_arrival[0],
                                         candidate_departure[0]).meters

                if dist > distance_threshold:
                    duration = candidate_departure[1] - candidate_arrival[1]

                    if duration.total_seconds() > time_threshold:
                        staypoint = StayPoint(points=trajectory[i:j+1])
                        staypoints.append(staypoint)

                        logger.debug(str(staypoint))

                    i = j
                    break

                j += 1

            # Algorithm in [1] lacks following line
            i += 1

        self.staypoints = staypoints
        logger.info('{} staypoints extracted'.format(termcolor.colored(
            len(staypoints), 'green', attrs=['bold']
        )))

    def __iter__(self):
        for staypoint in self.staypoints:
            yield staypoint.dict()

    def __bool__(self):
        return len(self.staypoints) > 0

    def keys(self):
        return self.fields


def setup_logger(args):
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
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
        " %(message)s")
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
                        default=True, help='verbose output')
    parser.add_argument('-i', '--input-directory', type=existing_directory,
                        help='directory containing .plt files',
                        default=existing_directory(DEFAULT_GEOLIFE_DIRECTORY))
    parser.add_argument('--kml', action='store_true',
                        help='also create .kml files (default: False)',
                        default=True)

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
