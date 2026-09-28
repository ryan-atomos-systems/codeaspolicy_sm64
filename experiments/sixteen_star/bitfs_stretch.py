"""Development skill retained from bitfs_stretch.py; see README.md for evidence and limits."""

from sm64_policy import Action
from .move import Waypoints, turning_air

class Stretch:

    def __init__(self):
        self.phase = 'stretching ramps'
        self.route = Waypoints([(-5600, 320), (-6100, 320), (-7160, 300), (-7160, -300), (-6550, -300), (-6020, -300), (-6020, 400), (-5480, 400), (-4950, 320), (-4200, 320), (-4200, -300), (-4920, -300), (-6030, -300)])

    def act(self, s):
        if s.mario.action == 16910519:
            return turning_air(s, self.route.points[self.route.index][:2])
        return self.route.act(s)
