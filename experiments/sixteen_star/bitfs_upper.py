"""Development skill retained from bitfs_upper.py; see README.md for evidence and limits."""

from dataclasses import replace
from sm64_policy import Action
from .move import Waypoints, steer, turning_air
from sm64_policy.control import air_steer

class Upper:

    def __init__(self):
        self.phase = 'leave stretching ramps'
        self.left = False
        self.route = Waypoints([(-6100, 350), (-6500, 350, 1), (-7100, 300), (-7200, -850), (-6500, -850), (-5600, -400), (-5400, 300), (-4400, 96), (-3300, 96, 2), (-2400, 96, 2), (-1400, 96, 2), (0, 96, 2)])

    def act(self, s):
        if not self.left:
            if s.position[1] > 2850:
                self.left = True
            else:
                return Action()
        t = self.route.points[self.route.index][:2]
        if s.mario.action == 16910519:
            return turning_air(s, t)
        return self.route.act(s)
