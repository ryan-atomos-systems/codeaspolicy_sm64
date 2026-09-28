"""Development skill retained from bowser_base.py; see README.md for evidence and limits."""

"""Bowser: circle to the tail, spin, aim at a mine, and collect the key."""
import math
from dataclasses import replace
from sm64_policy.api import Action
from sm64_policy.control import horizontal_distance
from .move import steer
from sm64_policy.decision_trace import record_gate

class Fight:

    def __init__(self):
        self.phase = 'approach'
        self.spin = 0
        self.throws = 0

    def act(self, s, f):
        if s.ui.dialog_id >= 0:
            return Action(a=f % 8 == 0)
        objs = s.objects.items
        bow = next((o for o in objs if o.behavior_name == 'bhvBowser'), None)
        tail = next((o for o in objs if o.behavior_name == 'bhvBowserTailAnchor'), None)
        key = next((o for o in objs if o.behavior_name == 'bhvBowserKey'), None)
        if key:
            self.phase = 'key'
            return replace(steer(s, (key.position[0], key.position[2])), a=f % 45 < 25)
        if s.mario.held_object_id:
            self.phase = 'spin'
            self.spin += 1
            mines = [o for o in objs if o.behavior_name == 'bhvBowserBomb']
            mines = sorted(mines, key=lambda o: math.dist(o.position, s.position))[:1]
            yaw = s.mario.face_angle[1] * math.tau / 65536
            best = min(mines, key=lambda o: abs((math.atan2(o.position[0] - s.position[0], o.position[2] - s.position[2]) - yaw + math.pi) % math.tau - math.pi))
            err = (math.atan2(best.position[0] - s.position[0], best.position[2] - s.position[2]) - yaw + math.pi) % math.tau - math.pi
            record_gate('Release Bowser toward bomb', {'angular speed > 4000': abs(s.mario.angular_velocity[1]) > 4000, 'aim error < 0.15 rad': abs(err) < 0.15}, object_id=best.id, target_position=best.position, aim_error_degrees=math.degrees(err), angular_speed=s.mario.angular_velocity[1])
            if abs(s.mario.angular_velocity[1]) > 4000 and abs(err) < 0.15:
                self.throws += 1
                return Action(b=True)
            if self.spin % 64 == 0:
                return Action()
            a = self.spin * 0.3
            return Action(round(-70 * math.sin(a)), round(70 * math.cos(a)))
        if bow is None:
            return Action()
        if bow.health <= 0:
            self.phase = 'defeated'
            return steer(s, (bow.position[0], bow.position[2]), 40) if horizontal_distance(s, (bow.position[0], bow.position[2])) > 320 else Action()
        if bow.action in (1, 4, 12, 19):
            self.phase = 'wait'
            return Action()
        self.phase = 'circle'
        bx, _, bz = bow.position
        mx, _, mz = s.position
        theta = math.atan2(mx - bx, mz - bz)
        tailtheta = math.atan2(tail.position[0] - bx, tail.position[2] - bz)
        err = (tailtheta - theta + math.pi) % math.tau - math.pi
        if abs(err) < 0.5:
            point = (tail.position[0], tail.position[2])
        else:
            heading = theta + 0.6
            point = (bx + 280 * math.sin(heading), bz + 280 * math.cos(heading))
        a = steer(s, point)
        if math.dist(s.position, tail.position) < 150:
            a = replace(a, b=f % 2 == 0)
        return a
