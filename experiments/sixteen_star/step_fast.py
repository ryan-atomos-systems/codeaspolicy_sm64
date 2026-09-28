"""Development skill retained from step_fast.py; see README.md for evidence and limits."""

from .step_crawl import Steps as Base
from sm64_policy import Action

class Steps(Base):

    def act(self, s):
        if s.mario.action in (67110010, 134218287):
            t = self.points[self.index]
            if s.position[1] >= t[1] - 20 and self.index < len(self.points) - 1:
                self.index += 1
            return Action(z=True, a=s.frame % 2 == 0)
        return super().act(s)
