"""Development skill retained from ddd_board2.py; see README.md for evidence and limits."""

from .ddd_board import Board
from .swim import swim
from dataclasses import replace

class Board2(Board):

    def __init__(self):
        super().__init__()
        self.east = False

    def act(self, s):
        self.east = self.east or s.position[0] > 5600
        if s.mario.swimming and (not self.east):
            return swim(s, (5900, -1200, 2000))
        if s.mario.swimming and s.position[0] > 6400 and (s.position[1] > -85):
            return replace(swim(s, (6800, 500, 2000)), stick_y=-80, a=s.frame % 4 == 0)
        return super().act(s)
