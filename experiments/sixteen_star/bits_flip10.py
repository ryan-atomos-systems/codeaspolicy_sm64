"""Development skill retained from bits_flip10.py; see README.md for evidence and limits."""

from .sideflip_diagonal import Flip
from .mips_adjust import Adjust
from sm64_policy.control import horizontal_distance, air_steer
from dataclasses import replace
from sm64_policy import Action

class Jump:

    def __init__(self):
        self.stage = 0
        self.flip = Flip()
        self.approach = Adjust(-5605, -850)
        self.phase = 'approach'

    def act(self, s):
        if self.stage == 0:
            if not s.mario.airborne and horizontal_distance(s, (-5605, -850)) < 5:
                self.stage = 1
            else:
                return self.approach.act(s)
        self.phase = self.flip.phase
        if s.mario.airborne and s.mario.action == 16779399 and (s.velocity[1] < 26):
            return replace(air_steer(s, (-4950, -850), 32), b=True)
        if s.mario.action == 25692298:
            return Action(stick_y=80, a=True)
        return self.flip.act(s)
