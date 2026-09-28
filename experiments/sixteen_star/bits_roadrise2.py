"""Development skill retained from bits_roadrise2.py; see README.md for evidence and limits."""

from .move import Waypoints

class Road:

    def __init__(self):
        self.route = Waypoints([(3400, -900), (4300, -900), (4900, -900), (5600, -900), (6500, -900, 3), (7100, -1200, 3), (7100, -2300)])

    def act(self, s):
        return self.route.act(s)
