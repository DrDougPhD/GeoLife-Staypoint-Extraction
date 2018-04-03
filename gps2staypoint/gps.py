import logging
logger = logging.getLogger(__name__)


class GPSPoint(object):
    def __str__(self):
        return '({0.latitude}, {0.longitude}) @{0.timestamp}'.format(self)


class GPSTrajectory(object):
    def __init__(self, time_interval_threshold, initial_point=None):
        self.threshold = time_interval_threshold

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

    def __str__(self):
        start = self.points[0].timestamp
        end = self.latest_time
        return '{point_count: >4} points, {start} to {end} ' \
               '({time_difference})'.format(
            point_count=len(self.points),
            start=start,
            end=end,
            time_difference=end-start,
        )
