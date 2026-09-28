"""Development skill retained from jumproute.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance
from .move import steer, turning_air

class JumpRoute:

    def __init__(self, points):
        self.points = points
        self.index = 0
        self.done = False
        self.phase = 'align'
        self.last_a = False

    def act(self, s):
        t = self.points[self.index]
        xz = (t[0], t[2])
        d = horizontal_distance(s, xz)
        if not s.mario.airborne and d < 65 and (s.position[1] >= t[1] - 20):
            if self.index + 1 == len(self.points):
                self.done = True
                return Action()
            self.index += 1
            self.phase = 'align'
            return Action()
        if s.mario.action == 16910519:
            return turning_air(s, xz)
        if s.mario.airborne:
            self.phase = 'flight'
            return air_steer(s, xz, 32)
        yaw = s.mario.face_angle[1] * math.tau / 65536
        err = (math.atan2(t[0] - s.position[0], t[2] - s.position[2]) - yaw + math.pi) % math.tau - math.pi
        if abs(err) > 0.12:
            self.phase = 'align'
            return steer(s, xz, 24)
        if d < 130 and abs(s.position[1] - t[1]) < 25:
            return steer(s, xz, 24)
        if self.phase == 'flight':
            self.phase = 'run'
            return Action()
        self.phase = 'run'
        a = steer(s, xz)
        if s.mario.forward_velocity > 14 or d < 120:
            self.phase = 'jump'
            return replace(a, a=True)
        return a
