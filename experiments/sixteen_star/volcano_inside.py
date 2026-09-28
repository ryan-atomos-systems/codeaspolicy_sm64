"""Development skill retained from volcano_inside.py; see README.md for evidence and limits."""

from dataclasses import replace
from .move import steer
from sm64_policy import Action
from .move import Waypoints
from sm64_policy.control import air_steer, horizontal_distance

class Inside:

    def __init__(self):
        self.route = Waypoints([(-1100, -1150), (0, -1450, 2), (800, -1450), (1150, -1900), (1500, -2100), (2200, -1800, 1), (2550, -900), (2800, 0), (2800, 600), (2600, 1200), (2100, 1800), (1450, 2300, 1), (0, 2600, 1), (-500, 2550), (-1100, 2350, 3), (-1600, 2200), (-2050, 1550, 1), (-1600, 750, 1), (-2200, 850, 3), (-2400, 250, 1), (-2600, -350, 1), (-2300, -1300, 1), (-1400, -2400, 1), (-500, -2650), (650, -2700, 1)])
        self.phase = 'outer climb'

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        if self.route.index >= 17:
            floors = {17: 1720, 18: 1864, 19: 1981, 20: 2089, 21: 2268, 22: 2442, 23: 2442, 24: 2606}
            if self.route.index < 24 and (not s.mario.airborne) and (s.position[1] >= floors[self.route.index + 1] - 15) and (horizontal_distance(s, self.route.points[self.route.index + 1][:2]) < 700):
                self.route.index += 1
            t = self.route.points[self.route.index]
            if horizontal_distance(s, t[:2]) < 60 and s.position[1] >= floors[self.route.index] - 15 and (not s.mario.airborne):
                if self.route.index < 24:
                    self.route.index += 1
                    t = self.route.points[self.route.index]
            if s.mario.airborne:
                return air_steer(s, t[:2], 32 if horizontal_distance(s, t[:2]) > 180 else 18)
            a = steer(s, t[:2], 40) if horizontal_distance(s, t[:2]) > 25 else Action()
            return replace(a, a=(s.position[1] < floors[self.route.index] - 15 or horizontal_distance(s, t[:2]) > 100) and s.frame % 2 == 0)
        a = self.route.act(s)
        if self.route.index == 1 and (not s.mario.airborne) and (s.mario.forward_velocity > 16):
            return replace(a, z=True)
        if self.route.index == 1 and s.mario.action == 75531353:
            return replace(a, z=True, a=True)
        return a
