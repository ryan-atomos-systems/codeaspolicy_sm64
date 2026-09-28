"""Development skill retained from ddd.py; see README.md for evidence and limits."""

import math
from sm64_policy import Action
from .swim import swim

class Sub:

    def __init__(self):
        self.i = 0
        self.phase = 'swim tunnel'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        points = [(-2500, -3600, 0), (-500, -4200, 0), (1500, -3600, 0), (2900, -3800, 0), (4500, 100, 0)]
        if s.area == 1:
            t = points[self.i]
            if math.dist(s.position, t) < 250 and self.i < 4:
                self.i += 1
                t = points[self.i]
            return swim(s, t)
        self.phase = 'sub room'
        return swim(s, (0, -2300, 0) if s.position[0] < 0 else (3900, 300, -600))
