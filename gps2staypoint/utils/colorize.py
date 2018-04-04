import logging
import termcolor

from gps2staypoint import config

logger = logging.getLogger(__name__)


def distance(s):
    return termcolor.colored(
        '{:.2f}'.format(s),
        config.Colors.distance
    )


def time_difference(s):
    return termcolor.colored(s, config.Colors.time_difference)
