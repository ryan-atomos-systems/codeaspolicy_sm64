"""Compact traces retain controller timing and detect rich-state divergence."""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from test_oracle_state import FakeLibrary

from scripts.compare_rollouts import compare
from sm64_policy import Action, Observation
from sm64_policy.dashboard.server import ArtifactStore
from sm64_policy.native_state import OracleReader
from sm64_policy.storage import OBSERVATION_HASH, TraceWriter, observation_hash, write_json


class TraceModeTests(unittest.TestCase):
    def test_full_and_compact_compare_early_stops_and_reject_state_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reader = OracleReader(FakeLibrary())
            reader.buffer.version = 1
            initial = Observation(
                (0, 0, 0), (0, 0, 0), 8, **reader.read((0, 0, 0), (0, 0, 0), 128, 72)
            )
            for mode in ("full", "compact"):
                run = root / mode
                session = run / "session-000"
                session.mkdir(parents=True)
                config = {
                    "policy": "test",
                    "seed": 0,
                    "steps": 100,
                    "frame_skip": 1,
                    "observation_mode": "oracle",
                    "trace_mode": mode,
                    "record_every": 0,
                }
                write_json(session / "config.json", config)
                write_json(session / "result.json", {"status": "ok", "steps": 2})
                write_json(
                    run / "summary.json",
                    {
                        "backend": "native",
                        "status": "ok",
                        "policies": ["test"],
                        "seeds": [0],
                        "steps": 100,
                        "frame_skip": 1,
                        "observation_mode": "oracle",
                    },
                )
                write_json(
                    session / "rollout.json",
                    {
                        "initial_observation": initial.to_dict(),
                        "frames": [],
                        "observation_hash_algorithm": OBSERVATION_HASH,
                    },
                )
                with TraceWriter(session / "trace.jsonl", mode) as trace:
                    for frame in (1, 2):
                        state = replace(initial, frame=frame, last_action_frames=1)
                        trace.append(
                            frame - 1,
                            frame,
                            Action(a=frame == 1),
                            state,
                            {"extra": mode} if mode == "full" else None,
                        )
            self.assertEqual(compare(root / "full", root / "compact"), (1, 2))
            store = ArtifactStore(root)
            rollout = store.rollout("compact", "session-000")
            self.assertEqual(len(rollout["records"]), 2)
            self.assertNotIn("mario", rollout["records"][0]["observation"])
            self.assertNotIn("policy", rollout["records"][0])
            path = root / "compact/session-000/trace.jsonl"
            lines = [json.loads(line) for line in path.read_text().splitlines()]
            changed = replace(
                initial, progress=replace(initial.progress, coins=99), frame=2, last_action_frames=1
            )
            lines[1]["observation_sha256"] = observation_hash(changed)
            path.write_text("".join(json.dumps(line) + "\n" for line in lines))
            with self.assertRaisesRegex(ValueError, "State mismatch"):
                compare(root / "full", root / "compact")
