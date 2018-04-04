import logging
import progressbar
from geopy.distance import vincenty

from gps2staypoint.gps import GPSTrajectory
from gps2staypoint.utils import colorize

logger = logging.getLogger(__name__)


class GPSUser(object):
    def __init__(self, id):
        self.id = id
        self.gps_logs = []

    def add_plt_file(self, plt):
        self.gps_logs.append(plt)

    def sort_trajectories_by_time(self):
        self.gps_logs.sort(key=lambda p: p.start_time)

    def trajectories(self, time_interval_threshold):
        '''Split GPS logs into trajectories, determined by the time 
        difference between two consecutive GPS records exceeding the defined 
        threshold.
        '''

        trajectory = GPSTrajectory(
            time_interval_threshold=time_interval_threshold,
            user=self,
        )
        for log in self.gps_logs:
            logger.debug('Reading {}'.format(log.path))
            with progressbar.ProgressBar(max_value=len(log)) as progress:
                for i, gps_record in enumerate(log, start=1):
                    point_added = trajectory.add_point(point=gps_record)
                    if not point_added:

                        # Print out information about the change in trajectory
                        last_point_of_trajectory = trajectory.points[-1]
                        time_difference = gps_record.timestamp\
                                        - last_point_of_trajectory.timestamp
                        distance = vincenty(
                            last_point_of_trajectory.location,
                            gps_record.location
                        ).meters
                        logger.debug('Trajectory: {}'.format(trajectory))
                        logger.debug('\t{} meters, {} time diff to new '
                                     'trajectory'.format(
                            colorize.distance(distance),
                            colorize.time_difference(time_difference)
                        ))
                        logger.debug('\t{} to {}'.format(
                            last_point_of_trajectory.location,
                            gps_record.location,
                        ))
                        logger.debug('\t{} to {}'.format(
                            last_point_of_trajectory.timestamp,
                            gps_record.timestamp
                        ))
                        logger.debug('')

                        # Yield the previous trajectory and create a new one
                        yield trajectory
                        trajectory = GPSTrajectory(
                            time_interval_threshold=time_interval_threshold,
                            initial_point=gps_record,
                            user=self,
                        )

                    progress.update(i)
