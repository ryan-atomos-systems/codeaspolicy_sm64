"""Development skill retained from bits_arrow_blocks.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from .bits_arrow10 import Arrow as Base
from sm64_policy import Action
from .air_both import air_steer
from .move import steer

class Arrow(Base):

    def __init__(self):
        super().__init__()
        self.jumping = None
        self.index = 0
        self.blocks = [(284, 80, 2633), (-329, -534, 2633), (-1251, -1455, 2735), (-2070, -2275, 2735)]

    def act(self, s):
        x, y, z = s.position
        if self.jumping:
            r, l, h = self.jumping
            if not s.mario.airborne and y >= h - 10:
                self.jumping = None
                self.index += 1
            else:
                if s.mario.airborne:
                    return air_steer(s, ((r + l) / 2, -904), 32)
                yaw = s.mario.face_angle[1] * math.tau / 65536
                err = (math.pi / 2 - yaw + math.pi) % math.tau - math.pi
                if abs(err) > 0.1:
                    return replace(steer(s, (x + 100, -904), 32), z=True)
                return Action(z=True, a=s.mario.action in (201359904, 201359905))
        if self.index < len(self.blocks):
            r, l, h = self.blocks[self.index]
            if 70 < x - r < 260 and y < h - 80 and (not s.mario.airborne):
                self.jumping = self.blocks[self.index]
                return Action(z=True)
        if self.index == 4 and x < -2280:
            self.phase = 'leave'
        o = next((o for o in s.objects.items if o.behavior_name == 'bhvActivatedBackAndForthPlatform'), None)
        if self.phase == 'leave':
            return self.route.act(s)
        if s.mario.action == 134218571:
            return Action(a=s.frame % 2 == 0) if x > 1400 else Action(z=s.frame % 2 == 0)
        if s.mario.action in (1356, 1357, 1359):
            return Action()
        if y > 2490:
            return steer(s, ((o.position[0] if o else x) - 150, -904), 64)
        if s.mario.airborne:
            return replace(air_steer(s, ((o.position[0] if o else x) - 150, -904), 32), a=False)
        return Action(z=True)
