"""Reusable feedback skills for the fork's Mario-relative controller.

Controllers are evaluated every physics frame. Air control inverts the normal
jump dynamics in mario_actions_airborne.c; it is not valid for flying/swimming.
Only controller inputs are produced here. No engine state is modified.
"""

import math
from dataclasses import replace

from .api import Action, Observation
from .decision_trace import record_control, record_gate
from .state import ObjectState


def horizontal_distance(state: Observation, target: tuple[float, float]) -> float:
    return math.hypot(target[0] - state.position[0], target[1] - state.position[2])


def steer(
    state: Observation,
    target: tuple[float, float],
    magnitude: int = 64,
    *,
    ensure_turn: bool = False,
) -> Action:
    """Face and walk toward an XZ target; caller handles stopping and obstacles.

    Use ensure_turn for slow heading-alignment gates: nonzero lateral commands
    must survive the native raw-stick dead zone. Ordinary walking retains its
    existing response, including small inputs that the engine ignores.
    """
    if state.mario is None:
        raise ValueError("Feedback control requires an oracle Mario state")
    dx, dz = target[0] - state.position[0], target[1] - state.position[2]
    yaw = state.mario.face_angle[1] * math.tau / 65536
    error = (math.atan2(dx, dz) - yaw + math.pi) % math.tau - math.pi
    stick_x = round(-magnitude * math.sin(error))
    # Alignment gates must keep turning until their angular tolerance is met.
    # adjust_analog_stick ignores raw axes in [-7, 7], so a slow diagonal
    # command can otherwise walk straight forever just outside that tolerance.
    if ensure_turn and 0 < abs(stick_x) < 8:
        stick_x = 8 if stick_x > 0 else -8
    action = Action(stick_x, round(magnitude * math.cos(error)))
    record_control(
        "steer",
        target_xz=target,
        distance=math.hypot(dx, dz),
        heading_error_degrees=math.degrees(error),
        magnitude=magnitude,
        ensure_turn=ensure_turn,
        action=action.to_dict(),
    )
    return action


def air_steer(state: Observation, target: tuple[float, float], max_speed: float = 18) -> Action:
    """Position/velocity feedback for ordinary jumps, with A held for height.

    Mario's facing is fixed during an ordinary jump. Forward speed integrates
    acceleration, while sideways input directly sets lateral speed. Invert
    those two dynamics, then compensate for quadratic stick magnitude and the
    six-unit controller dead zone. Limits keep the controller in the ordinary
    jump regime. This is a small model-based controller, not learned weights.
    """
    if state.mario is None:
        raise ValueError("Air control requires an oracle Mario state")
    yaw = state.mario.face_angle[1] * math.tau / 65536
    dx, dz = target[0] - state.position[0], target[1] - state.position[2]
    along = dx * math.sin(yaw) + dz * math.cos(yaw)
    side = dx * math.cos(yaw) - dz * math.sin(yaw)
    wanted_speed = max(-12, min(max_speed, along * 0.18))
    acceleration = max(-1, min(1, (wanted_speed - state.mario.forward_velocity + 0.35) / 1.5))
    lateral = max(-1, min(1, side * 0.15 / 10))
    norm = math.hypot(acceleration, lateral)
    magnitude = 64 * math.sqrt(min(1, norm))

    def raw(value):
        return round(value + math.copysign(6, value)) if abs(value) > 1 else 0

    action = (
        Action(a=True)
        if norm < 0.02
        else Action(raw(-magnitude * lateral / norm), raw(magnitude * acceleration / norm), a=True)
    )
    record_control(
        "air_steer",
        target_xz=target,
        along_error=along,
        side_error=side,
        desired_forward_speed=wanted_speed,
        forward_speed=state.mario.forward_velocity,
        acceleration_command=acceleration,
        lateral_command=lateral,
        max_speed=max_speed,
        action=action.to_dict(),
    )
    return action


class GroundPoundObject:
    """Jump above an object's center, cancel lateral motion with Z, and land.

    Object position and collision-top offset are supplied by the task. Repeated
    attempts are bounded by the parent task's timeout. A is released on landing
    before the next jump; elapsed time uses physics frames, not decision count.
    """

    def __init__(self, top_offset: float):
        self.top_offset = top_offset
        self.last_jump = -100

    def act(self, state: Observation, target: ObjectState) -> Action:
        point = target.position[0], target.position[2]
        distance = horizontal_distance(state, point)
        record_gate(
            "Ground-pound window",
            {
                "airborne": state.mario.airborne,
                "horizontal error < 32": distance < 32,
                "feet above post top + 5": state.position[1]
                > target.position[1] + self.top_offset + 5,
            },
            object_id=target.id,
            target_position=target.position,
            horizontal_error=distance,
            height_above_top=state.position[1] - target.position[1] - self.top_offset,
        )
        if state.mario.airborne:
            if distance < 32 and state.position[1] > target.position[1] + self.top_offset + 5:
                return Action(z=True)
            return air_steer(state, point)
        if state.frame - self.last_jump > 40:
            self.last_jump = state.frame
            action = steer(state, point, 32) if distance > 25 else Action()
            return replace(action, a=True)
        return steer(state, point, 40) if distance > 100 else Action()


def query_covers(state: Observation, position: tuple[float, float, float]) -> bool:
    """Whether absence at a known location is meaningful in a bounded query."""
    if state.objects is None:
        return False
    distance = math.dist(state.position, position)
    cutoff = state.objects.radius
    if state.objects.truncated:
        cutoff = min(cutoff, max((o.distance for o in state.objects.items), default=0))
    return distance + 100 < cutoff
