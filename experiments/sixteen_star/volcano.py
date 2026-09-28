"""Development skill retained from volcano.py; see README.md for evidence and limits."""

from sm64_policy import Action
from .move import Waypoints

class Volcano:

    def __init__(self):
        self.route = Waypoints([(-2800, 6272), (-1300, 6272, 2), (0, 6272), (0, 4500), (0, 3900, 1), (0, 3500, 3), (0, 2200, 2), (0, 1000, 3), (0, 0, 3)])
        self.phase = 'enter'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.area == 2 and s.act > 0:
            self.phase = 'inside'
            return Action()
        if s.mario.action == 16910519:
            from .move import turning_air
            return turning_air(s, (0, 0))
        return self.route.act(s)

class VolcanoStar(Volcano):

    def __init__(self):
        super().__init__()
        from .volcano_precise import Precise
        from .poles import Poles
        self.inside = Precise()
        self.poles = Poles()

    def act(self, s):
        if s.area == 2 and s.act > 0:
            if self.inside.jumps.done:
                self.phase = 'volcano poles'
                return self.poles.act(s)
            self.phase = self.inside.phase
            return self.inside.act(s)
        return super().act(s)
