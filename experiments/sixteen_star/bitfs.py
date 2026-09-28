"""Development skill retained from bitfs.py; see README.md for evidence and limits."""

import math
from dataclasses import replace
from sm64_policy import Action
from sm64_policy.control import air_steer, horizontal_distance
from .move import Waypoints, steer, turning_air

class FireSea:

    def __init__(self):
        self.phase = 'approach cart'
        self.riding = False
        self.boarding = False
        self.left = False
        self.route = Waypoints([(-4300, -400, 1), (-2866, -715, 2), (-1945, -715, 2), (-1650, -600), (-300, 300, 2), (0, 300), (1100, 300, 2), (2400, 300, 2), (3600, 266), (3890, 266, 3)])

    def act(self, s):
        if s.ui.dialog_id >= 0:
            return Action(a=s.frame % 8 == 0)
        if self.left:
            self.phase = 'bottom path'
            t = self.route.points[self.route.index][:2]
            if s.mario.action == 16910519:
                return turning_air(s, t)
            a = self.route.act(s)
            if len(self.route.points[self.route.index]) > 2 and self.route.points[self.route.index][2] == 2 and (not s.mario.airborne):
                if s.mario.action == 75531353:
                    return replace(a, a=True, z=True)
                if s.mario.forward_velocity > 16:
                    return replace(a, z=True)
            return a
        cart = next((o for o in s.objects.items if o.behavior_name == 'bhvPlatformOnTrack'), None)
        if cart is None:
            return steer(s, (-6400, 0))
        on = (s.mario.platform_id == cart.id or (s.mario.floor and s.mario.floor.object_id == cart.id)) and (not s.mario.airborne)
        if on:
            self.riding = True
            self.phase = 'ride cart'
            if cart.position[0] > -4900:
                self.left = True
                return Action()
            t = (cart.position[0], cart.position[2])
            return steer(s, t, 32) if horizontal_distance(s, t) > 75 else Action()
        if s.position[0] < -6370 and (not self.boarding):
            return steer(s, (-6340, 0))
        if cart.position[0] < -5500:
            self.boarding = True
        if not self.boarding:
            return Action()
        self.phase = 'board cart'
        t = (cart.position[0] + cart.velocity[0] * 10, cart.position[2])
        if s.mario.action == 16910519:
            return turning_air(s, t)
        if s.mario.airborne:
            return air_steer(s, t, 48)
        a = steer(s, t)
        if s.mario.action == 75531353:
            return replace(a, a=True, z=True)
        return replace(a, z=s.mario.forward_velocity > 16)
