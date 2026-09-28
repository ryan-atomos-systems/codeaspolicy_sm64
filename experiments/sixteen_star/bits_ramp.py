"""Development skill retained from bits_ramp.py; see README.md for evidence and limits."""

from .move import Waypoints

class Ramp:

    def __init__(self):
        self.route = Waypoints([(3600, 0), (4800, 0), (5850, 0), (6250, -900), (6000, -1800), (5200, -1800), (4300, -1800, 2), (3200, -1800, 2), (2000, -1800), (1700, -1200), (1700, -700), (500, -700, 2), (0, -700)])

    def act(self, s):
        return self.route.act(s)
