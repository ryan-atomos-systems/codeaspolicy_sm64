"""Development skill retained from bowser_safe.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from .bowser import Battle
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance
from .move import steer

class Safe(Battle):

    def __init__(self):
        super().__init__()
        self.safe = None
        self.until = 0

    def act(self, s):
        a = super().act(s)
        if s.ui.dialog_id >= 0 or s.mario.held_object_id or self.phase in ('Grand Star', 'defeated'):
            return a
        flames = [o for o in s.objects.items if o.behavior_name in ('bhvFlameLargeBurningOut', 'bhvFlameBouncing', 'bhvFlameFloatingLanding', 'bhvFlameMovingForwardGrowing')]
        if flames and (len(flames) > 10 or s.mario.action in (16910516, 132169, 16910517)):
            if s.frame >= self.until or self.safe is None:
                candidates = [(r * math.sin(i * math.tau / 16), r * math.cos(i * math.tau / 16)) for r in (1000, 1600, 2100) for i in range(16)]
                self.safe = max(candidates, key=lambda p: min((math.hypot(p[0] - o.position[0], p[1] - o.position[2]) for o in flames)) - horizontal_distance(s, p) * 0.25)
                self.until = s.frame + 90
            self.phase = 'avoid fire field'
            t = self.safe
            if s.mario.airborne:
                return air_steer(s, t, 32)
            a = steer(s, t, 64) if horizontal_distance(s, t) > 150 else Action()
            if s.mario.action == 132169:
                return a
            nearest = min((math.hypot(o.position[0] - s.position[0], o.position[2] - s.position[2]) for o in flames))
            return replace(a, a=nearest < 500 and s.frame % 2 == 0)
        if self.phase == 'wait':
            t = (1500, 1200)
            return air_steer(s, t, 32) if s.mario.airborne else steer(s, t) if horizontal_distance(s, t) > 120 else Action()
        return a
