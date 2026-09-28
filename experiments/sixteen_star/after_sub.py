"""Development skill retained from after_sub.py; see README.md for evidence and limits."""

from sm64_policy import Action
from .move import Waypoints
from .bitfs_full import Full
from .mips_adjust import Adjust

class Finish:

    def __init__(self):
        self.route = Adjust(4147, 1997)
        self.skill = None
        self.phase = 'enter Fire Sea'
        self.last = None

    def act(self, s):
        if s.level == 6 and self.last in (19, 33):
            self.skill = None
        self.last = s.level
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.level == 23 or s.mario.action == 4864:
            return Action()
        if s.level in (19, 33):
            if self.skill is None:
                self.skill = Full()
            a = self.skill.act(s)
            self.phase = self.skill.phase
            return a
        if s.progress.save_flags & (32 | 128):
            self.phase = 'second key'
            return Action()
        return self.route.act(s)
