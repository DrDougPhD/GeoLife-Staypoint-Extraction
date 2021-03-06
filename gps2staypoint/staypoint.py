import logging

from gps2staypoint import config

logger = logging.getLogger(__name__)


class StayPoint(config.StayPointConfiguration):
    def __init__(self, initial_point=None):
        self.points = []
        if initial_point is not None:
            self.points.append(initial_point)

    def add_point(self, point):
        if not self.points:
            self.points.append(point)
            return True

        else:
            first_point = self.points[0]
            distance = first_point.distance_to(point)
            # logger.debug('\tDistance: {}'.format(distance))
            if distance > self.DISTANCE_THRESHOLD:
                return False

            else:
                self.points.append(point)
                return True

    def is_valid(self):
        first_point = self.points[0]
        last_point = self.points[-1]
        time_difference = last_point.timestamp - first_point.timestamp
        # logger.debug('Time difference between first and last points: '
        #              '{}'.format(time_difference))
        # logger.debug(self.TIME_THRESHOLD)
        if time_difference >= self.TIME_THRESHOLD:
            return True
        else:
            return False

    @property
    def location(self):
        return (self.average_latitude, self.average_longitude)

    @property
    def average_latitude(self):
        summed_latitudes = sum(map(
            lambda p: p.latitude,
            self.points
        ))
        return summed_latitudes / len(self.points)

    @property
    def average_longitude(self):
        summed_longitudes = sum(map(
            lambda p: p.longitude,
            self.points
        ))
        return summed_longitudes / len(self.points)

    @property
    def arrival(self):
        return self.points[0].timestamp

    @property
    def departure(self):
        return self.points[-1].timestamp

    @property
    def duration(self):
        return self.departure - self.arrival

    def __str__(self):
        return '{0.location} from {0.arrival} to {0.departure} ' \
               '({0.duration})'.format(
            self
        )


class StaypointBuilder(object):
    def __init__(self, trajectory):
        self.trajectory = trajectory

    def extract_staypoints(self):
        # logger.debug('\tExtracting staypoints')

        staypoints = []
        staypoint = StayPoint()
        skipped_staypoints = 0

        for point in self.trajectory:
            point_added = staypoint.add_point(point=point)

            if not point_added:
                if staypoint.is_valid():
                    # logger.debug('\t{}'.format(staypoint))
                    staypoints.append(staypoint)

                else:
                    skipped_staypoints += 1

                staypoint = StayPoint(initial_point=point)

        if staypoints:
            logger.debug('{: >4} detected staypoints,'
                         '{: >4} skipped staypoints'.format(
                len(staypoints),
                skipped_staypoints,
            ))

        return staypoints

    def _extract_staypoints(self):
        logger.debug('Extracting staypoints')
        staypoints = []
        skip_points_before_index = 0
        trajectory_length = len(self.trajectory)

        for i, starting_point in enumerate(self.trajectory):
            # Skip trying to create a staypoint starting at the last point
            if i + 1 == trajectory_length:
                break

            if i < skip_points_before_index:
                logger.debug('Skipping point #{}'.format(i))
                continue

            logger.debug('Building new point at #{}'.format(i))
            staypoint = StayPoint(initial_point=starting_point)

            # Build up the staypoint starting from points immediately after
            # the starting point
            for j in range(i + 1, trajectory_length):
                next_point = self.trajectory[j]
                point_added = staypoint.add_point(point=next_point)

                # If this point cannot be a part of the current staypoint,
                # then check if the current staypoint is valid.
                if point_added:
                    # logger.debug('\tAdded #{}: {}'.format(j, next_point))
                    pass

                else:
                    logger.debug('\tStaypoint finished.')
                    if staypoint.is_valid():
                        logger.debug('\tValid staypoint!')
                        logger.debug('\t{}'.format(staypoint))
                        staypoints.append(staypoint)
                        skip_points_before_index = j

                        logger.debug('')
                    else:
                        logger.debug('\tInvalid staypoint.')

                    break

        if staypoints:
            logger.debug(
                '{: >4} detected staypoints'.format(len(staypoints)))

        return staypoints

    #     self.constituent_points = list(map(lambda p: p[0],
    #                                        points))
    #     staypoint_location = numpy.mean(self.constituent_points,
    #                                     axis=0)
    #     latitude = staypoint_location[0]
    #     longitude = staypoint_location[1]
    #
    #     arrival_timestamp = points[0][1]
    #     arrival_timestamp_epoch = int(
    #         time.mktime(arrival_timestamp.timetuple())
    #     )
    #
    #     departure_timestamp = points[-1][1]
    #     departure_timestamp_epoch = int(
    #         time.mktime(departure_timestamp.timetuple())
    #     )
    #     self.latitude = latitude
    #     self.longitude = longitude
    #     self.arrival_time = arrival_timestamp
    #     self.arrival_time_epoch = arrival_timestamp_epoch
    #
    #     self.departure_time = departure_timestamp
    #     self.departure_time_epoch = departure_timestamp_epoch
    #
    #     self._radius = None
    #
    # @property
    # def duration(self):
    #     return self.departure_time - self.arrival_time
    #
    # @property
    # def radius(self):
    #     if self._radius is None:
    #         # find the point that is furthest from the staypoint
    #         max_distance = float('-inf')
    #         for point in self.constituent_points:
    #             distance_to_staypoint = distance.vincenty(
    #                 point,
    #                 (self.latitude, self.longitude)
    #             ).meters
    #
    #             if distance_to_staypoint > max_distance:
    #                 max_distance = distance_to_staypoint
    #
    #         self._radius = int(max_distance)+1
    #
    #     return self._radius
    #
    # def __str__(self):
    #     return ('({0.latitude}, {0.longitude})'
    #             ' for {0.duration}'
    #             ' ({0.arrival_time} to'
    #             ' {0.departure_time}).'
    #             ' {0.radius} meter radius, {1} raw points.').format(
    #         self, len(self.constituent_points)
    #     )
    #
    # def dict(self):
    #     return {
    #         'latitude': self.latitude,
    #         'longitude': self.longitude,
    #         'arrival_time': self.arrival_time_epoch,
    #         'departure_time': self.departure_time_epoch
    #     }


# class StayPointExtractor(object):
#     # Extract stay points from a GPS log file
#     # Default values of distance_threshold and time_threshold are 200m and
#     #  30 min, respectively, according to [1].
#
#     fields = ['latitude', 'longitude',
#               'arrival_time', 'departure_time']
#
#     def __init__(self, trajectory, distance_threshold=200,
#                  time_threshold=20*60):
#         staypoints = []
#         # # Map raw lines in the GPS trajectory into a tuple of lat, long,
#         # # and timestamp.
#         # # e.g.
#         # # '39.89,116.45,0,157,39925.448611,2009-04-22,10:46:00\n'
#         # #       is mapped to
#         # # [(39.89, 116.45), datetime.datetime(2009, 4, 22, 10, 46)]
#         # points = self.point_extractor(trajectory=trajectory)
#         # point_count = len(points)
#
#         point_count = trajectory.point_count
#         i = 0
#         while i < point_count - 1:
#             candidate_arrival = trajectory[i]
#
#             j = i + 1
#             while j < point_count:
#                 candidate_departure = trajectory[j]
#                 dist = distance.vincenty(candidate_arrival[0],
#                                          candidate_departure[0]).meters
#
#                 if dist > distance_threshold:
#                     if j == i+1:
#                         i = j
#                         break
#
#                     else:
#                         duration = candidate_departure[1] - trajectory[j-1][1]
#
#                         if duration.total_seconds() >= time_threshold:
#                             staypoint = StayPoint(points=trajectory[i:j])
#                             staypoints.append(staypoint)
#
#                             logger.debug(str(staypoint))
#
#                         i = j
#                         break
#
#                 j += 1
#
#             # Algorithm in [1] lacks following line
#             i += 1
#
#         self.staypoints = staypoints
#         logger.info('{} staypoints extracted'.format(termcolor.colored(
#             len(staypoints), 'green', attrs=['bold']
#         )))
#
#     def __iter__(self):
#         for staypoint in self.staypoints:
#             yield staypoint
#
#     def __bool__(self):
#         return len(self.staypoints) > 0
#
#     def keys(self):
#         return self.fields
#
#     def dict(self):
#         return [staypoint.dict() for staypoint in self.staypoints]