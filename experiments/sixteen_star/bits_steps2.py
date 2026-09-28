"""Development skill retained from bits_steps2.py; see README.md for evidence and limits."""

from sm64_policy import Action
from sm64_policy.control import air_steer
from .move import steer
from dataclasses import replace

class Climb:

    def __init__(self):
        self.phase = 0

    def act(self, s):
        if s.mario.action == 134218571:
            return Action(a=s.frame % 2 == 0)
        if s.mario.action in (1356, 1357, 1359):
            return Action()
        if s.position[0] > -3200 and s.position[1] >= -4321:
            self.phase = 1
        t = (-3300, 0) if self.phase == 0 else (-2700, 0)
        if s.mario.airborne:
            return air_steer(s, t, 24)
        return replace(steer(s, t, 48), a=s.frame % 2 == 0)
