"""Development primitive; consult README.md before composing a route."""

from sm64_policy import Action
from sm64_policy.control import air_steer
from dataclasses import replace
from .move import steer

class Out:

    def __init__(self):
        self.jumped = False

    def act(self, s):
        t = (-3097, 1800)
        if not self.jumped:
            if s.position[2] < 1434:
                return Action()
            self.jumped = True
            return replace(steer(s, t, 40), a=True)
        if s.mario.airborne:
            return air_steer(s, t, 24)
        return steer(s, t, 40)
