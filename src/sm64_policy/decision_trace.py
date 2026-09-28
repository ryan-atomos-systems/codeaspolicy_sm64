"""Optional, observation-only controller diagnostics scoped to one policy decision.

The dashboard reads these records; it never re-executes policy code. A control
call is an evaluated intermediate result, not necessarily the final action.
"""

import sys
from contextlib import contextmanager
from contextvars import ContextVar

_active = ContextVar("sm64_decision_trace", default=None)


def record_control(controller: str, **values) -> None:
    trace = _active.get()
    if trace is None:
        return
    caller = sys._getframe(2)
    source = caller.f_code.co_filename.replace("\\", "/").split("/sm64_policy/")[-1]
    trace["controls"].append(
        {"controller": controller, "source": f"{source}:{caller.f_lineno}", **values}
    )


def record_gate(name: str, conditions: dict, **values) -> None:
    trace = _active.get()
    if trace is not None:
        trace["gates"].append({"name": name, "conditions": conditions, **values})


def record_route(points, index: int) -> None:
    trace = _active.get()
    if trace is not None:
        trace["route"] = {"points_xz": [point[:2] for point in points], "index": index}


@contextmanager
def capture_decision(input_frame: int):
    trace = {"version": 1, "input_frame": input_frame, "controls": [], "gates": []}
    token = _active.set(trace)
    try:
        yield trace
    finally:
        _active.reset(token)
