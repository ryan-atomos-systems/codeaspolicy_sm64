"""Development skill retained from bits_pipe.py; see README.md for evidence and limits."""

from .move import Waypoints
from sm64_policy import Action

class Pipe:

    def __init__(self):
        self.route = Waypoints([(600, -1400), (350, -1800), (350, -2250, 3), (350, -3200), (350, -4250), (350, -4800, 3), (350, -5550, 3), (351, -6030, 3)])

    def act(self, s):
        if s.level != 21:
            return Action()
        return self.route.act(s)
