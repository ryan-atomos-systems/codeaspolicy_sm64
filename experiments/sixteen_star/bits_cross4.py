"""Development skill retained from bits_cross4.py; see README.md for evidence and limits."""

from .bits_cross3 import Cross as Base
from .move import steer
from dataclasses import replace

class Cross(Base):

    def act(self, s):
        a = super().act(s)
        t = self.route.points[self.route.index]
        if len(t) > 2 and t[2] == 2 and (not s.mario.airborne) and (s.mario.forward_velocity > 16):
            return replace(a, z=True, a=s.mario.action == 75531353)
        return a
