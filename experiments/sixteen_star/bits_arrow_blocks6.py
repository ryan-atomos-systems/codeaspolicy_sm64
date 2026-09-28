"""Development skill retained from bits_arrow_blocks6.py; see README.md for evidence and limits."""

from .bits_arrow_blocks import Arrow as Base
from sm64_policy import Action
from dataclasses import replace
from .mips_adjust import Adjust
from .move import steer
from .air_landing import air_steer

class Arrow(Base):

    def __init__(self):
        super().__init__()
        self.last_phase = 'position'
        self.adjust = Adjust(-1335, -1140)

    def act(self, s):
        x, y, z = s.position
        if self.index == 3:
            if self.last_phase == 'position':
                if abs(x + 1335) < 12 and abs(z + 1140) < 12:
                    self.last_phase = 'launch'
                else:
                    return self.adjust.act(s)
            if self.last_phase == 'launch':
                if s.mario.airborne:
                    self.last_phase = 'flight'
                else:
                    a = steer(s, (-2160, -1140), 64)
                    if s.mario.action == 75531353:
                        return replace(a, z=True, a=True)
                    if s.mario.forward_velocity > 12:
                        return replace(a, z=s.frame % 2 == 0)
                    return a
            if self.last_phase == 'flight':
                if s.mario.airborne:
                    return air_steer(s, (-2200, -1320) if x > -1930 else (-2200, -1140), 48)
                if y > 2700:
                    self.index = 4
                    self.phase = 'leave'
                else:
                    return Action()
        return super().act(s)
