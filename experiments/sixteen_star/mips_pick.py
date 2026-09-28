"""Development primitive; consult README.md before composing a route."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import horizontal_distance
from .move import steer

class Pick:

    def act(self, s):
        if s.mario.held_object_id:
            return Action()
        m = next((o for o in s.objects.items if o.behavior_name == 'bhvMips'))
        t = (m.position[0], m.position[2])
        d = horizontal_distance(s, t)
        if s.mario.airborne:
            return Action()
        e = (math.atan2(t[0] - s.position[0], t[1] - s.position[2]) - s.mario.face_angle[1] * math.tau / 65536 + math.pi) % math.tau - math.pi
        a = steer(s, t, 24 if d > 120 else 16) if d > 82 or abs(e) > 0.3 else Action()
        return replace(a, b=d < 110 and s.frame % 40 == 0)
