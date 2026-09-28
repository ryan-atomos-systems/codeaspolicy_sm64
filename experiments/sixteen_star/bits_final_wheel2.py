"""Development skill retained from bits_final_wheel2.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from .air_landing import air_steer
from .move import Waypoints, steer

class Board:

    def __init__(self):
        self.route = Waypoints([(1950, -1020)])
        self.target = None
        self.phase = 'wait lower wheel'

    def act(self, s):
        if any((o.id == s.mario.platform_id and o.behavior_name == 'bhvFerrisWheelPlatform' for o in s.objects.items)):
            self.phase = 'aboard'
            return Action()
        if not self.route.done:
            return self.route.act(s)
        if s.mario.airborne:
            return air_steer(s, self.target or (2800, -1020), 48)
        if not self.target:
            for o in s.objects.items:
                if o.behavior_name != 'bhvFerrisWheelPlatform' or not 4200 < o.position[1] < 5200:
                    continue
                theta = math.atan2(o.position[1] - 4701, o.position[0] - 3114) + 0.03835 * 35
                x = 3114 + 400 * math.cos(theta)
                y = 4803 + 400 * math.sin(theta)
                if x < 2950 and 4460 < y < 4580:
                    self.target = (x, -1020)
                    break
            if not self.target:
                return Action()
        a = steer(s, self.target, 64)
        if s.mario.action == 75531353:
            return replace(a, z=True, a=True)
        if s.mario.forward_velocity > 16:
            return replace(a, z=s.frame % 2 == 0)
        return a
