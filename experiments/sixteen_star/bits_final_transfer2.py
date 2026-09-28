"""Development skill retained from bits_final_transfer2.py; see README.md for evidence and limits."""

import math
from sm64_policy import Action
from .move import steer
from .air_landing import air_steer
from dataclasses import replace

class Transfer:

    def __init__(self):
        self.phase = 'center'
        self.target = (2450, -1015)

    def act(self, s):
        x, y, z = s.position
        on = next((o for o in s.objects.items if o.id == s.mario.platform_id and o.behavior_name == 'bhvFerrisWheelPlatform'), None)
        if on and on.position[1] > 5200:
            self.phase = 'upper wheel'
            return Action()
        if self.phase == 'center':
            if on and abs(x - on.position[0] - 100) < 15:
                self.phase = 'wait high'
            else:
                return steer(s, ((on.position[0] if on else x) + 100, -1020), 24)
        if self.phase == 'wait high':
            if y > 5080 and on and (on.velocity[1] > 0):
                self.phase = 'launch'
            else:
                return Action()
        if s.mario.airborne:
            return air_steer(s, self.target, 48)
        a = steer(s, self.target, 64)
        if s.mario.action == 75531353:
            return replace(a, z=True, a=True)
        if s.mario.forward_velocity > 16:
            return replace(a, z=s.frame % 2 == 0)
        return a
