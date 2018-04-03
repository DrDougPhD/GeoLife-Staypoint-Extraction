import logging
import os

from gps2staypoint.staypoint import StaypointBuilder
from gps2staypoint.writers.kml import StaypointKML

logger = logging.getLogger(__name__)

from geopy.distance import vincenty


class GPSPoint(object):
    def __str__(self):
        return '({0.latitude}, {0.longitude}) @{0.timestamp}'.format(self)

    def distance_to(self, point):
        return vincenty(self.location, point.location).meters

    @property
    def location(self):
        return (self.latitude, self.longitude)


class GPSTrajectory(object):
    def __init__(self, time_interval_threshold, user, initial_point=None):
        self.threshold = time_interval_threshold
        self.user = user

        self.points = []
        if initial_point is not None:
            self.points.append(initial_point)

    def add_point(self, point):
        if not self.points:
            self.points.append(point)
            return True

        else:
            time_difference = point.timestamp - self.latest_time
            # logger.debug('Time difference between points: {}'.format(time_difference))
            if time_difference >= self.threshold:
                return False

            else:
                self.points.append(point)
                return True

    @property
    def latest_time(self):
        return self.points[-1].timestamp

    @property
    def earliest_time(self):
        return self.points[0].timestamp

    def staypoints(self, distance_threshold, time_threshold):
        builder = StaypointBuilder(trajectory=self,
                                   distance_threshold=distance_threshold,
                                   time_threshold=time_threshold)
        return builder.extract_staypoints()

    def write_to_kml(self, directory, staypoints=None):
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        filename = 'User{user:0>3}_{start}-{end}.kml'.format(
            user=self.user.id,
            start=self.earliest_time.strftime("%s"),
            end=self.latest_time.strftime("%s"),
        )
        kml = StaypointKML(path=os.path.join(directory, filename))
        kml.add_trajectory(trajectory=self)

        if staypoints is not None:
            kml.add_staypoints(staypoints=staypoints)

        kml.save()


    def __iter__(self):
        for p in self.points:
            yield p

    def __str__(self):
        start = self.earliest_time
        end = self.latest_time
        return '{point_count: >4} points, {start} to {end} ' \
               '({time_difference})'.format(
            point_count=len(self.points),
            start=start,
            end=end,
            time_difference=end-start,
        )
