"""Development skill retained from bitfs_cages.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from .move import Waypoints, steer, turning_air
from sm64_policy.control import air_steer, horizontal_distance

class Cages:

    def __init__(self):
        self.i = 0
        self.flying = False
        self.phase = 'cage poles'
        self.route = Waypoints([(4000, 96), (5100, 96, 2), (5750, 96, 2), (6500, 96), (6735, 96)])

    def act(self, s):
        if s.position[0] > 3500 and s.position[1] > 4300 and (not s.mario.airborne):
            self.i = 3
        if self.i == 3:
            return self.route.act(s)
        px = (614, 1843, 3072)[self.i]
        tx = (1229, 2400, 3800)[self.i]
        height = (4403, 3789, 4403)[self.i]
        if s.mario.on_pole:
            pole = min((o for o in s.objects.items if o.behavior_name == 'bhvDddMovingPole'), key=lambda o: abs(o.position[0] - s.position[0]))
            self.flying = False
            rel = 180 if self.i == 1 else 585
            if s.position[1] > pole.position[1] + rel + 20:
                return Action(stick_y=-40)
            if s.position[1] < pole.position[1] + rel - 10:
                return Action(stick_y=48)
            if s.mario.action not in (135267136, 1049413):
                return Action()
            yaw = s.mario.face_angle[1] * math.tau / 65536
            err = (math.atan2(tx - s.position[0], 96 - s.position[2]) + (0 if s.mario.action == 1049413 else math.pi) - yaw + math.pi) % math.tau - math.pi
            if abs(err) > 0.04:
                v = max(-60, min(60, -err * 65536 / math.tau / 16 * 0.4))
                return Action(stick_x=round(v + math.copysign(6, v)))
            if not height - 350 < s.position[1] < height - 230:
                return Action()
            self.flying = True
            return Action(a=True)
        if not s.mario.airborne and abs(s.position[0] - tx) < 250 and (s.position[1] >= height - 20):
            self.i += 1
            self.flying = False
            if self.i == 3:
                return self.route.act(s)
            px = (614, 1843, 3072)[self.i]
            tx = (1229, 2400, 3800)[self.i]
        t = (tx, 96) if self.flying else (px, 96)
        if s.mario.action == 16910519:
            return turning_air(s, t)
        if s.mario.airborne:
            return air_steer(s, t, 32)
        return replace(steer(s, t), a=s.frame % 2 == 0)
