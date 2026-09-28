"""Versioned JSON artifacts. Atomic metadata writes let readers observe active runs."""

import hashlib
import json
from pathlib import Path

from .state import StateRecord, _record_values

SCHEMA_VERSION = 3
OBSERVATION_HASH = "sm64-observation-positional-json-v1"


def observation_hash(observation) -> str:
    """Hash all observation fields without building a large tree of dictionaries.

    v1 fixes the dataclass field order in api.py/state.py. Increment the algorithm
    when changing that schema. JSON handles numbers/strings without identity-based
    memoization, so equal observations hash equally after IPC or JSON decoding.
    """

    def values(record):
        if not isinstance(record, StateRecord):
            raise TypeError(f"Not a state record: {type(record)}")
        return _record_values(type(record))(record)

    data = json.dumps(observation, default=values, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


class TraceWriter:
    def __init__(self, path: Path, mode: str = "full"):
        if mode not in {"full", "compact"}:
            raise ValueError("Trace mode must be full or compact")
        self.mode = mode
        self.previous_frame = 0
        self.actions = []
        self.observation_digest = hashlib.sha256()
        self.file = path.open("w", buffering=256 * 1024)
        self.digest = hashlib.sha256()

    def append(self, step: int, frame: int, action, observation, policy=None) -> None:
        record = {
            "step": step,
            "frame": frame,
            "action": action.to_dict(),
            "observation": observation.to_dict(summary=True)
            if self.mode == "compact"
            else observation.to_dict(),
        }
        if self.mode == "compact":
            record["observation_sha256"] = observation_hash(observation)
            record["n_frames"] = frame - self.previous_frame
            self.observation_digest.update(bytes.fromhex(record["observation_sha256"]))
            self.actions.append(
                (
                    action.stick_x,
                    action.stick_y,
                    int(action.a)
                    | (int(action.b) << 1)
                    | (int(action.z) << 2)
                    | (int(action.start) << 3),
                    record["n_frames"],
                )
            )
        self.previous_frame = frame
        if policy is not None:
            record["policy"] = policy  # Decision-input diagnostics, before this action.
        line = json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n"
        self.file.write(line)
        self.digest.update(line.encode())

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.file.close()
