"""Development skill retained from bowser.py; see README.md for evidence and limits."""

from .bowser_base import Fight
from sm64_policy import Action
from sm64_policy.control import air_steer
from .move import steer
from dataclasses import replace

class Battle(Fight):

    def act(self, s):
        grand = next((o for o in s.objects.items if o.behavior_name == 'bhvGrandStar'), None)
        if grand:
            self.phase = 'Grand Star'
            t = (grand.position[0], grand.position[2])
            return air_steer(s, t, 24) if s.mario.airborne else replace(steer(s, t, 40), a=s.frame % 2 == 0)
        return super().act(s, s.frame)
