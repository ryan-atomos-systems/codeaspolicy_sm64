"""Development primitive; consult README.md before composing a route."""

import math
from sm64_policy import Action
from .move import steer

class Edge:

    def act(self, s):
        if s.position[2] >= 2120:
            return Action()
        a = 10680 * math.tau / 65536
        return steer(s, (s.position[0] + 100 * math.sin(a), s.position[2] + 100 * math.cos(a)), 16)
