"""Development skill retained from bitfs_safe.py; see README.md for evidence and limits."""

from .bitfs import FireSea
from .air_landing import air_steer

class Safe(FireSea):

    def act(self, s):
        a = super().act(s)
        if self.left and s.mario.action == 50333832:
            return air_steer(s, self.route.points[self.route.index][:2], 48)
        return a
