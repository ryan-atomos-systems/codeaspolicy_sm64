"""Development skill retained from campaign.py; see README.md for evidence and limits."""

from sm64_policy import Action
from sm64_policy.campaign.policy import FirstBowser
from sm64_policy.campaign.navigation import Route
from .wall import Wall
from .basement import Basement, ToLLL, RepeatLLL, ToHMC, HMCStep, ToToad
from .lll import Reds, BigBully, TrioSafe
from .volcano import VolcanoStar
from .beast import Beast

class Campaign(FirstBowser):

    def __init__(self):
        super().__init__()
        self.stage = 'opening'
        self.sub = None
        self.last_area = None
        self.course_goal = None
        self.retry = 0

    def enter(self, s):
        previous = self.level
        super().enter(s)
        if self.stage == 'opening':
            if s.level == 6 and previous == 24 and (not s.progress.has_star(2, 6)):
                self.route = Route([(256, -5100, 1)])
            if s.level == 24 and s.progress.has_star(2, 3) and (not s.progress.has_star(2, 6)):
                self.skill, self.target_star = (Wall(), 6)

    def act(self, s, f):
        if self.stage == 'opening':
            if s.level == 6 and s.progress.save_flags & 80:
                self.stage = 'basement'
                self.sub = Basement()
            else:
                return super().act(s, f)
        if s.level == 16:
            if self.level != 16:
                self.level = 16
                self.sub = Route([(-1300, 3100), (0, 2000), (0, 200), (0, -1100), (0, -1700), (-76, -3350)])
            return self.sub.act(s)
        if self.level == 16 and s.level == 6:
            self.stage = 'basement'
            self.sub = Basement()
            self.sub.route = Route([(-1024, 600), (-1024, 0), (-1024, -750), (-1700, -750), (-1900, -1000), (-1024, -1400), (-1024, 1100)])
            self.level = 6
        if s.health <= 0:
            return Action()
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0 or (s.act == 0 and s.level in (7, 22, 24)):
            return Action(a=s.frame % 8 == 0)
        if self.stage == 'basement':
            if s.level == 6 and s.area == 3:
                self.stage = 'courses'
                self.level = None
            else:
                return self.sub.act(s)
        if self.level != s.level:
            previous = self.level
            self.level = s.level
            if s.level == 6:
                missing = next((star for star in (3, 1, 2, 5) if not s.progress.has_star(7, star)), None)
                if missing:
                    self.sub = ToLLL() if previous is None else RepeatLLL()
                elif not s.progress.has_star(0, 1):
                    self.sub = ToToad()
                elif not s.progress.has_star(6, 1):
                    self.sub = Route([(2400, -2662)])
                else:
                    self.stage = 'fifteen stars'
                    self.sub = None
            elif s.level == 22:
                self.course_goal = next((star for star in (3, 1, 2, 5) if not s.progress.has_star(7, star)), None)
                self.sub = {3: Reds, 1: BigBully, 2: TrioSafe, 5: VolcanoStar}[self.course_goal]()
            elif s.level == 7:
                self.course_goal = 1
                self.sub = Beast()
        self.phase = f"{self.stage}: {getattr(self.sub, 'phase', '')}"
        if self.stage == 'fifteen stars':
            return Action()
        if s.level == 6 and isinstance(self.sub, ToToad) and s.progress.has_star(0, 1):
            self.sub = Route([(2400, -2662)])
        if s.level in (7, 22) and s.progress.has_star(6 if s.level == 7 else 7, self.course_goal):
            return Action(a=s.frame % 8 == 0)
        return self.sub.act(s)
