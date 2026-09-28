"""Development skill retained from bits_wheel_exit.py; see README.md for evidence and limits."""

import math
from sm64_policy import Action
from .move import steer
from .air_landing import air_steer
from dataclasses import replace

class Exit:

    def __init__(self):
        self.ready = False

    def act(self, s):
        if not self.ready:
            if s.position[0] < -1800 and s.position[1] > -1050:
                self.ready = True
            else:
                return Action()
        target = (-2750, -900)
        if s.mario.airborne:
            return air_steer(s, target, 48)
        if s.position[0] < -2570 and s.position[1] > -1400:
            return Action()
        a = steer(s, target)
        if s.mario.action == 75531353:
            return replace(a, z=True, a=True)
        if s.mario.action == 67109952 and s.mario.forward_velocity > 14:
            return replace(a, z=s.frame % 2 == 0)
        return a
