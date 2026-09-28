"""Development primitive; consult README.md before composing a route."""

from .move import Waypoints

class Hop:

    def __init__(self):
        self.route = Waypoints([(0, 1997, 3), (260, 1997)])

    def act(self, s):
        return self.route.act(s)
