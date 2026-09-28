"""Development skill retained from bits_arrow10.py; see README.md for evidence and limits."""

from sm64_policy import Action
from .move import steer, Waypoints
from sm64_policy.control import air_steer
from dataclasses import replace

class Arrow:

    def __init__(self):
        self.phase = 'ride'
        self.route = Waypoints([(-2450, -900), (-3300, -900), (-3800, -900), (-4700, -900, 2), (-5600, -900, 2), (-6400, -900)])

    def act(self, s):
        o = next((o for o in s.objects.items if o.behavior_name == 'bhvActivatedBackAndForthPlatform'), None)
        if o and o.position[0] < -1900:
            self.phase = 'leave'
        if self.phase == 'leave':
            return self.route.act(s)
        if s.mario.action == 134218571:
            return Action(a=s.frame % 2 == 0) if s.position[0] > 1400 else Action(z=s.frame % 2 == 0)
        if s.mario.action in (1356, 1357, 1359):
            return Action()
        if s.position[1] > 2490:
            return steer(s, (o.position[0] - 150, -904), 64)
        if s.mario.airborne:
            return replace(air_steer(s, (o.position[0] - 300, -904), 32), a=False)
        return Action(z=True)
