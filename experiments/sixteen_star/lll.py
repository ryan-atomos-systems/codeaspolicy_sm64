"""Development skill retained from lll.py; see README.md for evidence and limits."""

from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import steer, air_steer, horizontal_distance
from .move import Waypoints as Route

class Reds:

    def __init__(self):
        self.route = Route([(-2800, 6272), (-1300, 6272, 2), (0, 6272), (0, 4500), (0, 3900, 1), (-1000, 3750, 1), (-2800, 3800, 2), (-3500, 3900), (-4100, 3600), (-5100, 3456), (-5119, 3000), (-5119, 1500, 2), (-5100, 1024)])
        self.phase = 'route'

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if self.route.index < len(self.route.points) - 1:
            return self.route.act(s)
        self.phase = 'coins'
        coins = [o for o in s.objects.items if o.behavior_name == 'bhvRedCoin']
        stars = [o for o in s.objects.items if o.behavior_name in ('bhvStar', 'bhvStarSpawnCoordinates') and o.behavior_params >> 24 == 2]
        objs = stars or coins
        if not objs:
            return Action()
        o = min(objs, key=lambda o: sum(((v - w) ** 2 for v, w in zip(o.position, s.position))))
        t = (o.position[0], o.position[2])
        return air_steer(s, t) if s.mario.airborne else replace(steer(s, t, 40), a=bool(stars) and s.frame % 40 < 25)

class Bully:

    def __init__(self):
        self.route = Route([(-2800, 6272), (-1300, 6272, 2), (0, 6272), (0, 4500), (0, 3900, 1), (-1000, 3750, 1), (-2800, 3800, 2), (-3500, 3900), (-4100, 3600), (-5100, 3456), (-5119, 3000), (-5119, 1500, 2), (-5100, 1024), (-5300, 0), (-5400, -1400, 1), (-5400, -2750, 1), (-5119, -4095, 2), (-3900, -4095, 2), (-2100, -4095, 2), (-200, -4385, 2)])
        self.phase = 'route'
        self.hit = False

    def act(self, s):
        if s.ui.dialog_id >= 0 or s.ui.menu_mode >= 0:
            return Action(a=s.frame % 8 == 0)
        if self.route.index < len(self.route.points) - 1:
            return self.route.act(s)
        self.phase = 'bully'
        stars = [o for o in s.objects.items if o.behavior_name in ('bhvStar', 'bhvStarSpawnCoordinates') and o.behavior_params >> 24 == 0]
        if stars:
            if s.position[2] > -5400:
                return replace(steer(s, (0, -5800)), a=s.frame % 40 < 25)
            o = stars[0]
            t = (o.position[0], o.position[2])
            return air_steer(s, t) if s.mario.airborne else replace(steer(s, t, 40), a=s.frame % 40 < 25)
        boss = next((o for o in s.objects.items if o.behavior_name == 'bhvBigBully'), None)
        if not boss:
            return self.route.act(s)
        t = (boss.position[0], boss.position[2])
        if s.position[1] < 250:
            return replace(steer(s, (0, -4385)), a=s.frame % 40 < 25)
        if s.mario.airborne:
            return replace(air_steer(s, t, 32), b=s.frame % 10 < 5)
        return replace(steer(s, t, 48), a=s.frame % 40 < 25, b=s.frame % 10 < 5)

class BigBully(Bully):

    def __init__(self):
        super().__init__()
        from .bullysearch import Fight
        self.fight = Fight(1)

    def act(self, s):
        if self.route.index < len(self.route.points) - 1:
            return super().act(s)
        self.phase = self.fight.phase
        return self.fight.act(s)

class Trio(Bully):

    def __init__(self):
        super().__init__()
        self.route.points = self.route.points[:-1] + [(-200, -4100, 3), (500, -4500, 1), (1800, -4607, 2), (3000, -5400, 2), (3800, -5500)]
        self.phase = 'route'

    def act(self, s):
        from .move import turning_air
        if self.route.index < len(self.route.points) - 1:
            return super().act(s)
        self.phase = 'trio'
        center = (3850, -5500)
        if s.mario.action == 16910519:
            return turning_air(s, center)
        stars = [o for o in s.objects.items if o.behavior_name in ('bhvStar', 'bhvStarSpawnCoordinates') and o.behavior_params >> 24 == 1]
        if stars:
            t = (stars[0].position[0], stars[0].position[2])
            return air_steer(s, t, 32) if s.mario.airborne else replace(steer(s, t, 40), a=s.frame % 2 == 0)
        small = [o for o in s.objects.items if o.behavior_name == 'bhvSmallBully' and o.position[0] > 2400 and (o.position[2] < -4500) and (o.position[1] > 200) and (o.action not in (4, 5, 100, 101))]
        big = [o for o in s.objects.items if o.behavior_name == 'bhvBigBullyWithMinions' and o.position[1] < 900 and (o.action not in (4, 5, 100, 101))]
        objs = small or big
        if not objs:
            return steer(s, center, 40) if horizontal_distance(s, center) > 100 else Action()
        boss = min(objs, key=lambda o: sum(((v - w) ** 2 for v, w in zip(o.position, s.position))))
        t = (boss.position[0], boss.position[2])
        if not 2540 < t[0] < 4880 or not -6150 < t[1] < -4850:
            t = center
        if s.mario.airborne:
            return air_steer(s, t, 32)
        return replace(steer(s, t), a=s.frame % 2 == 0)

class TrioRide(Trio):

    def __init__(self):
        super().__init__()
        from .meshride import Ride
        self.route.points = self.route.points[:20] + [(450, -4607)]
        self.ride = Ride()
        self.arrived = False

    def act(self, s):
        if self.route.index < len(self.route.points) - 1:
            return super().act(s)
        if s.position[0] > 2900 and s.position[2] < -4850 and (s.position[1] > 250) and (not s.mario.airborne):
            self.arrived = True
        if not self.arrived:
            self.phase = self.ride.phase
            return self.ride.act(s)
        return super().act(s)

class TrioSafe(Trio):

    def __init__(self):
        super().__init__()
        from .bullysearch import Fight
        from .meshride import Ride
        self.route.points = self.route.points[:19] + [(-1100, -4095), (-200, -4385, 2)]
        self.first = Fight(1)
        self.ride = Ride()
        self.dock = Route([(0, -4400), (450, -4607)])
        self.arrived = False
        self.defeated = False

    def act(self, s):
        if self.route.index < len(self.route.points) - 1:
            return super().act(s)
        self.defeated = self.defeated or any((o.behavior_name in ('bhvStar', 'bhvStarSpawnCoordinates') and o.behavior_params >> 24 == 0 for o in s.objects.items))
        if not self.defeated:
            self.phase = 'clear approach'
            return self.first.act(s)
        if not self.dock.done:
            self.phase = 'dock'
            return self.dock.act(s)
        if s.position[0] > 2900 and s.position[2] < -4850 and (s.position[1] > 250) and (not s.mario.airborne):
            self.arrived = True
        if not self.arrived:
            self.phase = self.ride.phase
            return self.ride.act(s)
        return super().act(s)

class TrioFight(Trio):

    def __init__(self):
        super().__init__()
        self.route.index = len(self.route.points) - 1
