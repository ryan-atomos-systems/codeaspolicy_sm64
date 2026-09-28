"""Development skill retained from collect.py; see README.md for evidence and limits."""

from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer
from .move import steer

class Star:

    def __init__(self, star=0):
        self.star = star
        self.phase = 'collect star'

    def act(self, s):
        stars = [o for o in s.objects.items if o.behavior_name in ('bhvStar', 'bhvStarSpawnCoordinates') and o.behavior_params >> 24 == self.star]
        if not stars:
            return Action(a=s.frame % 8 == 0)
        o = stars[0]
        t = (o.position[0], o.position[2])
        return air_steer(s, t, 24) if s.mario.airborne else replace(steer(s, t, 32), a=s.frame % 2 == 0)
