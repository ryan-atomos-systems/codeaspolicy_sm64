"""Whomp’s Fortress: gap jumps, the in-game teleporter, and elevator boarding."""

import math

from ..api import Action
from ..control import air_steer, horizontal_distance, steer
from .whomp_fight import WhompFight


class Whomp:
    points = (
        (3800, 4500),
        (3800, 3900, 1),
        (3800, 3000),
        (3750, 2000),
        (3750, 1000),
        (3750, 0),
        (3750, -3200, 1),
        (3500, -3700),
        (2548, -3962, 3),
        (-2500, -800),
        (-1700, -800, 1),
        (-1700, -2100),
        (0, -1800),
        (800, -1400),
        (1100, -1100, 1, 3500),
        (0, 0),
    )

    def __init__(self):
        self.i = 0
        self.lift_id = None
        self.exitlift = False
        self.fight = WhompFight()

    def act(self, s):
        if s.ui and (s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0) or s.area == 2:
            return Action(a=s.frame % 8 == 0)
        if self.i == 15:
            if s.position[1] < 3300:
                self.i = 14
                self.exitlift = False
            else:
                return self.fight.act(s)
        t = self.points[self.i]
        d = horizontal_distance(s, t[:2])
        if self.i == 6:
            if s.position[2] < -3200 and not s.mario.airborne:
                self.i = 7
            else:
                target = (3840, -3300)
                if s.mario.airborne:
                    return air_steer(s, target, 32)
                a = steer(s, target, 80)
                jump = any(0 < s.position[2] - edge < 190 for edge in (-512, -1536, -2560))
                return Action(a.stick_x, a.stick_y, a=jump)
        if self.i == 14:
            if self.exitlift and not s.mario.airborne and s.position[1] < 3300:
                self.exitlift = False
            lifts = [o for o in s.objects.items if o.behavior_name == "bhvCheckerboardPlatformSub"]
            current = next((o for o in lifts if o.id == self.lift_id), None)
            if current is None:
                current = min(lifts, key=lambda o: o.position[1])
                self.lift_id = current.id
            if (
                s.position[1] > 3500
                and s.position[0] < 900
                and s.position[2] > -900
                and not s.mario.airborne
                and not s.mario.platform_id
            ):
                self.i = 15
                return steer(s, (0, 0))
            if (
                s.mario.platform_id == current.id
                or s.mario.floor
                and s.mario.floor.object_id == current.id
            ) and not s.mario.airborne:
                if s.position[1] > 3410:
                    target = (500, -500)
                    yaw = s.mario.face_angle[1] * math.tau / 65536
                    err = (
                        math.atan2(target[0] - s.position[0], target[1] - s.position[2])
                        - yaw
                        + math.pi
                    ) % math.tau - math.pi
                    if abs(err) > 0.15:
                        return steer(s, target, 24)
                    self.exitlift = True
                    a = steer(s, target, 80)
                    return Action(a.stick_x, a.stick_y, a=True)
                target = current.position[0], current.position[2]
                return steer(s, target, 32) if horizontal_distance(s, target) > 30 else Action()
            target = (500, -500) if self.exitlift else (current.position[0], current.position[2])
            if s.mario.airborne:
                return air_steer(s, target, 30 if self.exitlift else 18)
            if horizontal_distance(s, target) > 240:
                return steer(s, target, 40)
            away = math.atan2(s.position[0] - target[0], s.position[2] - target[1])
            yaw = s.mario.face_angle[1] * math.tau / 65536
            if abs((away - yaw + math.pi) % math.tau - math.pi) > 0.15:
                return steer(s, (2 * s.position[0] - target[0], 2 * s.position[2] - target[1]), 24)
            return Action(
                z=True, a=s.mario.action in (0x0C008220, 0x0C008221) and current.position[1] < 2850
            )
        if len(t) > 2 and t[2] == 3:
            if s.position[0] < -2500 and s.position[1] > 2400:
                self.i += 1
                t = self.points[self.i]
                d = horizontal_distance(s, t[:2])
            elif d < 25:
                return Action()
            else:
                return steer(s, t[:2], 32 if d < 300 else 64)
        if (
            d < 100
            and (self.i < 10 or not s.mario.airborne)
            and (len(t) < 4 or s.position[1] >= t[3])
            and self.i + 1 < len(self.points)
        ):
            self.i += 1
            t = self.points[self.i]
        if len(t) > 2 and t[2] == 2:
            a = steer(s, t[:2], 80)
            if s.mario.airborne:
                return air_steer(s, t[:2]) if d < 800 else a
            if s.mario.action == 0x04808459:
                return Action(a.stick_x, a.stick_y, a=True, z=True)
            if s.mario.forward_velocity > 25:
                return Action(a.stick_x, a.stick_y, z=True)
            return a
        if s.mario.airborne and self.i >= 10:
            return air_steer(s, t[:2])
        a = steer(s, t[:2])
        return Action(a.stick_x, a.stick_y, a=len(t) > 2 and s.frame % 40 < 25)
