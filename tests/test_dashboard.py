"""Oracle paging keeps decision inputs causal and never returns the whole rich trace."""

import json
import tempfile
import unittest
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

from sm64_policy.dashboard.server import ArtifactStore, create_server
from sm64_policy.dashboard.traces import TraceCache


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = self.root / "run" / "session-000"
        self.session.mkdir(parents=True)
        self.initial = self.observation(0)
        (self.session / "rollout.json").write_text(
            json.dumps({"initial_observation": self.initial})
        )
        (self.session / "config.json").write_text("{}")
        self.records = [
            {
                "step": i,
                "frame": (i + 1) * 4,
                "action": {"a": True},
                "observation": self.observation((i + 1) * 4),
                "policy": {"phase": "étoile"},
            }
            for i in range(5)
        ]
        self.trace = self.session / "trace.jsonl"
        self.trace.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in self.records)
        )

    @staticmethod
    def observation(frame):
        return {
            "frame": frame,
            "position": [frame, 0, 1],
            "health": 8,
            "level": 9,
            "area": 1,
            "mario": {"airborne": False, "face_angle": [0, 1, 0]},
            "objects": {"items": [{"id": frame}]},
            "geometry": {"rays": []},
            "camera": {},
        }

    def test_page_includes_previous_input_without_off_by_one(self):
        store = ArtifactStore(self.root)
        page = store.states("run", "session-000", 3, 2)
        self.assertEqual(page["start"], 2)
        self.assertEqual([o["frame"] for o in page["observations"]], [8, 12, 16])
        self.assertIn("mario", page["observations"][0])
        self.assertEqual(store.states("run", "session-000", 0, 1)["observations"], [self.initial])
        compact = store.rollout("run", "session-000")
        self.assertNotIn("mario", compact["records"][0]["observation"])
        self.assertEqual(compact["records"][0]["policy"]["phase"], "étoile")
        self.assertEqual(store.states("run", "session-000", 5, 48)["total"], 6)
        for start, count in [(-1, 1), (6, 1), (0, 49), (0, 0)]:
            with self.assertRaises(ValueError):
                store.states("run", "session-000", start, count)

    def test_partial_tail_refresh_and_bounded_cache(self):
        cache = TraceCache(capacity=1)
        original = cache.get(self.trace)
        self.assertIs(original, cache.get(self.trace))
        last = json.dumps(self.records[0])
        with self.trace.open("a") as f:
            f.write(last[:10])
        self.assertEqual(len(cache.get(self.trace).records), 5)
        with self.trace.open("a") as f:
            f.write(last[10:] + "\n")
        self.assertEqual(len(cache.get(self.trace).records), 6)
        second = self.session / "second.jsonl"
        second.write_text(last + "\n")
        cache.get(second)
        self.assertEqual(list(cache.entries), [second])

    def test_legacy_frames_come_from_trace_and_missing_initial_is_unknown(self):
        record = self.records[0]
        del record["observation"]["frame"]
        self.trace.write_text(json.dumps(record) + "\n")
        (self.session / "rollout.json").unlink()
        page = ArtifactStore(self.root).states("run", "session-000", 1, 1)
        self.assertIsNone(page["observations"][0])
        self.assertEqual(page["observations"][1]["frame"], 4)

    def test_http_pages_and_path_boundaries(self):
        server = create_server(self.root, 0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(
                base + "/api/states?run=run&session=session-000&start=1&count=1"
            ) as response:
                self.assertEqual([o["frame"] for o in json.load(response)["observations"]], [0, 4])
            for path, code in [
                ("/api/states?run=..&session=session-000&start=0", 400),
                ("/api/states?run=run&session=session-000&start=-1", 400),
                ("/vendor/../../server.py", 404),
                ("/vendor/README.md", 404),
            ]:
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + path)
                self.assertEqual(error.exception.code, code)
            with urlopen(base + "/vendor/three.module.min.js") as response:
                self.assertEqual(response.headers["Content-Type"], "text/javascript")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
