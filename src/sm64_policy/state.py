"""Typed oracle observations shared by policies, logs, and future state estimators.

Coordinates are world-space engine units (Y up). Angles are signed SM64 units:
65536 units per turn; yaw zero points along +Z. Missing values remain None.
"""

from dataclasses import MISSING, dataclass, fields
from functools import cache
from operator import attrgetter
from types import UnionType
from typing import Any, get_args, get_origin, get_type_hints

Vec3 = tuple[float, float, float]
Angles = tuple[int, int, int]


@cache
def _field_names(cls: type) -> tuple[str, ...]:
    return tuple(field.name for field in fields(cls))


def _value(value: Any) -> Any:
    if isinstance(value, StateRecord):
        return value.to_dict()
    # Schema tuples are homogeneous: numeric vectors/matrices or state records.
    # JSON already handles numeric tuples, including nested surface vertices.
    if isinstance(value, tuple) and value and isinstance(value[0], StateRecord):
        return tuple(item.to_dict() for item in value)
    return value


class StateRecord:
    __slots__ = ()

    def __reduce__(self):
        # Frozen slot dataclasses otherwise unpickle via a Python field loop.
        # Their generated constructors restore the same immutable values faster.
        return type(self), _record_values(type(self))(self)

    def to_dict(self) -> dict:
        # Avoid asdict's deepcopy on thousands of small records per rollout.
        return {name: _value(getattr(self, name)) for name in _field_names(type(self))}


@cache
def _record_values(cls):
    names = _field_names(cls)
    getter = attrgetter(*names)
    return (lambda value: (getter(value),)) if len(names) == 1 else getter


@cache
def _record_types(cls):
    return get_type_hints(cls)


def record_from_dict(cls, data):
    """Restore our JSON observation schema for offline validation/export.

    Missing required fields raise; unknown additive metadata is ignored. Numeric
    sequences become tuples so restored records remain immutable.
    """

    def convert(kind, value):
        if value is None:
            return None
        origin, args = get_origin(kind), get_args(kind)
        if origin is UnionType:
            return convert(next(arg for arg in args if arg is not type(None)), value)
        if origin is tuple:
            return tuple(
                convert(args[0] if args[-1] is Ellipsis else args[i], item)
                for i, item in enumerate(value)
            )
        if isinstance(kind, type) and issubclass(kind, StateRecord):
            return record_from_dict(kind, value)
        return value

    kinds = _record_types(cls)
    values = {}
    for field in fields(cls):
        if field.name in data:
            values[field.name] = convert(kinds[field.name], data[field.name])
        elif field.default is MISSING and field.default_factory is MISSING:
            raise ValueError(f"Missing {cls.__name__}.{field.name}")
    return cls(**values)


@dataclass(frozen=True, slots=True)
class SurfaceState(StateRecord):
    surface_type: int
    flags: int
    room: int
    object_id: int | None
    normal: Vec3
    vertices: tuple[Vec3, Vec3, Vec3]


@dataclass(frozen=True, slots=True)
class UIState(StateRecord):
    dialog_id: int
    dialog_state: int
    dialog_response: int
    menu_mode: int
    transition_active: bool
    play_mode: int
    selected_act: int


@dataclass(frozen=True, slots=True)
class MarioState(StateRecord):
    position: Vec3
    velocity: Vec3
    face_angle: Angles
    angular_velocity: Angles
    forward_velocity: float
    action: int
    previous_action: int
    action_arg: int
    action_state: int
    action_timer: int
    flags: int
    input_flags: int
    health_raw: int
    lives: int
    room: int
    invincibility_timer: int
    cap_timer: int
    wall_kick_timer: int
    double_jump_timer: int
    frames_since_a: int
    frames_since_b: int
    airborne: bool
    swimming: bool
    on_pole: bool
    hanging: bool
    near_floor: bool  # Geometric proximity, not a definitive grounded/contact flag.
    floor_height: float | None
    ceiling_height: float | None
    water_level: float
    quicksand_depth: float
    floor: SurfaceState | None
    ceiling: SurfaceState | None
    wall: SurfaceState | None
    held_object_id: int | None
    ridden_object_id: int | None
    platform_id: int | None
    interacted_object_id: int | None


@dataclass(frozen=True, slots=True)
class CameraState(StateRecord):
    position: Vec3
    focus: Vec3
    roll: int
    control_yaw: int  # Engine control convention; not a world-space viewing yaw.
    mode: int
    cutscene: int
    fov_degrees: float  # Engine FOV before render-time overrides/shake.
    image_size: tuple[int, int]


@dataclass(frozen=True, slots=True)
class ObjectState(StateRecord):
    id: int  # Episode-local pool slot + allocation generation, never a pointer.
    behavior_id: int
    behavior_name: str | None
    behavior_params: int
    interaction_type: int
    interaction_subtype: int
    affordances: tuple[str, ...]
    active_flags: int
    action: int
    sub_action: int
    timer: int
    health: int
    damage_or_coin_value: int
    move_flags: int
    intangible_timer: int
    room: int
    face_angle: Angles
    position: Vec3
    relative_position: Vec3  # World-axis displacement from Mario.
    velocity: Vec3
    hitbox_radius: float
    hitbox_height: float
    hitbox_down_offset: float
    hurtbox_radius: float
    hurtbox_height: float
    distance: float


@dataclass(frozen=True, slots=True)
class NearbyObjects(StateRecord):
    radius: float
    capacity: int
    total_in_radius: int
    truncated: bool
    items: tuple[ObjectState, ...]


@dataclass(frozen=True, slots=True)
class RaySample(StateRecord):
    kind: str
    origin: Vec3
    direction: Vec3
    length: float
    hit_distance: float | None
    hit_position: Vec3 | None
    surface: SurfaceState | None


@dataclass(frozen=True, slots=True)
class GeometryState(StateRecord):
    rays: tuple[RaySample, ...]


@dataclass(frozen=True, slots=True)
class ProgressState(StateRecord):
    level: int
    area: int
    act: int
    course: int
    save_file: int
    stars: int
    coins: int
    lives: int
    save_flags: int
    collected_star_masks: tuple[int, ...]  # Index = course ID; 0 = castle secret stars.
    cannon_unlocked_mask: int  # Bit = course ID.
    last_completed_course: int
    last_completed_star: int
    credits_active: bool  # Diagnostic engine signal; not a completion detector.

    def has_star(self, course: int, star: int) -> bool:
        """Course ID 0..25; human-facing star number 1..7 (7 = 100 coins in main courses)."""
        if not 0 <= course < len(self.collected_star_masks) or not 1 <= star <= 7:
            raise ValueError("course must be in [0, 25] and star in [1, 7]")
        return bool(self.collected_star_masks[course] & (1 << (star - 1)))
