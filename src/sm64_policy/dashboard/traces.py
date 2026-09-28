"""Bounded telemetry cache and byte offsets for read-only oracle paging.

Never load the complete rich trace into memory. Index a session once, retain its
small telemetry projection, and seek directly to bounded batches of observations.
"""

import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

RICH_FIELDS = {"mario", "camera", "geometry", "objects", "ui"}


@dataclass
class IndexedTrace:
    fingerprint: tuple
    offsets: list[int]
    records: list[dict]


class TraceCache:
    def __init__(self, capacity: int = 2):
        self.capacity = capacity
        self.entries = OrderedDict()
        self.lock = RLock()

    def get(self, path: Path) -> IndexedTrace:
        stat = path.stat()
        fingerprint = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
        with self.lock:
            cached = self.entries.get(path)
            if cached and cached.fingerprint == fingerprint:
                self.entries.move_to_end(path)
                return cached
            offsets, records = [], []
            with path.open("rb") as trace:
                while True:
                    offset = trace.tell()
                    line = trace.readline()
                    if not line or not line.endswith(b"\n"):
                        break
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        break
                    observation = record["observation"]
                    mario = observation.get("mario") or {}
                    record["signals"] = {
                        key: mario.get(key) for key in ("airborne", "held_object_id", "platform_id")
                    }
                    record["observation"] = {
                        key: value for key, value in observation.items() if key not in RICH_FIELDS
                    }
                    offsets.append(offset)
                    records.append(record)
            cached = IndexedTrace(fingerprint, offsets, records)
            self.entries[path] = cached
            self.entries.move_to_end(path)
            while len(self.entries) > self.capacity:
                self.entries.popitem(last=False)
            return cached

    def observations(self, path: Path, initial: dict | None, start: int, count: int) -> dict:
        if start < 0 or not 1 <= count <= 48:
            raise ValueError("Invalid observation page")
        index = self.get(path)
        total = len(index.offsets) + 1
        if start >= total:
            raise ValueError("Observation index outside the trace")
        first = max(0, start - 1)  # Include the causal input to the first decision.
        observations = []
        with path.open("rb") as trace:
            for number in range(first, min(start + count, total)):
                if number == 0:
                    observations.append({"frame": 0, **initial} if initial is not None else None)
                else:
                    trace.seek(index.offsets[number - 1])
                    record = json.loads(trace.readline())
                    observations.append({"frame": record["frame"], **record["observation"]})
        return {"start": first, "observations": observations, "total": total}


def debug_events(records: list[dict], initial: dict | None) -> list[dict]:
    events = []
    previous = initial
    previous_signals = {}
    previous_phase = None
    for record in records:
        observation, signals = record["observation"], record["signals"]
        policy = record.get("policy") or {}
        phase = " / ".join(str(policy[key]) for key in ("phase", "skill") if policy.get(key))
        if phase and phase != previous_phase:
            events.append({"frame": record["frame"], "kind": "skill", "label": phase})
            previous_phase = phase
        if previous and (observation.get("level"), observation.get("area")) == (
            previous.get("level"),
            previous.get("area"),
        ):
            if observation["health"] < previous["health"]:
                events.append(
                    {
                        "frame": record["frame"],
                        "kind": "damage",
                        "label": f"Health {previous['health']} → {observation['health']}",
                    }
                )
            if signals.get("held_object_id") != previous_signals.get("held_object_id"):
                events.append(
                    {
                        "frame": record["frame"],
                        "kind": "interaction",
                        "label": "Grab object"
                        if signals.get("held_object_id")
                        else "Release object",
                    }
                )
            if signals.get("airborne") is False and previous_signals.get("airborne") is True:
                events.append(
                    {"frame": record["frame"], "kind": "landing", "label": "Airborne action ended"}
                )
        previous, previous_signals = observation, signals
    return events
