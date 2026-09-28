"""Development skill retained from bitfs_rise.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance
from .move import Waypoints, steer, turning_air

class Rise:

    def __init__(self):
        self.phase = 'far pole'
        self.route = Waypoints([(5400, 266), (5900, 266), (6605, 266, 2)])
        self.route2 = Waypoints([(5500, 266), (4550, 266, 2), (4100, 266), (3890, 266, 3)])
        self.upper = Waypoints([(3500, 266), (3100, 307), (2867, 307)])
        self.stage = 0

    def pole(self, s, height, target):
        if s.position[1] < height:
            return Action(stick_y=56)
        if s.mario.action != 135267136:
            return Action()
        yaw = s.mario.face_angle[1] * math.tau / 65536
        err = (math.atan2(target[0] - s.position[0], target[1] - s.position[2]) + math.pi - yaw + math.pi) % math.tau - math.pi
        if abs(err) > 0.04:
            v = max(-60, min(60, -err * 65536 / math.tau / 16 * 0.4))
            return Action(stick_x=round(v + math.copysign(6, v)))
        self.stage += 1
        return Action(a=True)

    def act(self, s):
        if s.mario.on_pole:
            if s.position[0] > 6000:
                self.stage = 0
                self.phase = 'climb far pole'
                o = next((o for o in s.objects.items if o.behavior_name == 'bhvDddMovingPole' and o.position[0] > 6000))
                return self.pole(s, -2480, (6100, 266))
            self.stage = 3
            self.phase = 'climb upper pole'
            return self.pole(s, -1350, (3600, 266))
        if self.stage == 0:
            if s.mario.action == 16910519:
                return turning_air(s, (6605, 266))
            return self.route.act(s)
        if self.stage == 1:
            if not s.mario.airborne and s.position[1] > -2600 and (s.position[0] < 6300):
                self.stage = 2
            else:
                return air_steer(s, (6100, 266), 32) if s.mario.airborne else replace(steer(s, (6100, 266)), a=s.frame % 2 == 0)
        if self.stage == 2:
            self.phase = 'seesaws'
            return self.route2.act(s)
        if self.stage >= 4:
            self.phase = 'elevator'
            if s.mario.airborne:
                return air_steer(s, (3600, 266), 24)
            if not self.upper.done:
                return self.upper.act(s)
            return Action()
        return Action()
