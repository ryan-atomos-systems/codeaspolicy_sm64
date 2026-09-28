"""Development skill retained from sideflip_diagonal.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance
from .move import steer

class Flip:

    def __init__(self, x=-4950, z=-850):
        self.t = (x, z)
        self.phase = 'align'
        self.done = False

    def act(self, s):
        if s.mario.airborne:
            self.phase = 'flight'
            return air_steer(s, self.t, 32)
        if self.phase == 'flight':
            self.done = True
            return Action()
        away = (s.position[0] - 100, s.position[2] + 200)
        if self.phase == 'align':
            yaw = s.mario.face_angle[1] * math.tau / 65536
            err = (math.atan2(away[0] - s.position[0], away[1] - s.position[2]) - yaw + math.pi) % math.tau - math.pi
            if abs(err) > 0.1:
                return replace(steer(s, away, 32), z=True)
            self.phase = 'run'
        if self.phase == 'run':
            if s.mario.forward_velocity < 16:
                return steer(s, away)
            self.phase = 'turn'
        a = steer(s, self.t)
        return replace(a, a=s.mario.action in (1091, 1092))
