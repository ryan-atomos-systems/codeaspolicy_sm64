"""Development skill retained from blj.py; see README.md for evidence and limits."""

import math
from sm64_policy import Action
from .mips_preciseface import Face

class BLJ:

    def __init__(self, yaw=-32768):
        self.yaw = yaw
        self.phase = 'face downstairs'
        self.t = 0
        self.minv = 0

    def act(self, s):
        self.t += 1
        self.minv = min(self.minv, s.mario.forward_velocity)
        if self.phase == 'face downstairs':
            err = (self.yaw - s.mario.face_angle[1] + 32768) % 65536 - 32768
            if abs(err) > 300:
                return Face(self.yaw).act(s)
            self.phase = 'run'
        if self.phase == 'run':
            if s.mario.forward_velocity > 18:
                self.phase = 'crouch'
            else:
                return Action(stick_y=80)
        if self.phase == 'crouch':
            if s.mario.action == 75531353:
                self.phase = 'BLJ'
                self.t = 0
                return Action(stick_y=80, z=True, a=True)
            return Action(stick_y=80, z=s.mario.action == 67109952 and self.t % 2 == 0)
        return Action(stick_y=-80, z=True, a=self.t % 2 == 0)
