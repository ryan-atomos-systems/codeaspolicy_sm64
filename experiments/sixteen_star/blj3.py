"""Development skill retained from blj3.py; see README.md for evidence and limits."""

import json, math
from .blj import BLJ as Base
from sm64_policy import Action

class BLJ(Base):

    def __init__(self, **k):
        super().__init__(**k)
        self.prev = False

    def act(self, s):
        a = super().act(s)
        if self.phase == 'BLJ' and self.t > 0:
            z = s.position[2]
            next_z = round(1740.8 + (math.floor((z - 1740.8) / 51.2) + 1) * 51.2)
            ready = next_z - z < max(1, -s.mario.forward_velocity * 1.5 * 0.72)
            a = Action(stick_y=-80, z=True, a=not s.mario.airborne and ready and (not self.prev))
        self.prev = a.a
        return a
