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
STAYPOINT_TIME_THRESHOLD = datetime.timedelta(minutes=20)
STAYPOINT_DISTANCE_THRESHOLD = 200


class Colors:
    distance = 'green'
    time_difference = 'cyan'

