"""Development skill retained from bits_steps3.py; see README.md for evidence and limits."""

from .bits_steps2 import Climb as Base
from sm64_policy import Action
from sm64_policy.control import air_steer
from .move import steer
from dataclasses import replace

class Climb(Base):

    def act(self, s):
        if s.mario.action == 134218571:
            return Action(a=s.frame % 2 == 0)
        if s.mario.action in (1356, 1357, 1359):
            return Action()
        if not s.mario.airborne and s.position[1] > -4350:
            self.phase = 1
        t = (-3050, 0) if self.phase == 0 else (-2600, 0)
        if s.mario.airborne:
            return air_steer(s, t, 32)
        return replace(steer(s, t, 48), a=s.frame % 2 == 0)
