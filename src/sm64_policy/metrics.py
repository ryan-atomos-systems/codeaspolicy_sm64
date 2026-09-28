"""Gameplay summaries, independent of engine and artifact persistence."""

import math

from .api import Observation


class EpisodeMetrics:
    def __init__(self, initial: Observation):
        self.initial = self.previous = initial
        self.visited: set[tuple] = set()
        self.levels: set[int] = set()
        self.deaths = 0
        self.distance = self.displacement = 0.0
        self.height = initial.position[1]
        self.health = initial.health
        self.stars = initial.stars
        self.coins = initial.coins

    def update(self, observation: Observation) -> None:
        x, y, z = observation.position
        self.visited.add(
            (observation.level, observation.area, math.floor(x / 400), math.floor(z / 400))
        )
        self.deaths += int(observation.died)
        location = (observation.level, observation.area)
        if not observation.died and location == (self.previous.level, self.previous.area):
            self.distance += math.dist(observation.position, self.previous.position)
        if location == (self.initial.level, self.initial.area):
            self.displacement = max(
                self.displacement, math.dist(self.initial.position, observation.position)
            )
        self.height = max(self.height, y)
        self.health = min(self.health, observation.health)
        if observation.stars is not None:
            self.stars = max(self.stars or 0, observation.stars)
        if observation.coins is not None:
            self.coins = max(self.coins or 0, observation.coins)
        if observation.level is not None:
            self.levels.add(observation.level)
        self.previous = observation

    def to_dict(self) -> dict:
        return {
            "deaths": self.deaths,
            "minimum_health": self.health,
            "path_distance": self.distance,
            "max_displacement": self.displacement,
            "max_height": self.height,
            "visited_xz_cells_400": len(self.visited),
            "stars_gained": None if self.stars is None else self.stars - (self.initial.stars or 0),
            "peak_coins": self.coins,
            "levels_visited": sorted(self.levels),
            "game_beaten": None,
        }
