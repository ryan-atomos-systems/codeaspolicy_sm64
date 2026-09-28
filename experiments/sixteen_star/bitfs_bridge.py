"""Development skill retained from bitfs_bridge.py; see README.md for evidence and limits."""

from .move import Waypoints

class Bridge:

    def __init__(self):
        self.route = Waypoints([(4250, 96), (4600, 96), (5000, 96), (5350, 96), (5750, 96), (6500, 96), (6735, 96)])

    def act(self, s):
        return self.route.act(s)
