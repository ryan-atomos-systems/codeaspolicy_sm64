"""Development primitive; consult README.md before composing a route."""

from .move import Waypoints

class Carry:

    def __init__(self):
        self.route = Waypoints([(-3097, 1900), (-3000, 2300), (-2700, 2550), (-2300, 2680), (-1900, 2600), (-1500, 2400), (-1100, 2100), (-700, 1997), (0, 1997), (260, 1997)])

    def act(self, s):
        return self.route.act(s)
