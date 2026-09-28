"""Development primitive; consult README.md before composing a route."""

from .move import Waypoints

class Path:

    def __init__(self):
        self.route = Waypoints([(-1170, 2040), (-970, 1940), (-950, 1500), (-950, 1000), (-200, 1200), (-200, 2700)])

    def act(self, s):
        return self.route.act(s)
