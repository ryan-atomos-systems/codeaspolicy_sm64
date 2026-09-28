"""Development skill retained from beast.py; see README.md for evidence and limits."""

from .lake import Lake
from .dorrie_star import DorrieStar

class Beast:

    def __init__(self):
        self.route = Lake()
        self.dorrie = DorrieStar()
        self.arrived = False
        self.phase = 'lake'

    def act(self, s):
        self.arrived = self.arrived or s.mario.swimming
        if self.arrived:
            self.phase = self.dorrie.phase
            return self.dorrie.act(s)
        return self.route.act(s)
