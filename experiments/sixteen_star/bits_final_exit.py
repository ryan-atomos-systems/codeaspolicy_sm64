"""Development skill retained from bits_final_exit.py; see README.md for evidence and limits."""

from .bits_final_transfer2 import Transfer as Base
from sm64_policy import Action
from .move import steer
from .air_landing import air_steer
from dataclasses import replace

class Exit:

    def __init__(self):
        self.phase = 'center'
        self.target = (1200, -1100)

    def act(self, s):
        x, y, z = s.position
        if y > 5800 and x < 1400 and (not s.mario.airborne):
            self.phase = 'landed'
            return Action()
        on = next((o for o in s.objects.items if o.id == s.mario.platform_id and o.behavior_name == 'bhvFerrisWheelPlatform'), None)
        if self.phase == 'center':
            if on and abs(x - on.position[0] - 80) < 15:
                self.phase = 'wait high'
            else:
                return steer(s, ((on.position[0] if on else x) + 80, -1015), 24)
        if self.phase == 'wait high':
            if y > 6000 and on and (on.velocity[1] > 0):
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
