"""Whomp King: bait, evade, and ground-pound its exposed back."""

import math
from dataclasses import replace

from ..api import Action
from ..control import GroundPoundObject, air_steer, horizontal_distance, steer


class WhompFight:
    def __init__(self):
        self.pound = GroundPoundObject(200)
        self.phase = "bait"
        self.target = None
        self.last_jump = -100

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        star = next(
            (
                o
                for o in s.objects.items
                if o.behavior_name in ("bhvStar", "bhvStarSpawnCoordinates")
                and o.behavior_params >> 24 == 0
            ),
            None,
        )
        if star:
            t = star.position[0], star.position[2]
            if s.mario.airborne:
                return air_steer(s, t)
            a = steer(s, t, 40)
            return replace(a, a=s.frame % 40 < 25)
        boss = next((o for o in s.objects.items if o.behavior_name == "bhvWhompKingBoss"), None)
        if not boss:
            return Action()
        x, y, z = boss.position
        angle = boss.face_angle[1] * math.tau / 65536
        if boss.action == 0:
            return steer(s, (x, z), 40)
        if boss.action == 6 and boss.sub_action == 0:
            self.phase = "pound"
            target = replace(
                boss, position=(x + math.sin(angle) * 350, y, z + math.cos(angle) * 350)
            )
            self.target = target.position
            point = target.position[0], target.position[2]
            d = horizontal_distance(s, point)
            if s.mario.airborne:
                if d < 65 and s.position[1] > y + 220:
                    return Action(z=True)
                return air_steer(s, point)
            if d > 550:
                return steer(s, point, 80)
            a = steer(s, point, 64)
            if s.frame - self.last_jump > 40:
                self.last_jump = s.frame
                return replace(a, a=True)
            return a
        if boss.action in (3, 4, 5, 6):
            self.phase = "dodge"
            t = x + 650 * math.cos(angle), z - 650 * math.sin(angle)
            self.target = t
            return air_steer(s, t) if s.mario.airborne else steer(s, t, 80)
        self.phase = "bait"
        t = (x + 250 * math.sin(angle), z + 250 * math.cos(angle))
        self.target = t
        return steer(s, t, 40)
