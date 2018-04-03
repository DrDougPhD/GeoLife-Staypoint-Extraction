import logging
import os

logger = logging.getLogger(__name__)

import dateutil.parser


class PLTFileReader(object):
    LATITUDE_INDEX = 0
    LONGITUDE_INDEX = 1
    DATE_INDEX = -2
    TIME_INDEX = -1

    USER_ID_INDEX = -3

    def __init__(self, path):
        self.path = path
        self.timestamped_locations = None

        # extract useful information from file
        self.user = int(path.split(os.sep)[self.USER_ID_INDEX])

        # get the first timestamp of the first record in the file
        file = self.open()
        first_line = next(file)
        file.close()

        split_line = self.split_line(line=first_line)

        self.start_time = split_line['timestamp']

    def open(self):
        '''Open .plt file and skip the first few lines.'''
        gps_log = open(self.path)
        for _ in range(6):
            next(gps_log)
        return gps_log

    def load(self):
        with open(self.path) as gps_log:
            # Ignore the first six lines of each file
            valid_lines = filter(lambda x: x[0] >= 6,
                                 enumerate(gps_log))
            # Split the lines into seperate fields
            # '39.890275,116.453691,0,157,39925.4486111111,2009-04-22,10:46:00'
            #       mapped to
            # ['39.890275', '116.453691', '0', '157', '39925.4486111111',
            #  '2009-04-22', '10:46:00']
            raw_points = map(lambda line: line[1].rstrip().split(','),
                             valid_lines)
            # Extract only the lat, long, date, and time fields, merging the
            #   date and time fields, and convert to the appropriate data types
            # ['39.890275', '116.453691', '0', '157', '39925.4486111111',
            #  '2009-04-22', '10:46:00']
            #       mapped to
            # [(39.890275, 116.453691), datetime.datetime(2009, 4, 22, 10, 46)]
            points = map(
                lambda raw_point: (
                    (float(raw_point[self.LATITUDE_INDEX]),
                     float(raw_point[self.LONGITUDE_INDEX])),
                    dateutil.parser.parse(' '.join([
                        raw_point[self.DATE_INDEX],
                        raw_point[self.TIME_INDEX]
                    ]))
                ),
                raw_points
            )
            self.timestamped_locations = list(points)

    def split_line(self, line):
        split_line = line.rstrip().split(',')
        return {
            'latitude': float(split_line[self.LATITUDE_INDEX]),
            'longitude': float(split_line[self.LONGITUDE_INDEX]),
            'timestamp': dateutil.parser.parse(' '.join([
                        split_line[self.DATE_INDEX],
                        split_line[self.TIME_INDEX]
            ]))
        }

    def __getitem__(self, key):
        # if isinstance(key, slice):
        #     pass
        #
        # else:
        #     pass
        return self.timestamped_locations[key]

    @property
    def point_count(self):
        return len(self.timestamped_locations)

    def long_lat_pairs(self):
        return list(map(lambda p: (p[0][1], p[0][0]),
                        self.timestamped_locations))