"""Development skill retained from bits_loop2.py; see README.md for evidence and limits."""

from .move import Waypoints

class Loop:

    def __init__(self):
        self.route = Waypoints([(7100, -2700), (6500, -2800), (5900, -3000), (5300, -3000), (4600, -3000), (4000, -3000), (3650, -3000), (3650, -2100), (3650, -1300), (3300, -900), (2793, -900)])

    def act(self, s):
        return self.route.act(s)
