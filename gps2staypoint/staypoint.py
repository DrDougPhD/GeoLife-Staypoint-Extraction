import logging
logger = logging.getLogger(__name__)

import numpy
import time

import termcolor
from geopy import distance


class StayPoint(object):
    def __init__(self, points):
        self.constituent_points = list(map(lambda p: p[0],
                                           points))
        staypoint_location = numpy.mean(self.constituent_points,
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

        self._radius = None

    @property
    def duration(self):
        return self.departure_time - self.arrival_time

    @property
    def radius(self):
        if self._radius is None:
            # find the point that is furthest from the staypoint
            max_distance = float('-inf')
            for point in self.constituent_points:
                distance_to_staypoint = distance.vincenty(
                    point,
                    (self.latitude, self.longitude)
                ).meters

                if distance_to_staypoint > max_distance:
                    max_distance = distance_to_staypoint

            self._radius = int(max_distance)+1

        return self._radius

    def __str__(self):
        return ('({0.latitude}, {0.longitude})'
                ' for {0.duration}'
                ' ({0.arrival_time} to'
                ' {0.departure_time}).'
                ' {0.radius} meter radius, {1} raw points.').format(
            self, len(self.constituent_points)
        )

    def dict(self):
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'arrival_time': self.arrival_time_epoch,
            'departure_time': self.departure_time_epoch
        }


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
            yield staypoint

    def __bool__(self):
        return len(self.staypoints) > 0

    def keys(self):
        return self.fields

    def dict(self):
        return [staypoint.dict() for staypoint in self.staypoints]