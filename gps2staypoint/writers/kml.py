import logging
logger = logging.getLogger(__name__)

import simplekml
from geopy import distance
from polycircles import polycircles

from gps2staypoint.readers.plt import PLTFileReader
from gps2staypoint.utils import smallestenclosingcircle


class StaypointKML(object):
    def __init__(self, staypoints, raw_plt_file):
        logger.info('Creating KML file')
        plt = PLTFileReader(path=raw_plt_file)

        self.kml = simplekml.Kml()
        self.add_trajectory(trajectory=plt.long_lat_pairs())
        self.add_staypoints(staypoints)

    def save_to(self, path):
        logger.info('Saving KML to {}'.format(path))
        self.kml.save(path)

    def add_trajectory(self, trajectory):
        trajectory = self.kml.newlinestring(
            name='Trajectory',
            description='Raw GPS trajectory',
            coords=trajectory)
        return trajectory

    def add_staypoints(self, staypoints):
        for staypoint in staypoints:
            staypoint_location = (staypoint.longitude, staypoint.latitude)

            lat, long, radius = smallestenclosingcircle.make_circle(
                staypoint.constituent_points
            )
            western_most_point_on_circle = (long-radius, lat)
            radius_in_meters = distance.vincenty(
                western_most_point_on_circle,
                staypoint_location
            ).meters
            polycircle = polycircles.Polycircle(latitude=lat,
                                                longitude=long,
                                                radius=radius_in_meters,
                                                number_of_vertices=36)
            pol = self.kml.newpolygon(name="Staypoint vicinity",
                                      outerboundaryis=polycircle.to_kml())
            pol.style.polystyle.color = \
                simplekml.Color.changealphaint(30, simplekml.Color.green)

            self.kml.newpoint(name="Staypoint",
                              coords=[staypoint_location])
