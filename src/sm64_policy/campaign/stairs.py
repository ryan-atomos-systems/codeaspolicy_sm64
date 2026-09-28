"""Press the floor switch, climb the temporary stairs, and enter the pipe."""

from dataclasses import replace

from ..api import Action
from ..control import air_steer, horizontal_distance, steer


class Stairs:
    def __init__(self):
        self.phase = "switch"
        self.timer = None

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        switch = next(
            (o for o in s.objects.items if o.behavior_name == "bhvFloorSwitchAnimatesObject"), None
        )
        if self.phase == "switch":
            if switch and switch.action >= 2:
                self.phase = "stairs"
            else:
                t = (3922, -7)
                return steer(s, t, 32) if horizontal_distance(s, t) > 35 else Action()
        if s.position[0] > 5700:
            self.phase = "pipe"
        t = (6816, -7) if self.phase == "pipe" else (5700, -7)
        if s.mario.airborne:
            return air_steer(s, t, 32)
        # Pulsed jumps at the pipe rim can cancel a ledge climb repeatedly.
        # Complete the climb, then walk into the opening without jumping.
        if self.phase == "pipe" and s.position[1] >= 3050:
            return steer(s, t, 32)
        a = steer(s, t, 80)
        return replace(a, a=s.frame % 8 < 4)
