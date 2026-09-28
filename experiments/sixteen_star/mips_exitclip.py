"""Development primitive; consult README.md before composing a route."""

from sm64_policy import Action
from sm64_policy.control import air_steer
from dataclasses import replace
from .move import steer

class Exit:

    def act(self, s):
        t = (-3097, 1800)
        return air_steer(s, t, 24) if s.mario.airborne else replace(steer(s, t, 40), a=s.frame % 2 == 0)
