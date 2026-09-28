"""Development primitive; consult README.md before composing a route."""

from .move import steer
from sm64_policy import Action
from sm64_policy.control import horizontal_distance, air_steer
from dataclasses import replace

class Enter:

    def act(self, s):
        if s.level != 6:
            return Action()
        if s.mario.airborne:
            return air_steer(s, (-230, -3352), 24)
        return replace(steer(s, (-230, -3352)), a=horizontal_distance(s, (-230, -3352)) < 380 and s.frame % 2 == 0)
