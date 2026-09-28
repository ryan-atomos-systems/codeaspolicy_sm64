"""Development skill retained from bits_cross3.py; see README.md for evidence and limits."""

from .move import Waypoints
from sm64_policy import Action

class Cross:

    def __init__(self):
        self.route = Waypoints([(-2400, -300), (-1800, -300), (-1550, 0), (-650, 0, 2), (200, 0), (1300, 0, 2), (1900, 0), (2400, 0), (2800, 0)])

    def act(self, s):
        if s.mario.action == 134218571:
            return Action(a=s.frame % 2 == 0)
        if s.mario.action in (1356, 1357, 1359):
            return Action()
        return self.route.act(s)
