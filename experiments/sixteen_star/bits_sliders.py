"""Development skill retained from bits_sliders.py; see README.md for evidence and limits."""

from .move import Waypoints, steer
from sm64_policy import Action
from .air_landing import air_steer
from dataclasses import replace

class Sliders:

    def __init__(self):
        self.route = Waypoints([(-4480, -905), (-3326, -905, 2)])
        self.phase = 'jump to pole'

    def act(self, s):
        if s.mario.on_pole:
            return Action(stick_y=80)
        if s.mario.airborne:
            return air_steer(s, (-3326, -905), 48)
        a = self.route.act(s)
        if self.route.index == 1 and s.mario.action == 67109952 and (s.mario.forward_velocity > 16):
            return replace(a, z=s.frame % 2 == 0)
        if self.route.done:
            return replace(steer(s, (-3326, -905)), a=s.frame % 2 == 0)
        return a
