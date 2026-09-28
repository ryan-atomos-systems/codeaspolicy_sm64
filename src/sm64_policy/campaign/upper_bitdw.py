"""Long jumps, narrow paths, and a seesaw with observed tilt feedback."""

import math
from dataclasses import replace

from ..api import Action
from ..control import air_steer, horizontal_distance, steer
from .navigation import Route
from .stairs import Stairs


class Upper:
    def __init__(self):
        self.phase = "gap1"
        self.route = Route(
            [
                (-4300, -500),
                (-4200, 100),
                (-4000, 250),
                (-3800, 475),
                (-3650, 630),
                (-3400, 735),
                (-3100, 820),
                (-2200, 820),
                (-1750, 800, 1),
                (-1750, -60),
                (3400, -60),
                (3500, 850),
                (3800, 850, 1),
                (3850, 400, 1),
                (3922, 0),
            ]
        )
        self.target = None
        self.beam_stage = 0
        self.approach_cleared = False
        self.stairs = Stairs()

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        if self.phase == "gap1" and s.position[0] > -5500 and not s.mario.airborne:
            self.phase = "stage2"
        if self.phase == "stage2":
            t = (-5100, -2250)
            if horizontal_distance(s, t) < 60:
                self.phase = "gap2"
            return steer(s, t, 40)
        if self.phase == "gap2" and s.position[2] > -850 and not s.mario.airborne:
            self.phase = "route"
        if self.phase == "end_stage":
            t = (2800, 0)
            if horizontal_distance(s, t) < 60 and not s.mario.airborne:
                self.phase = "gap3"
            return air_steer(s, t, 30) if s.mario.airborne else steer(s, t, 40)
        if self.phase == "gap3" and s.position[0] > 3650 and not s.mario.airborne:
            self.phase = "switch"
        if self.phase == "switch":
            return self.stairs.act(s)
        if self.phase.startswith("gap"):
            t = (
                (-5300, -2150)
                if self.phase == "gap1"
                else (-4600, -300)
                if self.phase == "gap2"
                else (3922, -7)
            )
            self.target = t
            if s.mario.airborne:
                return air_steer(s, t, 48)
            yaw = s.mario.face_angle[1] * math.tau / 65536
            err = (
                math.atan2(t[0] - s.position[0], t[1] - s.position[2]) - yaw + math.pi
            ) % math.tau - math.pi
            a = steer(s, t, 80)
            if s.mario.action == 0x04808459:
                return replace(a, a=True, z=True)
            # The last ledge has a short run-up; the earlier jumps have room
            # to reach full running speed before takeoff.
            speed = 16 if self.phase == "gap3" else 25
            tolerance = 0.25 if self.phase == "gap3" else 0.15
            return replace(a, z=s.mario.forward_velocity > speed and abs(err) < tolerance)
        if self.route.index == 10 and s.position[0] > 1300:
            self.phase = "beam"
        if self.phase == "beam":
            beam = min(
                (o for o in s.objects.items if o.behavior_name == "bhvSeesawPlatform"),
                key=lambda o: abs(o.position[0] - 1491),
            )
            if self.beam_stage == 0:
                t = (1491, -160)
                if horizontal_distance(s, t) < 30:
                    self.beam_stage = 1
                return steer(s, t, 32)
            if self.beam_stage == 1:
                if s.mario.platform_id == beam.id and not s.mario.airborne:
                    self.beam_stage = 2
                else:
                    t = (1491, 280)
                    if s.mario.airborne:
                        if s.position[2] < 200:
                            return Action(stick_y=-64, a=True)
                        return air_steer(s, t, 30)
                    yaw = s.mario.face_angle[1] * math.tau / 65536
                    if abs((math.pi - yaw + math.pi) % math.tau - math.pi) > 0.3:
                        return steer(s, (s.position[0], s.position[2] - 1000), 24)
                    return Action(z=True, a=s.mario.action in (0x0C008220, 0x0C008221))
            if self.beam_stage == 2:
                t = (900, 512)
                if horizontal_distance(s, t) < 70:
                    self.beam_stage = 3
                return steer(s, t, 40)
            if self.beam_stage == 3:
                if abs(beam.face_angle[0]) > 3000:
                    self.beam_stage = 4
                return Action()
            if self.beam_stage == 4:
                t = (2150, 512)
                if s.position[0] > 2050:
                    self.beam_stage = 5
                return steer(s, t, 80)
            if self.beam_stage == 5:
                t = (2700, 512)
                if s.mario.airborne:
                    return air_steer(s, t, 32)
                if s.position[0] > 2463 and s.position[1] > 1800:
                    self.route.index = 11
                    self.phase = "end_stage"
                    return Action()
                else:
                    return replace(steer(s, t, 80), a=s.frame % 4 < 2)
        # Clear the Goomba from the broad landing before entering the narrow
        # ledge. A hit on that ledge knocks Mario straight into the void.
        if self.phase == "route" and self.route.index == 9 and not self.approach_cleared:
            enemies = [
                o
                for o in s.objects.items
                if o.behavior_name == "bhvGoomba"
                and -2050 < o.position[0] < -1250
                and -400 < o.position[2] < 1100
                and abs(o.position[1] - s.position[1]) < 150
                and o.action < 100
            ]
            if enemies:
                enemy = min(enemies, key=lambda o: o.distance)
                t = (
                    max(-1900, min(-1440, enemy.position[0])),
                    max(150, min(800, enemy.position[2])),
                )
                if s.mario.airborne:
                    return air_steer(s, t, 18)
                a = steer(s, t, 40)
                return replace(a, b=enemy.distance < 220 and s.frame % 8 < 4)
            self.approach_cleared = True
        self.target = self.route.points[self.route.index]
        t = self.route.points[self.route.index]
        if horizontal_distance(s, t[:2]) < 55 and self.route.index + 1 < len(self.route.points):
            self.route.index += 1
            t = self.route.points[self.route.index]
        if s.mario.airborne:
            return air_steer(s, t[:2], 30)
        a = steer(s, t[:2], 32 if self.route.index == 9 else 40 if self.route.index <= 10 else 64)
        return replace(a, a=len(t) > 2 and s.frame % 40 < 25)
