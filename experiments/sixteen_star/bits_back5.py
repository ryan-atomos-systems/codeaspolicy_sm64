"""Development skill retained from bits_back5.py; see README.md for evidence and limits."""

from .step_crawl import Steps
from sm64_policy import Action

class Back:

    def __init__(self):
        self.route = Steps([(-6120, -921, -850), (-5700, -716, -850), (-5650, -716, -850), (-4950, -409, -850), (-3800, -409, -850), (-3350, -409, -850)])

    def act(self, s):
        if s.mario.action == 134218571:
            return Action(a=s.frame % 2 == 0)
        if s.mario.action in (1356, 1357, 1359):
            return Action()
        return self.route.act(s)
