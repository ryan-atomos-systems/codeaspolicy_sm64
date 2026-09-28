"""Development primitive; consult README.md before composing a route."""

from .move import Waypoints
from .ddd_full import Submarine
from sm64_policy import Action

class Entry:

    def __init__(self):
        self.route = Waypoints([(1500, 1997), (2700, 1997), (4400, 1997)])
        self.sub = Submarine()
        self.phase = 'enter DDD'

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.level == 23:
            self.phase = 'submarine star'
            return self.sub.act(s)
        return self.route.act(s)
