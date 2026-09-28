"""Princess’s Secret Slide: velocity feedback and reward collection."""

import math

from ..api import Action
from ..control import air_steer, horizontal_distance, steer

points = [
    (3000, -5640),
    (780, -5600),
    (-809, -5600),
    (-2409, -5600),
    (-4445, -5536),
    (-5636, -5054),
    (-6263, -4009),
    (-5980, 945),
    (-2870, 2300),
    (-880, 2280),
    (260, 2280),
    (3930, 2425),
    (5174, 3200),
    (5707, 4565),
    (5194, 5845),
    (3640, 6450),
    (2550, 6050),
    (1821, 4616),
    (1860, 1680),
    (1880, 60),
    (1860, -1720),
    (1854, -4290),
    (-20, -6304),
    (-1197, -4692),
    (-2565, -3525),
    (-4909, -4218),
    (-6290, -2545),
    (-6400, -590),
    (-6400, 1409),
    (-6400, 3481),
    (-6385, 5770),
]


class Slide:
    def __init__(self):
        self.i = 0

    def act(self, s):
        t = points[self.i]
        d = horizontal_distance(s, t)
        if d < 850 and self.i < len(points) - 1:
            self.i += 1
            t = points[self.i]
        a = steer(s, t, 80)
        if not s.mario.airborne and abs(s.mario.forward_velocity) > 35:
            angle = math.atan2(s.velocity[0], s.velocity[2])
            want = math.atan2(t[0] - s.position[0], t[1] - s.position[2])
            err = (want - angle + math.pi) % math.tau - math.pi
            heading = angle + max(-1.5, min(1.5, err * 6))
            a = steer(
                s,
                (
                    s.position[0] + 1000 * math.sin(heading),
                    s.position[2] + 1000 * math.cos(heading),
                ),
                80,
            )
        if self.i == len(points) - 1:
            stars = [
                o
                for o in s.objects.items
                if not s.progress.has_star(19, ((o.behavior_params >> 24) & 255) + 1)
                and "Star" in o.behavior_name
                and o.behavior_name in ("bhvStar", "bhvStarSpawnCoordinates", "bhvSpawnedStar")
            ]
            t = (stars[0].position[0], stars[0].position[2]) if stars else points[-1]
            d = horizontal_distance(s, t)
            if s.mario.airborne:
                if not stars and d < 50 and s.position[1] > -4180:
                    return Action(z=True)
                return air_steer(s, t)
            a = steer(s, t, 64)
            return Action(
                a.stick_x,
                a.stick_y,
                a=d < 800 and s.frame % 40 < 24,
                b=d < 150 and s.frame % 40 >= 24,
            )
        return a
