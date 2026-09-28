"""Development skill retained from lake.py; see README.md for evidence and limits."""

from sm64_policy import Action
from .move import Waypoints

class Lake:

    def __init__(self, start=0):
        self.route = Waypoints([(-6650, 6000), (-6553, 4200), (-6553, 2400, 2), (-6553, 1800), (-6553, 1000), (-6700, -1000), (-6300, -3000), (-6100, -5000), (-6330, -6600, 1), (-6100, -7400, 1), (-5400, -7551), (-4500, -7551), (-3533, -7040)])
        self.phase = 'lake'
        self.route.index = start
        self.down = Waypoints([(-3500, -6100), (-3500, -4400), (-3500, -2500), (-3500, -500), (-3500, 1700), (-3600, 3400)])

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if self.route.done:
            if s.position[1] > -2400:
                return Action()
            return self.down.act(s)
        return self.route.act(s)
