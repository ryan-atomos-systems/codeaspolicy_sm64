"""Development skill retained from volcano_precise.py; see README.md for evidence and limits."""

from .volcano_inside import Inside
from .jumproute import JumpRoute

class Precise(Inside):

    def __init__(self):
        super().__init__()
        self.jumps = JumpRoute([(-1550, 1613, 2250), (-2050, 1679, 1500), (-2200, 1864, 940), (-2400, 1981, 250), (-2600, 2089, -350), (-2300, 2268, -1300), (-1400, 2442, -2400), (-500, 2442, -2650), (-100, 2460, -2530), (300, 2533, -2600), (650, 2606, -2700)])

    def act(self, s):
        if self.route.index >= 15:
            self.phase = f'precise {self.jumps.index} {self.jumps.phase}'
            return self.jumps.act(s)
        return super().act(s)
