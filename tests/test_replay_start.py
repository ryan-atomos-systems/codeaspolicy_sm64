"""Start must survive compact trace encoding and verified replay decoding."""

import json
import tempfile
import unittest
from pathlib import Path

from sm64_policy import Action, Observation
from sm64_policy.storage import TraceWriter


class ReplayStartTests(unittest.TestCase):
    def test_compact_trace_preserves_start_with_other_buttons(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            with TraceWriter(path, "compact") as trace:
                trace.append(
                    0,
                    1,
                    Action(a=True, z=True, start=True),
                    Observation((0, 0, 0), (0, 0, 0), 8, frame=1),
                )
                self.assertEqual(trace.actions, [(0, 0, 13, 1)])
            self.assertTrue(json.loads(path.read_text())["action"]["start"])
