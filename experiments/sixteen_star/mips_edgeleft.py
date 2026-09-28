"""Development primitive; consult README.md before composing a route."""

import math
from sm64_policy import Action
from .move import steer

class Edge:

    def __init__(self, x=-3155, yaw=-2000):
        self.x = x
        self.yaw = yaw

    def act(self, s):
        if s.position[0] <= self.x:
            return Action()
        a = self.yaw * math.tau / 65536
        return steer(s, (s.position[0] + 100 * math.sin(a), s.position[2] + 100 * math.cos(a)), 16)
