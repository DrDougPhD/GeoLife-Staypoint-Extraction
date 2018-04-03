import logging
logger = logging.getLogger(__name__)


class GPSUser(object):
    def __init__(self, id):
        self.id = id
        self.trajectories = []

    def add_plt_file(self, plt):
        self.trajectories.append(plt)

    def sort_trajectories_by_time(self):
        self.trajectories.sort(key=lambda p: p.start_time)