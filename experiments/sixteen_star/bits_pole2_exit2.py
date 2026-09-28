"""Development skill retained from bits_pole2_exit2.py; see README.md for evidence and limits."""

import math
from sm64_policy import Action
from .air_landing import air_steer
from .move import Waypoints, steer
from dataclasses import replace

class Exit:

    def __init__(self):
        self.phase = 'pole'
        self.route = Waypoints([(-2350, -905), (-1950, -905, 2), (-1000, -905), (-500, -905), (0, -1250), (500, -1650), (1000, -2100), (1700, -2100), (1900, -1500), (1900, -900)])

    def act(self, s):
        o = next((o for o in s.objects.items if o.behavior_name == 'bhvSlidingPlatform2' and o.behavior_params == 13565952), None)
        if s.mario.on_pole:
            if s.position[1] < 3880:
                return Action(stick_y=80)
            if s.mario.action == 1049411:
                return Action()
            yaw = s.mario.face_angle[1] * math.tau / 65536
            err = (-math.pi / 2 - yaw + math.pi) % math.tau - math.pi
            if abs(err) > 0.06:
                return Action(stick_x=round(max(-60, min(60, -err * 65536 / math.tau / 16 * 0.5))))
            if o and (not (o.position[0] > -2100 and o.velocity[0] < 0)):
                return Action()
            return Action(a=True)
        if self.phase == 'pole':
            if s.mario.airborne:
                return air_steer(s, (max(-2550, min(-1900, o.position[0] + o.velocity[0] * 12)) if o else -2450, -905), 32)
            self.phase = 'ramp'
        if s.mario.airborne:
            return air_steer(s, self.route.points[self.route.index][:2], 48)
        a = self.route.act(s)
        if self.route.index == 1 and s.mario.action == 67109952 and (s.mario.forward_velocity > 16):
            return replace(a, z=s.frame % 2 == 0)
        return a
