"""Small policy contract: observations in, bounded controller actions out."""

from dataclasses import dataclass
from typing import Protocol

from .state import (
    CameraState,
    GeometryState,
    MarioState,
    NearbyObjects,
    ProgressState,
    StateRecord,
    UIState,
)


@dataclass(frozen=True, slots=True)
class Action:
    stick_x: int = 0
    stick_y: int = 0
    a: bool = False
    b: bool = False
    z: bool = False
    start: bool = False

    def __post_init__(self):
        for value in (self.stick_x, self.stick_y):
            if type(value) is not int or not -80 <= value <= 80:
                raise ValueError("Stick values must be integers in [-80, 80]")
        if any(type(v) is not bool for v in (self.a, self.b, self.z, self.start)):
            raise ValueError("Buttons must be booleans")

    def to_dict(self) -> dict:
        return {
            "stick_x": self.stick_x,
            "stick_y": self.stick_y,
            "a": self.a,
            "b": self.b,
            "z": self.z,
            "start": self.start,
        }


@dataclass(frozen=True, slots=True)
class Observation(StateRecord):
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    health: int
    died: bool = False
    height_above_ground: float = 0.0
    stars: int | None = None
    coins: int | None = None
    level: int | None = None
    area: int | None = None
    act: int | None = None
    mario_action: int | None = None
    frame: int = 0
    last_action_frames: int = 0
    engine_frame: int | None = None
    mario: MarioState | None = None
    camera: CameraState | None = None
    geometry: GeometryState | None = None
    objects: NearbyObjects | None = None
    progress: ProgressState | None = None
    ui: UIState | None = None

    def to_dict(self, *, summary: bool = False) -> dict:
        result = {
            "position": self.position,
            "velocity": self.velocity,
            "health": self.health,
            "died": self.died,
            "height_above_ground": self.height_above_ground,
            "stars": self.stars,
            "coins": self.coins,
            "level": self.level,
            "area": self.area,
            "act": self.act,
            "mario_action": self.mario_action,
        }
        if self.mario is not None and not summary:
            result.update(
                schema_version=3,
                frame=self.frame,
                last_action_frames=self.last_action_frames,
                engine_frame=self.engine_frame,
            )
            for key in ("mario", "camera", "geometry", "objects", "progress"):
                item = getattr(self, key)
                result[key] = item.to_dict() if item is not None else None
            if self.ui is not None:
                result["ui"] = self.ui.to_dict()
        return result


class Policy(Protocol):
    def act(self, observation: Observation, step: int) -> Action: ...
