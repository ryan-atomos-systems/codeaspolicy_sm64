"""Compare every action and observation in two completed native suites."""

import argparse
import json
import sys
from itertools import zip_longest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sm64_policy.api import Observation
from sm64_policy.state import record_from_dict
from sm64_policy.storage import OBSERVATION_HASH, observation_hash


def read(path: Path):
    return json.loads(path.read_text())


def state_hash(record, mode, config):
    if mode == "compact":
        if record.get("n_frames") != config["frame_skip"]:
            raise ValueError("Compact action duration differs from configuration")
        return record.get("observation_sha256")
    observation = dict(record["observation"])
    if config.get("observation_mode", "basic") == "basic":
        # Historical flat traces carry frame timing on the enclosing row.
        observation.update(frame=record["frame"], last_action_frames=config["frame_skip"])
    return observation_hash(record_from_dict(Observation, observation))


def compare(reference: Path, candidate: Path) -> tuple[int, int]:
    left, right = (read(path / "summary.json") for path in (reference, candidate))
    for summary in (left, right):
        if summary["backend"] != "native" or summary["status"] != "ok":
            raise ValueError("Both suites must be successful native runs")
    for field in ("policies", "seeds", "steps", "frame_skip"):
        if left[field] != right[field]:
            raise ValueError(f"Incompatible suite field: {field}")
    if left.get("observation_mode", "basic") != right.get("observation_mode", "basic"):
        raise ValueError("Incompatible suite observation modes")
    sessions = sorted(reference.glob("session-*/trace.jsonl"))
    if not sessions or len(sessions) != len(list(candidate.glob("session-*/trace.jsonl"))):
        raise ValueError("Suite session counts differ or traces are missing")
    decisions = 0
    for trace in sessions:
        other = candidate / trace.parent.name / trace.name
        for directory in (trace.parent, other.parent):
            if read(directory / "result.json")["status"] != "ok":
                raise ValueError(f"Incomplete session: {directory}")
        config_a, config_b = (
            read(directory / "config.json") for directory in (trace.parent, other.parent)
        )
        for field in ("policy", "seed", "steps", "frame_skip"):
            if config_a[field] != config_b[field]:
                raise ValueError(f"Session configurations differ: {trace.parent.name}: {field}")
        metadata = [directory / "rollout.json" for directory in (trace.parent, other.parent)]
        if all(path.exists() for path in metadata) and read(metadata[0]).get(
            "initial_observation"
        ) != read(metadata[1]).get("initial_observation"):
            raise ValueError(f"Initial observations differ: {trace.parent.name}")
        modes = [config_a.get("trace_mode", "full"), config_b.get("trace_mode", "full")]
        if "compact" in modes:
            for path, mode in zip(metadata, modes):
                if (
                    read(path).get("observation_hash_algorithm") != OBSERVATION_HASH
                ) and mode == "compact":
                    raise ValueError("Unsupported observation hash algorithm")
        count = 0
        with trace.open() as a, other.open() as b:
            for index, (line_a, line_b) in enumerate(zip_longest(a, b)):
                if line_a is None or line_b is None:
                    raise ValueError(
                        f"Trace length mismatch: {trace.parent.name}, decision {index}"
                    )
                records = [json.loads(line_a), json.loads(line_b)]
                if any(
                    records[0].get(key) != records[1].get(key)
                    for key in ("step", "frame", "action")
                ):
                    raise ValueError(
                        f"Action/frame mismatch: {trace.parent.name}, decision {index}"
                    )
                if "compact" in modes:
                    hashes = [
                        state_hash(record, mode, config)
                        for record, mode, config in zip(records, modes, (config_a, config_b))
                    ]
                    matched = hashes[0] is not None and hashes[0] == hashes[1]
                else:
                    matched = records[0]["observation"] == records[1]["observation"]
                if not matched:
                    raise ValueError(f"State mismatch: {trace.parent.name}, decision {index}")
                count += 1
        for directory in (trace.parent, other.parent):
            if count != read(directory / "result.json")["steps"]:
                raise ValueError(f"Truncated trace: {directory}")
        decisions += count
    return len(sessions), decisions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    try:
        sessions, decisions = compare(args.reference, args.candidate)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Comparison failed: {exc}\n")
    print(f"Matched {sessions} native sessions, {decisions:,} decisions (actions + observations).")


if __name__ == "__main__":
    main()
