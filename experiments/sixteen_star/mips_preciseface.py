"""Development skill retained from mips_preciseface.py; see README.md for evidence and limits."""

from sm64_policy import Action
from .move import steer
import math

class Face:

    def __init__(self, yaw=8192):
        self.yaw = yaw

    def act(self, s):
        err = (self.yaw - s.mario.face_angle[1] + 32768) % 65536 - 32768
        if abs(err) < 140:
            return Action()
        a = self.yaw * math.tau / 65536
        return steer(s, (s.position[0] + 100 * math.sin(a), s.position[2] + 100 * math.cos(a)), 74)
