"""Development skill retained from meshride.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance
from .move import steer, turning_air

class Ride:

    def __init__(self):
        self.phase = 'board'
        self.jumped = False
        self.exit = False

    def act(self, s):
        objs = [o for o in s.objects.items if o.behavior_name == 'bhvLllMovingOctagonalMeshPlatform' and o.position[2] < 0]
        if not objs:
            return Action()
        o = objs[0]
        riding = (s.mario.platform_id == o.id or (s.mario.floor and s.mario.floor.object_id == o.id)) and (not s.mario.airborne)
        if riding:
            self.phase = 'ride'
            self.jumped = False
            if self.exit:
                return Action(z=True, a=s.mario.action in (201359904, 201359905))
            if o.position[0] > 2890:
                t = (3300, -5300)
                away = (2 * s.position[0] - t[0], 2 * s.position[2] - t[1])
                yaw = s.mario.face_angle[1] * math.tau / 65536
                err = (math.atan2(away[0] - s.position[0], away[1] - s.position[2]) - yaw + math.pi) % math.tau - math.pi
                self.phase = 'align backflip'
                if abs(err) > 0.12:
                    return steer(s, away, 24)
                self.exit = True
                return Action(z=True, a=s.mario.action in (201359904, 201359905))
            t = (o.position[0] + 80, o.position[2])
            return steer(s, t, 32) if horizontal_distance(s, t) > 60 else Action()
        if self.exit:
            self.phase = 'exit'
            if not s.mario.airborne and s.position[1] < 250:
                return Action(z=True, a=s.mario.action in (201359904, 201359905))
            return air_steer(s, (3400, -5400), 32) if s.mario.airborne else steer(s, (3400, -5400))
        t = (o.position[0] + o.velocity[0] * 8, o.position[2])
        if s.mario.action == 16910519:
            return turning_air(s, t)
        if s.mario.airborne:
            self.phase = 'board air'
            return air_steer(s, t, 48)
        if s.position[0] < 400:
            return steer(s, (500, -4607))
        if o.position[0] < 1600:
            a = steer(s, t)
            if s.mario.action == 75531353:
                return replace(a, a=True, z=True)
            if s.mario.forward_velocity > 20:
                return replace(a, z=True)
            return a
        return Action()
