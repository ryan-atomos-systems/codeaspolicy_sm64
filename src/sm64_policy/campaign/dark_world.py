"""Bowser in the Dark World: a hierarchy of terrain and moving-platform skills."""

import math
from dataclasses import replace

from ..api import Action
from ..control import air_steer, horizontal_distance, steer
from .navigation import Route
from .upper_bitdw import Upper


class DarkWorld:
    def __init__(self):
        self.i = 0
        self.phase = "path"
        self.target = None
        self.landed = False
        self.lift = None
        self.wheel_jump = False
        self.wheel_ready = False
        self.left = False
        self.rampdone = False
        self.upper_ready = False
        self.upper_started = False
        self.finish = Upper()
        self.upper = Route(
            [
                (-2000, 3681),
                (-2400, 3300),
                (-2400, 1200),
                (-3400, 800),
                (-4600, 900),
                (-6500, 900),
                (-7500, -500),
                (-7000, -2150),
                (-6400, -2150),
            ]
        )

    points = (
        (-7000, 3886),
        (-5000, 3886),
        (-3900, 4100),
        (-3500, 4100),
        (-2800, 4100),
        (-2600, 4100),
    )

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        if self.upper_ready:
            self.phase = "upper course"
            return self.finish.act(s)
        if self.upper.index == 8 and horizontal_distance(s, (-6400, -2150)) < 100:
            self.upper_ready = True
            return Action()
        if self.i < len(self.points):
            t = self.points[self.i]
            self.target = t
            if horizontal_distance(s, t) < 100:
                self.i += 1
            a = steer(s, t, 80)
            return replace(a, a=self.i == 4)
        if not self.landed:
            self.phase = "gap"
            if s.position[0] > -850 and not s.mario.airborne:
                self.landed = True
                return Action()
            t = (-700, 3886)
            a = steer(s, t, 80)
            if s.mario.airborne:
                return air_steer(s, t, 48)
            if s.mario.action == 0x04808459:
                return replace(a, a=True, z=True)
            return replace(a, z=s.mario.forward_velocity > 25)
        if not self.upper_started and s.position[1] < -2450:
            self.rampdone = False
            self.lift = None
            self.left = self.wheel_jump = self.wheel_ready = False
        self.phase = "ramp"
        if s.position[0] > 850 and not s.mario.airborne:
            self.rampdone = True
        if not self.rampdone:
            a = steer(s, (1050, 3700), 80)
            return replace(
                a,
                a=s.frame % 4 < 2,
                b=s.mario.action == 0x03000885 and s.mario.forward_velocity < 20,
            )
        if s.position[0] < -1000 and s.position[1] > -1800 and not s.mario.airborne:
            self.upper_started = True
        if self.upper_started:
            self.phase = "upper"
        if self.phase == "upper":
            t = self.upper.points[self.upper.index][:2]
            if s.mario.airborne:
                return air_steer(s, t, 30)
            a = self.upper.act(s)
            return replace(
                a,
                a=self.upper.index == 7
                and horizontal_distance(s, (-7000, -2150)) < 300
                and s.frame % 40 < 25,
                b=any(
                    o.behavior_name == "bhvGoomba"
                    and o.action < 100
                    and o.distance < 220
                    and abs(o.position[1] - s.position[1]) < 120
                    for o in s.objects.items
                )
                and s.frame % 8 < 4,
            )
        self.phase = "wheel"
        wheels = [o for o in s.objects.items if o.behavior_name == "bhvFerrisWheelPlatform"]
        if not wheels:
            return Action()
        if self.lift is None:
            stage = (1100, 3681)
            if s.mario.airborne:
                return air_steer(s, stage, 30)
            if not self.wheel_ready:
                if horizontal_distance(s, stage) > 35:
                    return steer(s, stage, 32)
                if abs(s.mario.forward_velocity) > 2:
                    return Action()
                self.wheel_ready = True
            yaw = s.mario.face_angle[1] * math.tau / 65536
            err = (-math.pi / 2 - yaw + math.pi) % math.tau - math.pi
            if abs(err) > 0.15:
                # Invert the six-unit dead zone for an accurate slow turn.
                def raw(value):
                    return round(value + math.copysign(6, value)) if abs(value) > 0.5 else 0

                return Action(raw(-12 * math.sin(err)), raw(12 * math.cos(err)))
            target = min(wheels, key=lambda o: o.position[1])
            # Board near the bottom of the orbit. Starting farther left makes
            # Mario's head hit the next platform overhead during the approach.
            # Observe the orbit phase instead of depending on entry-frame timing.
            if target.position[0] > -320 and target.velocity[1] < 0:
                self.lift = target.id
            else:
                return Action()
        else:
            target = next(o for o in wheels if o.id == self.lift)
        if not self.wheel_jump:
            if s.position[0] < 860:
                self.wheel_jump = True
                return replace(steer(s, (-200, 3681), 80), a=True)
            return steer(s, (-200, 3681), 80)
        t = (target.position[0] + target.velocity[0] * 10, target.position[2])
        if self.left:
            t = (-1200, 3681)
        on = s.mario.platform_id == target.id and not s.mario.airborne
        if on:
            if s.position[0] < 0 and s.position[1] > -1700:
                yaw = s.mario.face_angle[1] * math.tau / 65536
                err = (
                    math.atan2(-1200 - s.position[0], 3681 - s.position[2]) - yaw + math.pi
                ) % math.tau - math.pi
                if abs(err) < 0.2:
                    self.left = True
                    return replace(steer(s, (-1200, 3681), 80), a=True)
                return steer(s, (-1200, 3681), 24)
            return (
                steer(s, (target.position[0], target.position[2]), 32)
                if horizontal_distance(s, (target.position[0], target.position[2])) > 30
                else Action()
            )
        if s.mario.airborne:
            return air_steer(s, t, 32)
        a = steer(s, t, 80)
        return replace(a, a=self.lift is not None and s.frame % 40 < 25)
