"""Development skill retained from bits_switch2.py; see README.md for evidence and limits."""

from .move import steer
from sm64_policy import Action
from sm64_policy.control import horizontal_distance, air_steer

class Switch:

    def __init__(self):
        self.points = [(-3800, -900), (-3400, -1000), (-3100, -1400), (-2850, -1700), (-2200, -1700), (-1850, -1450), (-1600, -1100), (-1100, -900), (-280, -900)]
        self.i = 0

    def act(self, s):
        if s.mario.action == 134218571:
            return Action(a=s.frame % 2 == 0)
        if s.mario.action in (1356, 1357, 1359):
            return Action()
        t = self.points[self.i]
        if horizontal_distance(s, t) < 60:
            if self.i == len(self.points) - 1:
                return Action()
            self.i += 1
            t = self.points[self.i]
        return air_steer(s, t, 24) if s.mario.airborne else steer(s, t, 48)
