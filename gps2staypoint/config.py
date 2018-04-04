import os
import datetime


DEFAULT_GEOLIFE_DIRECTORY = os.path.join(
    os.path.expanduser('~'),
    'Desktop',
    'Research',
    'Geolife Trajectories 1.3',
    'Data'
)
GPS_TRAJECTORY_TIME_INTERVAL_THRESHOLD = datetime.timedelta(minutes=20)


class StayPointConfiguration(object):
    TIME_THRESHOLD = datetime.timedelta(minutes=20)
    DISTANCE_THRESHOLD = 200 # meters


class Colors(object):
    distance = 'green'
    time_difference = 'cyan'

