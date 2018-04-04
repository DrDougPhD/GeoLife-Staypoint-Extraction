import logging
logger = logging.getLogger(__name__)

import simplekml
from geopy import distance
from polycircles import polycircles

from gps2staypoint.utils import smallestenclosingcircle

class StaypointKML(object):
    def __init__(self, path):
        self.path = path
        self.kml = simplekml.Kml()

    def add_trajectory(self, trajectory):
        points = map(
            lambda p: tuple(reversed(p.location)),
            trajectory
        )
        for p in trajectory:
            point = self.kml.newpoint(name=str(p.timestamp))
            point.coords = [tuple(reversed(p.location))]

        line = self.kml.newlinestring(
            name='Trajectory',
            description='Raw GPS trajectory',
            coords=points
        )

    def add_staypoints(self, staypoints):
        for staypoint in staypoints:
            staypoint_points = map(
                lambda p: p.location,
                staypoint.points
            )
            lat, long, radius = smallestenclosingcircle.make_circle(
                staypoint_points
            )
            western_most_point_on_circle = (lat, long-radius)
            radius_in_meters = distance.vincenty(
                western_most_point_on_circle,
                staypoint.location
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
                              coords=[tuple(reversed(staypoint.location))])

    def save(self):
        logger.info('Saving KML to {}'.format(self.path))
        self.kml.save(self.path)