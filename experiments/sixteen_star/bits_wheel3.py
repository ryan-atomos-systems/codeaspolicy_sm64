"""Development skill retained from bits_wheel3.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer
from .move import Waypoints, steer

class Wheel:

    def __init__(self, delay=0):
        self.route = Waypoints([(-420, -794)])
        self.phase = 'wait wheel'
        self.launched = False
        self.target = (-1500, -794)
        self.delay = delay

    def act(self, s):
        if self.delay > 0:
            self.delay -= 1
            return Action()
        if any((o.id == s.mario.platform_id and o.behavior_name == 'bhvFerrisWheelPlatform' for o in s.objects.items)):
            return Action()
        if not self.route.done:
            return self.route.act(s)
        if s.mario.airborne:
            return air_steer(s, self.target, 40)
        if not self.launched:
            for o in s.objects.items:
                if o.behavior_name != 'bhvFerrisWheelPlatform' or o.position[0] > 0 or o.position[1] > 0:
                    continue
                ang = math.atan2(o.position[1] + 1330, o.position[0] + 1748) + 0.03835 * 30
                tx = -1748 + 400 * math.cos(ang)
                ty = -1330 + 400 * math.sin(ang) + 100
                if tx > -1650 and s.position[1] - 150 < ty < s.position[1] + 80 and (o.velocity[1] > 0):
                    self.target = (tx, -794)
                    self.launched = True
                    break
            if not self.launched:
                return Action()
        a = steer(s, self.target)
        if s.mario.action == 75531353:
            return replace(a, z=True, a=True)
        if s.mario.forward_velocity > 16:
            return replace(a, z=True)
        return a
