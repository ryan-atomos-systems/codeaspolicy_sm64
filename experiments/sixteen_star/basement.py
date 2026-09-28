"""Development skill retained from basement.py; see README.md for evidence and limits."""

from sm64_policy import Action
from sm64_policy.campaign.navigation import Route

class Basement:

    def __init__(self):
        self.route = Route([(-4500, -3300), (-3500, -2300), (-2400, -1200), (-1700, -750), (-1024, -750), (-1024, 600), (-1500, 0), (-1650, -600), (-1900, -1000), (-1024, -1400), (-1024, 1100)])
        self.phase = 'basement'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.area == 3:
            return Action()
        return self.route.act(s)

class ToLLL:

    def __init__(self):
        self.route = Route([(-1100, 2100, 1), (-1500, 2550), (-2200, 2650), (-2800, 2350), (-3100, 1750), (-3150, 900), (-2200, 700), (-1750, -1000), (-1400, -1800), (-1382, -3200), (-1382, -4600, 1)])
        self.phase = 'enter LLL'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.level != 6:
            return Action()
        return self.route.act(s)

class Return:

    def act(self, s):
        return Action(a=s.frame % 8 == 0)

class RepeatLLL:

    def __init__(self):
        self.route = Route([(-1382, -4600, 1)])
        self.phase = 'repeat LLL'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0 or (s.level == 22 and s.act == 0):
            return Action(a=s.frame % 8 == 0)
        if s.level != 6:
            return Action()
        return self.route.act(s)

class ToHMC:

    def __init__(self):
        self.route = Route([(-1382, -3000), (-600, -3000, 1), (500, -2662), (1500, -2662), (2500, -2662)])
        self.phase = 'enter HMC'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.level != 6:
            return Action()
        return self.route.act(s)

class HMCStep:

    def __init__(self):
        self.route = Route([(900, -2662, 2), (1500, -2662), (2500, -2662)])
        self.phase = 'HMC step'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.level != 6:
            return Action()
        return self.route.act(s)

class HMCToLLL:

    def __init__(self):
        self.route = Route([(3140, -1770, 1), (1400, -1770, 1), (1400, -2662), (500, -2662), (-600, -3000), (-1382, -3000), (-1382, -4600, 1)])
        self.phase = 'HMC to LLL'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if s.level != 6:
            return Action()
        return self.route.act(s)

class ToToad:

    def __init__(self):
        from .move import Waypoints
        self.route = Route([(-1382, -3000), (-600, -3000, 1), (500, -2662), (900, -2662, 2), (1500, -2662), (1800, -2350, 1)])
        self.phase = 'basement Toad'

    def act(self, s):
        from dataclasses import replace
        from sm64_policy.control import horizontal_distance, air_steer
        from .move import steer
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if self.route.index < 5:
            return self.route.act(s)
        stars = [o for o in s.objects.items if o.behavior_name in ('bhvStar', 'bhvStarSpawnCoordinates', 'bhvSpawnedStarNoLevelExit')]
        if stars:
            o = stars[0]
            t = (o.position[0], o.position[2])
            return air_steer(s, t, 18) if s.mario.airborne else replace(steer(s, t, 32), a=s.frame % 2 == 0)
        if s.position[0] < 1740:
            return self.route.act(s)
        t = (1787, -1957)
        return air_steer(s, t, 18) if s.mario.airborne else replace(steer(s, t, 24) if horizontal_distance(s, t) > 150 else Action(), b=s.frame % 8 == 0)
