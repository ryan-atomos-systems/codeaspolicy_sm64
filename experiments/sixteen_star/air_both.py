"""Development skill retained from air_both.py; see README.md for evidence and limits."""

import math
from sm64_policy import Action, Observation
from sm64_policy.decision_trace import record_control

def air_steer(state: Observation, target: tuple[float, float], max_speed: float=18) -> Action:
    """Position/velocity feedback for ordinary jumps, with A held for height.

    Mario's facing is fixed during an ordinary jump. Forward speed integrates
    acceleration, while sideways input directly sets lateral speed. Invert
    those two dynamics, then compensate for quadratic stick magnitude and the
    six-unit controller dead zone. Limits keep the controller in the ordinary
    jump regime. This is a small model-based controller, not learned weights.
    """
    if state.mario is None:
        raise ValueError('Air control requires an oracle Mario state')
    yaw = state.mario.face_angle[1] * math.tau / 65536
    dx, dz = (target[0] - state.position[0], target[1] - state.position[2])
    along = dx * math.sin(yaw) + dz * math.cos(yaw)
    side = dx * math.cos(yaw) - dz * math.sin(yaw)
    wanted_speed = max(-max_speed, min(max_speed, along * 0.18))
    acceleration = max(-1, min(1, (wanted_speed - state.mario.forward_velocity + 0.35) / 1.5))
    lateral = max(-1, min(1, side * 0.15 / 10))
    norm = math.hypot(acceleration, lateral)
    magnitude = 64 * math.sqrt(min(1, norm))

    def raw(value):
        return round(value + math.copysign(6, value)) if abs(value) > 1 else 0
    action = Action(a=True) if norm < 0.02 else Action(raw(-magnitude * lateral / norm), raw(magnitude * acceleration / norm), a=True)
    record_control('air_steer', target_xz=target, along_error=along, side_error=side, desired_forward_speed=wanted_speed, forward_speed=state.mario.forward_velocity, acceleration_command=acceleration, lateral_command=lateral, max_speed=max_speed, action=action.to_dict())
    return action
