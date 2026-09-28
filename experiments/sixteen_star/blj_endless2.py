"""Development skill retained from blj_endless2.py; see README.md for evidence and limits."""

import math
from .blj import BLJ as Base
from sm64_policy import Action

class BLJ(Base):

    def __init__(self):
        super().__init__(yaw=0)
        self.prev = False
        self.phase = 'BLJ'
        self.t = 1

    def act(self, s):
        if s.position[2] < -1800:
            return Action()
        a = super().act(s)
        if self.phase == 'BLJ' and self.t > 0:
            z = s.position[2]
            next_z = round(2543.6 + (math.ceil((z - 2543.6) / 51.2) - 1) * 51.2)
            ready = z - next_z < max(1, -s.mario.forward_velocity * 1.5 * 0.72)
            a = Action(stick_y=-80, z=True, a=not s.mario.airborne and ready and (not self.prev))
        self.prev = a.a
        return a
