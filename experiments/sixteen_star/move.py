"""Development skill retained from move.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance

def steer(s, t, magnitude=64):
    yaw = s.mario.face_angle[1] * math.tau / 65536
    err = (math.atan2(t[0] - s.position[0], t[1] - s.position[2]) - yaw + math.pi) % math.tau - math.pi

    def raw(v):
        return round(v + math.copysign(6, v)) if abs(v) > 0.2 else 0
    return Action(raw(-magnitude * math.sin(err)), raw(magnitude * math.cos(err)))

class Waypoints:

    def __init__(self, points):
        self.points = points
        self.index = 0
        self.jumped = False
        self.done = False

    def act(self, s):
        t = self.points[self.index]
        d = horizontal_distance(s, t[:2])
        mode = t[2] if len(t) > 2 else 0
        if d < 100 and (not s.mario.airborne or mode == 0):
            if self.index + 1 == len(self.points):
                self.done = True
                return Action()
            self.index += 1
            self.jumped = False
            t = self.points[self.index]
            mode = t[2] if len(t) > 2 else 0
            d = horizontal_distance(s, t[:2])
        if s.mario.airborne:
            return air_steer(s, t[:2], 48 if mode == 2 else 32)
        a = steer(s, t[:2], 64)
        yaw = s.mario.face_angle[1] * math.tau / 65536
        err = (math.atan2(t[0] - s.position[0], t[1] - s.position[2]) - yaw + math.pi) % math.tau - math.pi
        if mode and abs(err) > 0.15:
            return steer(s, t[:2], 24)
        if mode == 2:
            if s.mario.action == 75531353:
                return replace(a, a=True, z=True)
            if s.mario.forward_velocity > 25:
                return replace(a, z=True)
        if mode == 1:
            return replace(a, a=s.frame % 40 < 25)
        if mode == 3:
            return replace(a, a=s.frame % 2 == 0)
        return a

def turning_air(s, t):
    yaw = s.mario.face_angle[1] * math.tau / 65536
    d = horizontal_distance(s, t)
    err = (math.atan2(t[0] - s.position[0], t[1] - s.position[2]) - yaw + math.pi) % math.tau - math.pi
    turn = max(-1, min(1, err * 4))
    speed = min(32, d * 0.12)
    if abs(err) > 1:
        speed = 0
    acc = max(-1, min(1, speed - s.mario.forward_velocity))
    norm = math.hypot(turn, acc)
    if norm < 0.1:
        return Action()
    mag = 64 * math.sqrt(min(1, norm))

    def raw(v):
        return round(v + math.copysign(6, v)) if abs(v) > 0.2 else 0
    return Action(raw(-mag * turn / norm), raw(mag * acc / norm))
