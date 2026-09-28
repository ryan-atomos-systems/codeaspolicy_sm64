"""Development skill retained from bitfs_middle.py; see README.md for evidence and limits."""

from dataclasses import replace
from .jumproute import JumpRoute
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance
from .move import Waypoints, steer, turning_air

class Middle:

    def __init__(self):
        self.phase = 'elevator'
        self.left = False
        self.exit = JumpRoute([(3100, 410, 700)])
        self.route = Waypoints([(3100, 700), (2650, 700), (2050, 307), (900, 307, 2), (0, 307), (-500, 307, 3), (-1500, 307, 3), (-2400, 307), (-2750, 307), (-3400, 307, 2), (-4300, 307, 2), (-5200, 307), (-5750, 307)])

    def act(self, s):
        if not self.left:
            if s.position[1] > 350:
                self.left = True
            else:
                return Action()
        self.phase = 'middle path'
        t = self.route.points[self.route.index][:2]
        if s.mario.action == 16910519:
            return turning_air(s, t)
        if not self.exit.done:
            return self.exit.act(s)
        if self.route.index == 0:
            self.route.index = 1
        return self.route.act(s)
