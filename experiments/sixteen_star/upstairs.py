"""Development primitive; consult README.md before composing a route."""

from .move import Waypoints
from sm64_policy import Action

class Upstairs:

    def __init__(self):
        self.route = Waypoints([(-1024, 500), (-1024, -1000), (-1024, -1400)])
        self.phase = 'unlock upstairs'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.level != 6 or s.area != 1:
            return Action()
        return self.route.act(s)
