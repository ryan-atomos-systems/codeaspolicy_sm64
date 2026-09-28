"""Development skill retained from bits_stairs6.py; see README.md for evidence and limits."""

from .move import steer
from .step_fast import Steps
from sm64_policy import Action
from sm64_policy.control import air_steer
from dataclasses import replace

class Up:

    def __init__(self):
        self.phase = 0
        self.steps = Steps([(630, -234, -900), (1000, 22, -900), (1310, 278, -900), (1620, 534, -900), (1930, 790, -900), (2240, 1046, -900), (2630, 1301, -900), (2800, 1301, -900)])

    def act(self, s):
        if self.phase == 0:
            if s.position[0] > 450 and (not s.mario.airborne):
                self.phase = 1
            else:
                if s.mario.airborne:
                    return replace(air_steer(s, (590, -900), 48), a=True)
                a = steer(s, (590, -900))
                if s.position[0] > -240:
                    return replace(a, z=True, a=s.mario.action == 75531353)
                return a
        return self.steps.act(s)
