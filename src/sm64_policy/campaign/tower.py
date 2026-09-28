"""Tower climb with platform tracking and recovery after a missed landing."""

import math
from dataclasses import replace

from ..api import Action
from ..control import air_steer, horizontal_distance, steer


class Tower:
    def __init__(self):
        self.index = 0
        self.last_jump = -100
        self.release_until = 0
        self.phase = "platforms"
        self.target = None
        self.stage = 0

    def act(self, s):
        if self.index > 0 and s.position[1] < 3800 and not s.mario.airborne:
            self.index = 0
            self.stage = 0
            self.phase = "platforms"
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        star = next(
            (
                o
                for o in s.objects.items
                if o.behavior_name == "bhvStar" and o.behavior_params >> 24 == 1
            ),
            None,
        )
        if s.position[1] > 5260:
            self.phase = "star"
            t = star.position[0], star.position[2]
            if s.mario.airborne:
                return air_steer(s, t)
            a = steer(s, t, 40)
            return replace(a, a=s.frame % 40 < 25)
        platforms = [
            o
            for o in s.objects.items
            if o.behavior_name
            in (
                "bhvWfSolidTowerPlatform",
                "bhvWfSlidingTowerPlatform",
                "bhvWfElevatorTowerPlatform",
            )
        ]
        if not platforms:
            return Action()

        def ang(o):
            return math.atan2(o.position[0], o.position[2]) % math.tau

        target = min(
            platforms,
            key=lambda o: abs((ang(o) - self.index * math.pi / 4 + math.pi) % math.tau - math.pi),
        )
        t = target.position[0] + target.velocity[0] * 6, target.position[2] + target.velocity[2] * 6
        self.target = target.position
        on = (
            s.mario.platform_id == target.id
            or s.mario.floor
            and s.mario.floor.object_id == target.id
        ) and not s.mario.airborne
        if on and self.index < 7:
            self.index += 1
            self.release_until = s.frame + 2
            return Action()
        if s.frame < self.release_until:
            return Action()
        if on and self.index == 7:
            self.phase = "elevator"
            if s.position[1] < 5230:
                return steer(s, t, 32) if horizontal_distance(s, t) > 25 else Action()
            self.phase = "top"
            t = (-300, 0)
        if self.phase == "top":
            t = (-300, 0)
            if s.mario.airborne:
                return air_steer(s, t, 30)
            away = math.atan2(s.position[0] - t[0], s.position[2] - t[1])
            yaw = s.mario.face_angle[1] * math.tau / 65536
            if abs((away - yaw + math.pi) % math.tau - math.pi) > 0.15:
                return steer(s, (2 * s.position[0] - t[0], 2 * s.position[2] - t[1]), 24)
            return Action(z=True, a=s.mario.action in (0x0C008220, 0x0C008221))
        if self.index == 0 and self.stage < 2:
            angle = math.atan2(s.position[0], s.position[2])
            heading = angle + max(-0.35, min(0.35, -angle))
            q = (
                (850 * math.sin(heading), 850 * math.cos(heading))
                if abs(angle) > 0.15
                else (0, 1100)
            )
            if horizontal_distance(s, (0, 1100)) < 60 and not s.mario.airborne:
                self.stage = 2
            return air_steer(s, q, 30) if s.mario.airborne else steer(s, q, 48)
        if s.mario.airborne:
            return air_steer(s, t, 30)
        d = horizontal_distance(s, t)
        a = steer(s, t, 64)
        if self.index == 0:
            if self.stage == 2 and d < 340:
                self.stage = 3
                return replace(steer(s, t, 80), a=True)
            if self.stage == 3 and not s.mario.airborne:
                self.stage = 0
            return steer(s, t, 80)
        if d > 850 or (self.index % 2 == 1 and math.hypot(*t) < 570):
            return Action()
        yaw = s.mario.face_angle[1] * math.tau / 65536
        err = (
            math.atan2(t[0] - s.position[0], t[1] - s.position[2]) - yaw + math.pi
        ) % math.tau - math.pi
        if abs(err) > 0.18:
            return steer(s, t, 24)
        if s.frame - self.last_jump > 6:
            self.last_jump = s.frame
            return replace(a, a=True)
        return a
