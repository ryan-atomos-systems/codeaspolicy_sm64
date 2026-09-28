"""Development skill retained from bitfs_cage3.py; see README.md for evidence and limits."""

from .bitfs_cages import Cages
from sm64_policy import Action
from sm64_policy.control import air_steer
from .move import Waypoints, steer
from dataclasses import replace

class Third(Cages):

    def __init__(self):
        super().__init__()
        self.i = 2
        self.pre = Waypoints([(2400, 96), (2700, 96)])

    def act(self, s):
        if not self.pre.done:
            if s.mario.airborne:
                return air_steer(s, self.pre.points[self.pre.index][:2], 18)
            return self.pre.act(s)
        return super().act(s)
