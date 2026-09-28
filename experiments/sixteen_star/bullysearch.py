"""Development skill retained from bullysearch.py; see README.md for evidence and limits."""

from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import GroundPoundObject, air_steer, horizontal_distance
from .move import steer, Waypoints, turning_air

class Fight:

    def __init__(self, variant=0):
        self.phase = 'fight'
        self.variant = variant
        self.gp = GroundPoundObject(180)
        self.route = None

    def act(self, s):
        if s.mario.action == 16910519:
            return turning_air(s, (0, -4385))
        stars = [o for o in s.objects.items if o.behavior_name in ('bhvStar', 'bhvStarSpawnCoordinates') and o.behavior_params >> 24 == 0]
        if stars:
            self.phase = 'star'
            if self.route is None:
                self.route = Waypoints([(0, -4700), (0, -5000), (0, -5500, 3), (0, -5800, 3), (0, -6150, 3), (0, -6500, 3), (0, -6800, 3)])
            if self.route.done:
                from .collect import Star
                return Star(0).act(s)
            return self.route.act(s)
        boss = next((o for o in s.objects.items if o.behavior_name == 'bhvBigBully'), None)
        if not boss:
            return Action()
        t = (boss.position[0], boss.position[2])
        d = horizontal_distance(s, t)
        if abs(t[0]) > 670 or not -5050 < t[1] < -3910:
            return air_steer(s, (0, -4385), 32) if s.mario.airborne else steer(s, (0, -4385), 32) if horizontal_distance(s, (0, -4385)) > 50 else Action()
        if self.variant == 0:
            return self.gp.act(s, boss)
        if s.mario.airborne:
            return replace(air_steer(s, t, 32), b=self.variant == 2 and s.frame % 4 == 0)
        return replace(steer(s, t), a=self.variant == 1 and s.frame % 2 == 0, b=self.variant == 2 and s.frame % 4 == 0)
