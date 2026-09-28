"""Development skill retained from dorrie_star.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance, GroundPoundObject
from .move import steer
from .swim import swim

class DorrieStar:

    def __init__(self):
        self.phase = 'swim'
        self.pound = GroundPoundObject(280)
        self.raised = False
        self.aimed = False

    def act(self, s):
        t = (-3600, 3600)
        d = next((o for o in s.objects.items if o.behavior_name == 'bhvDorrie'), None)
        if not d:
            return swim(s, (-3600, -4500, 3400))
        dt = (d.position[0], d.position[2])
        yaw = d.face_angle[1] * math.tau / 65536
        on = s.mario.platform_id == d.id or (s.mario.floor and s.mario.floor.object_id == d.id)
        if d.action == 2:
            self.raised = True
        if self.raised:
            self.phase = 'jump from head'
            if s.mario.action == 536875782:
                return Action()
            if s.position[1] > -4450:
                if s.mario.airborne:
                    return air_steer(s, t, 48)
                yaw = s.mario.face_angle[1] * math.tau / 65536
                err = (math.atan2(t[0] - s.position[0], t[1] - s.position[2]) - yaw + math.pi) % math.tau - math.pi
                if abs(err) > 0.12:
                    return steer(s, t, 24)
                a = steer(s, t)
                if s.mario.action == 75531353:
                    return replace(a, a=True, z=True)
                if s.mario.forward_velocity > 18:
                    return replace(a, z=True)
                return a
            if d.action == 2:
                return Action()
            if s.mario.swimming:
                self.raised = False
                self.aimed = False
        if s.mario.swimming:
            self.phase = 'swim'
            return swim(s, (dt[0], -4150, dt[1]))
        if d.action == 1:
            self.phase = 'walk to head'
            head = (dt[0] + 870 * math.sin(yaw), dt[1] + 870 * math.cos(yaw))
            return air_steer(s, head, 18) if s.mario.airborne else steer(s, head, 32) if horizontal_distance(s, head) > 30 else Action()
        if self.aimed:
            self.phase = 'ground pound'
            return self.pound.act(s, d)
        if s.mario.airborne:
            return air_steer(s, dt, 24)
        err = (math.atan2(t[0] - dt[0], t[1] - dt[1]) - yaw + math.pi) % math.tau - math.pi
        if on and abs(err) < 0.15 and (horizontal_distance(s, dt) < 200):
            self.aimed = True
            return Action()
        self.phase = 'aim body'
        if horizontal_distance(s, dt) > 140:
            return steer(s, dt, 32)
        myaw = s.mario.face_angle[1] * math.tau / 65536
        me = (math.atan2(t[0] - s.position[0], t[1] - s.position[2]) - myaw + math.pi) % math.tau - math.pi
        return steer(s, t, 16) if abs(me) > 0.05 else Action()
