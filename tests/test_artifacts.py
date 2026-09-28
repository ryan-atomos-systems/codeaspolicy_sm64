import json
import struct
import tempfile
import threading
import unittest
import zlib
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from sm64_policy.api import Observation
from sm64_policy.dashboard.server import ArtifactStore, create_server
from sm64_policy.metrics import EpisodeMetrics
from sm64_policy.recording import encode_png
from sm64_policy.storage import write_json


class ArtifactTests(unittest.TestCase):
    def test_png_row_order_and_dimensions(self):
        rgb = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255])
        png = encode_png(2, 2, rgb)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", png[16:24]), (2, 2))
        position = 8
        while position < len(png):
            length = struct.unpack(">I", png[position : position + 4])[0]
            if png[position + 4 : position + 8] == b"IDAT":
                raw = zlib.decompress(png[position + 8 : position + 8 + length])
                self.assertEqual(raw, b"\0" + rgb[:6] + b"\0" + rgb[6:])
            position += 12 + length

    def test_death_and_level_warps_do_not_inflate_distance(self):
        metrics = EpisodeMetrics(Observation((0, 0, 0), (0, 0, 0), 8, level=9, area=1))
        metrics.update(Observation((3, 0, 4), (0, 0, 0), 8, level=9, area=1))
        metrics.update(Observation((5000, 0, 5000), (0, 0, 0), 8, died=True, level=9, area=1))
        metrics.update(Observation((-5000, 0, -5000), (0, 0, 0), 8, level=24, area=1))
        self.assertEqual(metrics.to_dict()["path_distance"], 5)
        self.assertEqual(metrics.to_dict()["deaths"], 1)

    def test_dashboard_serves_runs_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "test-run"
            run.mkdir()
            write_json(
                run / "manifest.json",
                {"backend": "synthetic", "workers": 1, "policies": ["noop"], "steps": 10},
            )
            (root / "escape").symlink_to(root.parent, target_is_directory=True)
            store = ArtifactStore(root)
            with self.assertRaises(ValueError):
                store.path("..", "private")
            with self.assertRaises(ValueError):
                store.path("escape", "private")
            server = create_server(root, 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urlopen(base + "/api/runs") as response:
                    self.assertEqual(json.load(response)["runs"][0]["id"], "test-run")
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + "/api/sessions?run=..")
                self.assertEqual(error.exception.code, 400)
                error.exception.close()
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + "/engine/baserom.us.z64")
                self.assertEqual(error.exception.code, 404)
                error.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
