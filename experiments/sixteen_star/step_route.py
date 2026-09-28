"""Development skill retained from step_route.py; see README.md for evidence and limits."""

import math
from .jumproute import JumpRoute
from sm64_policy import Action
from sm64_policy.control import horizontal_distance
from .move import steer

class Steps(JumpRoute):

    def act(self, s):
        t = self.points[self.index]
        xz = (t[0], t[2])
        if not s.mario.airborne and s.position[1] < t[1] - 60 and (horizontal_distance(s, xz) < 500):
            away = (2 * s.position[0] - t[0], 2 * s.position[2] - t[2])
            yaw = s.mario.face_angle[1] * math.tau / 65536
            err = (math.atan2(away[0] - s.position[0], away[1] - s.position[2]) - yaw + math.pi) % math.tau - math.pi
            if abs(err) > 0.08:
                return steer(s, away, 24)
            return Action(z=True, a=s.mario.action in (201359904, 201359905))
        return super().act(s)
