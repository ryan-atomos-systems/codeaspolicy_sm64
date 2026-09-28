"""Development skill retained from poles.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance
from .move import steer

class Poles:

    def __init__(self):
        self.index = 0
        self.phase = 'grab pole'
        self.jumped = False
        self.finish = False
    points = [(728, 3030, -2754), (1043, 3610, -2679), (1078, 3900, -2269), (1413, 3900, -2190), (2030, 3621, -1270)]

    def act(self, s):
        if self.index == 4 and (not s.mario.airborne):
            self.finish = True
        if self.finish:
            t = (2523, -901)
            return air_steer(s, t, 32) if s.mario.airborne else replace(steer(s, t, 40), a=s.frame % 2 == 0)
        if s.mario.on_pole:
            j = min(range(4), key=lambda i: horizontal_distance(s, (self.points[i][0], self.points[i][2])))
            self.index = j
            self.jumped = False
            if s.position[1] < self.points[j][1]:
                self.phase = 'climb'
                return Action(stick_y=80)
            if s.mario.action != 135267136:
                return Action()
            t = self.points[j + 1]
            yaw = s.mario.face_angle[1] * math.tau / 65536
            err = (math.atan2(t[0] - s.position[0], t[2] - s.position[2]) + math.pi - yaw + math.pi) % math.tau - math.pi
            self.phase = 'aim pole jump'
            if abs(err) > 0.04:
                v = max(-60, min(60, -err * 65536 / math.tau / 16 * 0.4))
                return Action(stick_x=round(v + math.copysign(6, v)))
            self.index = j + 1
            self.jumped = True
            return Action(a=True)
        t = self.points[self.index]
        xz = (t[0], t[2])
        if s.mario.airborne:
            return air_steer(s, xz, 32)
        if self.index == 4:
            stars = [o for o in s.objects.items if o.behavior_name == 'bhvStar' and o.behavior_params >> 24 == 4]
            if stars:
                t = stars[0].position
                xz = (t[0], t[2])
        return replace(steer(s, xz, 40), a=s.frame % 2 == 0)
