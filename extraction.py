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

__appname__ = "gps2staypoint"
__author__ = "Doug McGeehan"
__version__ = "0.0pre0"
__license__ = "GNU GPLv3"

import progressbar

progressbar.streams.wrap_stderr()

import logging

logger = logging.getLogger(__appname__)

import csv
import argparse
import sys
import os
from datetime import datetime

from gps2staypoint.readers.plt import PLTFileReader
from gps2staypoint.staypoint import StayPointExtractor
from gps2staypoint.writers.kml import StaypointKML

DEFAULT_GEOLIFE_DIRECTORY = os.path.join(
    os.path.expanduser('~'),
    'Desktop',
    'Research',
    'Geolife Trajectories 1.3',
    'DataTest'
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
                    staypoint_file_writer.writerows(staypoints.dict())

                if args.kml:
                    kml_file_path = staypoint_file_path.replace('.plt', '.kml')
                    kml = StaypointKML(staypoints=staypoints,
                                       raw_plt_file=plt_file_path)
                    kml.save_to(path=kml_file_path)

            logger.info('')
            progress.update(i)


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
