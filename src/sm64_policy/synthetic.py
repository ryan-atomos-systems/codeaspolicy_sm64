"""Deterministic harness fixture; not an SM64 simulator."""

from .api import Action, Observation


class Synthetic:
    """Tiny deterministic kinematic fixture; never evidence of SM64 capability."""

    def __init__(self, *, frame_skip: int, **kwargs):
        self.frame_skip = frame_skip
        self.position = (0.0, 0.0, 0.0)
        self.velocity = (0.0, 0.0, 0.0)

    def observe(self):
        return Observation(self.position, self.velocity, 8)

    def step(self, action: Action, *, capture: bool = False):
        self.velocity = (action.stick_x * 0.5, 0.0, action.stick_y * 0.5)
        self.position = tuple(p + v * self.frame_skip for p, v in zip(self.position, self.velocity))
        return self.observe()

    def pixels(self):
        return None

    def close(self):
        pass
