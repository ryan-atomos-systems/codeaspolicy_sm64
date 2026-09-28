"""Development skill retained from bitfs_full.py; see README.md for evidence and limits."""

from sm64_policy import Action
from .move import Waypoints
from .bitfs_safe import Safe as FireSea
from .bitfs_rise import Rise
from .bitfs_middle import Middle
from .bitfs_stretch import Stretch
from .bitfs_upper import Upper
from .bitfs_lava2 import Lava2
from .bitfs_cages import Cages
from .bitfs_cage3 import Third
from .bitfs_bridge import Bridge
from .bowser_safe import Safe

class Full:

    def __init__(self):
        self.i = 0
        self.skill = FireSea()
        self.phase = 'Fire Sea bottom'

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.level == 33:
            if self.i != 9:
                self.i = 9
                self.skill = Safe()
            self.phase = 'Bowser 2'
            return self.skill.act(s)
        if self.i == 0 and s.position[0] > 3800 and (s.position[1] > -2800) and (not s.mario.airborne):
            self.i = 1
            self.skill = Rise()
        if self.i == 1 and self.skill.upper.done:
            self.i = 2
            self.skill = Middle()
        if self.i == 2 and s.position[0] < -4400 and (s.position[1] > 0) and (not s.mario.airborne):
            self.i = 3
            self.skill = Stretch()
        if self.i == 3 and self.skill.route.done:
            self.i = 4
            self.skill = Upper()
        if self.i == 4 and self.skill.route.index >= 6:
            self.i = 5
            self.skill = Lava2()
        if self.i == 5 and s.position[0] > -180 and (s.position[1] >= 3788) and (not s.mario.airborne):
            self.i = 6
            self.skill = Cages()
        if self.i == 6 and self.skill.i == 2:
            self.i = 7
            self.skill = Third()
        if self.i == 7 and s.position[0] > 3500 and (s.position[1] > 4300) and (not s.mario.airborne):
            self.i = 8
            self.skill = Bridge()
        self.phase = f'Fire Sea {self.i} ' + getattr(self.skill, 'phase', '')
        return self.skill.act(s)
