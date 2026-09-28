"""Wake Hoot, hold on, steer, and release above the cage."""

import math
from dataclasses import replace

from ..api import Action
from ..control import air_steer, horizontal_distance, steer


class Owl:
    def __init__(self):
        self.phase = "tree"
        self.target = None
        self.last_jump = -100
        self.awake = False

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        owl = next((o for o in s.objects.items if o.behavior_name == "bhvHoot"), None)
        if owl is None:
            return Action()
        if s.mario.action == 0x000004A8:
            self.phase = "fly"
            self.target = (2880, 190)
            if s.position[1] > 4300 and horizontal_distance(s, self.target) < 90:
                self.phase = "drop"
                return Action()
            yaw = owl.face_angle[1] * math.tau / 65536
            err = (
                math.atan2(2880 - s.position[0], 190 - s.position[2]) - yaw + math.pi
            ) % math.tau - math.pi
            return Action(round(max(-80, min(80, -err * 65536 / math.tau / 5 * 0.15))), a=True)
        if self.phase in ("fly", "drop"):
            self.phase = "drop"
            return replace(air_steer(s, (2880, 190), 30), a=False)
        self.awake = self.awake or math.dist(owl.position, (2560, 700, 4608)) > 20
        if not self.awake:
            self.target = (2560, 4608)
            if s.mario.on_pole:
                return Action(stick_y=80)
            a = steer(s, self.target, 40)
            return replace(a, a=s.frame % 40 < 25)
        self.phase = "catch"
        self.target = (owl.position[0] + owl.velocity[0] * 5, owl.position[2] + owl.velocity[2] * 5)
        if s.mario.on_pole:
            return Action(a=True)
        if s.mario.airborne:
            return air_steer(s, self.target, 30)
        a = steer(s, self.target, 64)
        if horizontal_distance(s, self.target) < 450 and s.frame - self.last_jump > 40:
            self.last_jump = s.frame
            return replace(a, a=True)
        return a
