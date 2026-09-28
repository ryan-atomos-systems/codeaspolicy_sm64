"""The Secret Aquarium: yaw, pitch, and stroke feedback."""

import math

from ..api import Action


class Aquarium:
    points = (
        (1500, -2200, 0),
        (0, -2200, 1500),
        (-1500, -2200, 0),
        (0, -2200, -1500),
        (-2400, -4607, -2400),
        (-2400, -4607, 2400),
        (2400, -4607, 2400),
        (2400, -4607, -2400),
        (0, -4250, 0),
    )

    def __init__(self):
        self.i = 0

    def act(self, s):
        target = self.points[self.i]
        if math.dist(s.position, target) < 110 and self.i < 8:
            self.i += 1
            target = self.points[self.i]
        stars = [
            o for o in s.objects.items if o.behavior_name in ("bhvStar", "bhvStarSpawnCoordinates")
        ]
        if stars:
            target = stars[0].position
        x, y, z = target
        dx, dz = x - s.position[0], z - s.position[2]
        d = math.hypot(dx, dz)
        yaw = s.mario.face_angle[1] * math.tau / 65536
        err = (math.atan2(dx, dz) - yaw + math.pi) % math.tau - math.pi
        wanted = max(-600, min(600, err * 65536 / math.tau * 0.1))
        sx = -wanted / 10
        pitch = max(-1.3, min(1.3, math.atan2(y - s.position[1] + 35, d)))
        sy = -pitch * 65536 / math.tau / 252

        def raw(v):
            return round(v + math.copysign(6, v)) if abs(v) > 1 else 0

        return Action(
            max(-80, min(80, raw(sx))),
            max(-80, min(80, raw(sy))),
            a=abs(err) < 0.6 and s.frame % 16 != 0,
        )
