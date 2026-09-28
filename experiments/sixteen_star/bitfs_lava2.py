"""Development skill retained from bitfs_lava2.py; see README.md for evidence and limits."""

from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer
from .move import Waypoints, steer, turning_air

class Lava2:

    def __init__(self):
        self.phase = 'cross upper lava'
        self.route = Waypoints([(-5400, 300), (-4450, 300), (-50, 500)])

    def act(self, s):
        t = self.route.points[self.route.index][:2]
        if self.route.index < 2:
            return self.route.act(s)
        if s.position[0] > -180:
            return air_steer(s, t, 32) if s.mario.airborne else replace(steer(s, t), a=s.frame % 2 == 0)
        if s.mario.action == 16910519:
            return turning_air(s, t)
        if s.mario.airborne:
            return air_steer(s, t, 48)
        a = steer(s, t)
        if s.mario.action == 75531353:
            return replace(a, z=True, a=True)
        if s.mario.forward_velocity > 18:
            return replace(a, z=True)
        return a
