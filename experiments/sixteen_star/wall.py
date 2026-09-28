"""Development skill retained from wall.py; see README.md for evidence and limits."""

"""Open the cannon, solve its discrete ballistic arc, and descend the pole."""
import math
from dataclasses import replace
from functools import lru_cache
from sm64_policy.api import Action
from sm64_policy.control import air_steer, horizontal_distance, steer
from sm64_policy.campaign.navigation import Route
from sm64_policy.campaign.whomp_climb import Whomp

@lru_cache(maxsize=16)
def ballistic_pitch(d: float, height: float, target_height: float):
    best = None
    for k in range(100, 10001, 10):
        angle = k * math.tau / 65536
        v = 100 * math.cos(angle)
        y = height + 120 * math.sin(angle)
        x = 120 * math.cos(angle)
        vy = 100 * math.sin(angle)
        while x < d:
            y += vy
            vy -= 1
            x += v
            v -= 0.05
        err = abs(y - target_height)
        if best is None or err < best[0]:
            best = (err, k)
    return best

class Wall:

    def __init__(self, retry=False):
        self.phase = 'approach'
        self.climb = Whomp()
        self.route = Route([(-2500, -800), (-2200, 1400), (-1900, 3300), (-1700, 3500)])
        self.target = None
        self.shot = False
        self.returning = None
        if retry:
            self.climb.i = 9
            self.route = Route([(-1700, 3500)])

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.mario.action == 4977:
            self.phase = 'aim'
            t = (650, 2370, 2970) if any((o.behavior_name == 'bhvWfBreakableWallRight' for o in s.objects.items)) else (590, 2400, 2650)
            dx = t[0] - s.position[0]
            dz = t[2] - s.position[2]
            d = math.hypot(dx, dz)
            best = ballistic_pitch(d, s.position[1], t[1])
            yaw = math.atan2(dx, dz) * 65536 / math.tau
            ey = (yaw - s.mario.face_angle[1] + 32768) % 65536 - 32768
            ep = best[1] - s.mario.face_angle[0]
            self.target = (best, ey, ep)
            if abs(ey) < 30 and abs(ep) < 30:
                self.shot = True
                self.returning = None
                return Action(a=True)

            def stick(e):
                v = max(-60, min(60, -e / 5 * 0.35))
                return round(v + math.copysign(6, v)) if abs(v) > 1 else 0
            return Action(stick(ey), stick(ep))
        if self.shot and (not s.mario.airborne) and (s.position[1] < 1400):
            from .move import Waypoints
            self.returning = Waypoints([(-500, 3900), (-1500, 3900, 3), (-1844, 3893)])
            self.shot = False
        if self.returning is not None:
            self.phase = 'reload cannon'
            return self.returning.act(s)
        if self.shot:
            self.phase = 'shot'
            if s.mario.on_pole:
                return Action(stick_y=-80)
            if not s.mario.airborne:
                return replace(steer(s, (590, 2650), 40), a=horizontal_distance(s, (590, 2650)) < 200 and s.frame % 40 < 25)
            return air_steer(s, (590, 2650)) if s.mario.action != 8915096 else Action()
        if self.climb.i < 9:
            self.phase = 'climb'
            return self.climb.act(s)
        if self.route.index < len(self.route.points) - 1:
            self.phase = 'approach cannon'
            return self.route.act(s)
        if s.progress.cannon_unlocked_mask & 1 << 2:
            self.phase = 'enter'
            return steer(s, (-1844, 3893), 40)
        self.phase = 'buddy'
        return replace(self.route.act(s), b=s.frame % 8 == 0)
