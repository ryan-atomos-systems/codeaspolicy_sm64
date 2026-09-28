"""Development skill retained from bits_pole_exit.py; see README.md for evidence and limits."""

import math
from sm64_policy import Action
from .air_landing import air_steer
from .move import Waypoints

class Exit:

    def __init__(self):
        self.route = Waypoints([(-6000, -900), (-5100, -900), (-4580, -900)])
        self.phase = 'climb'

    def act(self, s):
        if s.mario.on_pole:
            if s.position[1] < 4000:
                return Action(stick_y=80)
            if s.mario.action == 1049411:
                return Action()
            top = s.mario.action == 1049413
            yaw = s.mario.face_angle[1] * math.tau / 65536
            target = math.pi / 2 if top else -math.pi / 2
            err = (target - yaw + math.pi) % math.tau - math.pi
            if abs(err) > 0.06:
                return Action(stick_x=round(max(-60, min(60, -err * 65536 / math.tau / 16 * 0.5))))
            return Action(a=True)
        if s.mario.airborne:
            return air_steer(s, (-6000, -900), 32)
        return self.route.act(s)
