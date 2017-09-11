#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

import time
import os
import sys
from ctypes import *
from math import radians
from math import cos
from math import sin
from math import asin
from math import sqrt

time_format = '%Y-%m-%d,%H:%M:%S'

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
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    m = 6371000 * c
    return m
    
def computMeanCoord(gpsPoints):
    lon = 0.0
    lat = 0.0
    for point in gpsPoints:
        fields = point.rstrip().split(',')
        lon += float(fields[0])
        lat += float(fields[1])
    return (lon/len(gpsPoints), lat/len(gpsPoints))

# Extract stay points from a GPS log file
# Input:
#        file: the name of a GPS log file
#        distThres: distance threshold
#        timeThres: time span threshold
# Default values of distThres and timeThres are 200 m and 30 min respectively,
#  according to [1]

def stayPointExtraction(file, distThres = 200, timeThres = 20*60):
    stayPointList = []
    log = open(file, 'r')
    points = log.readlines()[6:] # first 6 lines are useless
    pointNum = len(points)
    i = 0
    while i < pointNum-1: 
        j = i+1
        while j < pointNum:
            field_pointi = points[i].rstrip().split(',')
            field_pointj = points[j].rstrip().split(',')
            dist = getDistance(float(field_pointi[0]),float(field_pointi[1]),
                               float(field_pointj[0]),float(field_pointj[1]))
            
            if dist > distThres:
                t_i = time.mktime(time.strptime(field_pointi[-2]+','+field_pointi[-1],time_format))
                t_j = time.mktime(time.strptime(field_pointj[-2]+','+field_pointj[-1],time_format))
                deltaT = t_j - t_i
                if deltaT > timeThres:
                    sp = StayPoint()
                    sp.latitude, sp.longitude = computMeanCoord(points[i:j+1])
                    sp.arrivTime, sp.leaveTime = int(t_i), int(t_j)
                    stayPointList.append(sp)
                i = j
                break
            j += 1
        # Algorithm in [1] lacks following line
        i += 1
    return stayPointList


DEFAULT_GEOLIFE_DIRECTORY = os.path.join(
    os.path.expanduser('~'),
    'Desktop',
    'Research',
    'Geolife Trajectories 1.3'
)
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 {} PATH'.format(sys.argv[0]))
        print('Continuing with PATH set to "{}"'.format(
            DEFAULT_GEOLIFE_DIRECTORY
        ))
        geolife_directory = DEFAULT_GEOLIFE_DIRECTORY

    else:
        geolife_directory = os.path.abspath(sys.argv[-1])

    assert os.path.isdir(geolife_directory), (
        'No directory located at {}. Aborting.'.format(geolife_directory)
    )

    for dirname, dirnames, filenames in os.walk(geolife_directory):
        filenum = len(filenames)
        for filename in filenames:
            if filename.endswith('plt'):
                gpsfile = os.path.join(dirname, filename)
                spt = stayPointExtraction(gpsfile) 
                if len(spt) > 0:
                    spfile = gpsfile.replace('Data', 'StayPoint')
                    os.makedirs(os.path.dirname(spfile), exist_ok=True)
                    
                    spfile_handle = open(spfile, 'w+')
                    print(('Extracted stay points:\n'
                          'longitude\t'
                          'laltitude\t'
                          'arriving time\t'
                          'leaving time'),
                          file=spfile_handle)
                    for sp in spt:
                        print('\t'.join(map(
                            lambda v: str(v),
                            [
                                sp.latitude, sp.longitude,
                                time.strftime(time_format,
                                               time.localtime(sp.arrivTime)),
                                time.strftime(time_format,
                                               time.localtime(sp.leaveTime))
                            ]
                            )),
                            file=spfile_handle
                        )

                    spfile_handle.close()
