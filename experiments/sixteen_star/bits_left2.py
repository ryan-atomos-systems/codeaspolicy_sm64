"""Development skill retained from bits_left2.py; see README.md for evidence and limits."""

from .move import Waypoints

class Left:

    def __init__(self):
        self.route = Waypoints([(-3100, -900), (-3550, -900, 3), (-4000, -900, 3), (-4800, -900, 2), (-5400, -900), (-6000, -900), (-6500, -900, 3)])

    def act(self, s):
        return self.route.act(s)
