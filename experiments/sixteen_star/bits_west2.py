"""Development skill retained from bits_west2.py; see README.md for evidence and limits."""

from .move import Waypoints, steer
from sm64_policy import Action
from dataclasses import replace
from .air_landing import air_steer

class West:

    def __init__(self):
        self.route = Waypoints([(-2800, -900), (-3600, -900), (-3800, -900), (-4700, -900, 2), (-5100, -1100), (-6100, -1100, 2), (-6460, -905)])
        self.phase = 'cross octagons'

    def act(self, s):
        if s.mario.on_pole:
            return Action(stick_y=80)
        if self.route.done:
            return replace(steer(s, (-6460, -905), 40), a=s.frame % 2 == 0)
        t = self.route.points[self.route.index]
        if s.mario.airborne:
            return air_steer(s, t[:2], 48)
        a = self.route.act(s)
        if len(t) > 2 and t[2] == 2 and (s.mario.action == 67109952) and (s.mario.forward_velocity > 16):
            return replace(a, z=s.frame % 2 == 0)
        return a
