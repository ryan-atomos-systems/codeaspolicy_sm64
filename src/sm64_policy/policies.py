"""Executable baselines. Custom policies use module:Class and accept seed=."""

import importlib
import math
import random

from .api import Action, Observation
from .campaign.policy import FirstBowser
from .first_star import FirstStar


class Noop:
    def __init__(self, seed: int):
        pass

    def act(self, observation: Observation, step: int) -> Action:
        return Action()


class Random:
    """Hold a random input for eight decisions to avoid framewise jitter."""

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.action = Action()

    def act(self, observation: Observation, step: int) -> Action:
        if step % 8 == 0:
            angle = self.rng.uniform(-math.pi, math.pi)
            self.action = Action(
                round(64 * math.sin(angle)),
                round(64 * math.cos(angle)),
                a=self.rng.random() < 0.3,
                b=self.rng.random() < 0.1,
                z=self.rng.random() < 0.1,
            )
        return self.action


class Explore:
    """Walk, pulse jump, and turn when horizontal movement stalls.

    This is a capability baseline, not a star route or learned policy.
    This fork uses Mario-relative inputs; world coordinates do not set heading.
    """

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.last_position = None
        self.stalled = 0
        self.turn_until = -1
        self.turn = 0

    def act(self, observation: Observation, step: int) -> Action:
        x, _, z = observation.position
        if self.last_position is not None:
            distance = math.hypot(x - self.last_position[0], z - self.last_position[1])
            self.stalled = self.stalled + 1 if distance < 4 else 0
        self.last_position = (x, z)
        if observation.died or self.stalled >= 12:
            self.turn = self.rng.choice((-64, 64))
            self.turn_until = step + 18
            self.stalled = 0
        turn = self.turn if step < self.turn_until else 0
        return Action(turn, 40 if turn else 64, a=step % 16 < 3)


BUILTINS = {
    "noop": Noop,
    "random": Random,
    "explore": Explore,
    "first-star": FirstStar,
    "first-bowser": FirstBowser,
}


def load_policy(spec: str, seed: int):
    if spec in BUILTINS:
        return BUILTINS[spec](seed=seed)
    module, separator, name = spec.partition(":")
    if not separator or not module or not name:
        raise ValueError(f"Unknown policy {spec!r}; use {', '.join(BUILTINS)} or module:Class")
    return getattr(importlib.import_module(module), name)(seed=seed)
