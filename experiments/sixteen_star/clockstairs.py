"""Development primitive; consult README.md before composing a route."""

from .move import Waypoints
from sm64_policy import Action

class Up:

    def __init__(self):
        self.route = Waypoints([(-1500, 6500), (-1800, 5500), (-1800, 5100, 3), (-1800, 4600, 3), (-1300, 4400, 3), (-950, 4200, 3), (-300, 4100, 3), (-200, 3400)])

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        return self.route.act(s)
