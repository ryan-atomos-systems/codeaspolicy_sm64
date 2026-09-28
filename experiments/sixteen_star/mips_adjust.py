"""Development skill retained from mips_adjust.py; see README.md for evidence and limits."""

from sm64_policy import Action
from .move import steer
from sm64_policy.control import horizontal_distance

class Adjust:

    def __init__(self, x=-3170, z=1332):
        self.t = (x, z)

    def act(self, s):
        return steer(s, self.t, 20) if horizontal_distance(s, self.t) > 2 else Action()
