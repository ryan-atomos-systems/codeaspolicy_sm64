"""Authored route landmarks with observed position and action feedback."""

import math

from ..api import Action
from ..control import air_steer, horizontal_distance, steer
from ..decision_trace import record_route


class Route:
    def __init__(self, points):
        self.points = points
        self.index = 0
        self.flip = 0

    def act(self, s):
        t = self.points[self.index]
        if horizontal_distance(s, t[:2]) < 100 and self.index + 1 < len(self.points):
            self.index += 1
            t = self.points[self.index]
        record_route(self.points, self.index)
        if len(t) > 2 and t[2] == 2 and horizontal_distance(s, t[:2]) < 400:
            if s.mario.airborne:
                self.flip = 0
                return air_steer(s, t[:2])
            away = math.atan2(s.position[0] - t[0], s.position[2] - t[1])
            yaw = s.mario.face_angle[1] * math.tau / 65536
            if abs((away - yaw + math.pi) % math.tau - math.pi) > 0.15:
                return steer(s, (2 * s.position[0] - t[0], 2 * s.position[2] - t[1]), 24)
            return Action(z=True, a=s.mario.action in (0x0C008220, 0x0C008221))
        a = steer(s, t[:2])
        return Action(a.stick_x, a.stick_y, a=(len(t) > 2 and s.frame % 40 < 24))
