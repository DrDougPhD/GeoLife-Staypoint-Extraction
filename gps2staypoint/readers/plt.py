import dateutil.parser


class PLTFileReader(object):
    def __init__(self, path):
        with open(path) as gps_log:
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
            LATITUDE_INDEX = 0
            LONGITUDE_INDEX = 1
            DATE_INDEX = -2
            TIME_INDEX = -1
            points = map(
                lambda raw_point: (
                    (float(raw_point[LATITUDE_INDEX]),
                     float(raw_point[LONGITUDE_INDEX])),
                    dateutil.parser.parse(' '.join([raw_point[DATE_INDEX],
                                                    raw_point[TIME_INDEX]]))
                ),
                raw_points
            )
            self.timestamped_locations = list(points)

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