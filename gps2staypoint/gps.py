import logging
import os
from geopy.distance import vincenty

from gps2staypoint import config
from gps2staypoint.staypoint import StaypointBuilder
from gps2staypoint.writers.kml import StaypointKML

logger = logging.getLogger(__name__)


class GPSPoint(object):

    def distance_to(self, point):
        return vincenty(self.location, point.location).meters

    @property
    def location(self):
        return (self.latitude, self.longitude)

    def __str__(self):
        return '({0.latitude}, {0.longitude}) @{0.timestamp}'.format(self)


class GPSTrajectory(object):
    TIME_INTERVAL_THRESHOLD = config.GPS_TRAJECTORY_TIME_INTERVAL_THRESHOLD

    def __init__(self, user, initial_point=None):
        self.user = user
        self._staypoints = None

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
            if time_difference >= self.TIME_INTERVAL_THRESHOLD:
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

    @property
    def staypoints(self):
        if self._staypoints is None:
            builder = StaypointBuilder(trajectory=self)
            self._staypoints = builder.extract_staypoints()
        return self._staypoints

    def write_to_kml(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        filename = 'User{user:0>3}_{start}-{end}.kml'.format(
            user=self.user.id,
            start=self.earliest_time.strftime("%s"),
            end=self.latest_time.strftime("%s"),
        )
        path = os.path.join(directory, filename)
        # logger.debug('Saving trajectory to {}'.format(path))

        kml = StaypointKML(path=path)
        kml.add_trajectory(trajectory=self)
        staypoints = self.staypoints
        if staypoints:
            kml.add_staypoints(staypoints=staypoints)
        kml.save()

    def summarize(self):
        staypoints = self.staypoints
        for staypoint in staypoints:
            logger.debug('\t{}'.format(staypoint))

    def __iter__(self):
        for p in self.points:
            yield p

    def __getitem__(self, index):
        return self.points[index]

    def __len__(self):
        return len(self.points)

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
