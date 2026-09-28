"""Development skill retained from bits_start.py; see README.md for evidence and limits."""

from .move import Waypoints
from sm64_policy import Action

class Start:

    def __init__(self):
        self.phase = 'start'
        self.route = Waypoints([(-5850, 0), (-5100, 0, 2), (-4400, 0, 3), (-3700, 0, 3), (-3500, 0, 3), (-3250, 0, 3), (-2850, 0, 3), (-2650, 0, 3), (-2300, 0, 3), (-1750, 0, 3), (0, 0, 2), (1450, 0, 2), (2300, 0), (2800, 0)])

    def act(self, s):
        if s.mario.action == 134218571:
            return Action(a=s.frame % 2 == 0)
        if s.mario.action in (1356, 1357, 1359):
            return Action()
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        return self.route.act(s)
