"""Development skill retained from ddd_board.py; see README.md for evidence and limits."""

from .ddd import Sub
from .swim import swim
from .move import Waypoints, steer
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance
from dataclasses import replace

class Board:

    def __init__(self):
        self.phase = 'swim dock'
        self.on = False
        self.route = Waypoints([(6800, 2000), (6100, 2000, 3), (5700, 2000, 3), (5300, 2000, 3), (4900, 2000, 3), (4200, 1900), (3900, -600, 3)])

    def act(self, s):
        if s.mario.swimming:
            return swim(s, (6800, 500, 2000))
        if s.mario.airborne:
            return air_steer(s, self.route.points[self.route.index][:2], 24)
        self.phase = 'switch and boxes'
        return self.route.act(s)
