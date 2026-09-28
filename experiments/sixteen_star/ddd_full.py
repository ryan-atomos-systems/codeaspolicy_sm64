"""Development skill retained from ddd_full.py; see README.md for evidence and limits."""

from .ddd import Sub
from .ddd_board3 import Board3

class Submarine:

    def __init__(self):
        self.swim = Sub()
        self.board = Board3()
        self.phase = 'submarine'
        self.ready = False

    def act(self, s):
        self.ready = self.ready or (s.area == 2 and s.position[0] > 2600)
        p = self.board if self.ready else self.swim
        a = p.act(s)
        self.phase = p.phase
        return a
