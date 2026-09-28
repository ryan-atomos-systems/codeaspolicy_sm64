"""Development skill retained from ddd_board3.py; see README.md for evidence and limits."""

from dataclasses import replace
from .ddd_board2 import Board2
from .step_route import Steps as JumpRoute
from .move import Waypoints, steer
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance

class Board3(Board2):

    def __init__(self):
        super().__init__()
        self.jumps = JumpRoute([(6100, 100, 2000), (5750, 300, 2000), (5350, 500, 2000), (4950, 700, 2000), (4200, 571, 2000)])
        self.walk = Waypoints([(4300, 1300), (4300, -700), (3900, -600, 3)])
        self.started = False

    def act(self, s):
        if s.mario.swimming:
            self.started = False
            return super().act(s)
        if not self.started:
            self.phase = 'floor switch'
            t = (6800, 2000)
            if horizontal_distance(s, t) > 60:
                return air_steer(s, t, 24) if s.mario.airborne else steer(s, t, 32)
            switch = next((o for o in s.objects.items if o.behavior_name == 'bhvFloorSwitchHiddenObjects'), None)
            if switch and switch.action == 2:
                self.started = True
                self.jumps.index = 0
                self.jumps.done = False
            else:
                return Action()
        self.phase = 'box staircase'
        if not self.jumps.done:
            return self.jumps.act(s)
        self.phase = 'submarine'
        return self.walk.act(s)
