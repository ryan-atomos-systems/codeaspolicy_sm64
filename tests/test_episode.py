"""A failed policy must still leave its earlier trajectory available for diagnosis."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

from sm64_policy.api import Action
from sm64_policy.config import EpisodeConfig
from sm64_policy.dashboard.server import ArtifactStore
from sm64_policy.episode import run_episode


class EpisodeTests(unittest.TestCase):
    def test_policy_exception_preserves_rollout_metadata_and_trace(self):
        class FailingPolicy:
            events: ClassVar[list] = [{"frame": 1, "kind": "probe", "label": "Reached probe"}]

            def act(self, observation, step):
                if step == 2:
                    raise RuntimeError("policy failed")
                return Action()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run" / "session-000"
            folder.mkdir(parents=True)
            config = EpisodeConfig(str(folder), "unused", backend="synthetic", frame_skip=1)
            (folder / "config.json").write_text(json.dumps(config.to_dict()))
            with (
                patch("sm64_policy.episode.load_policy", return_value=FailingPolicy()),
                self.assertRaisesRegex(RuntimeError, "policy failed"),
            ):
                run_episode(config)
            rollout = ArtifactStore(root).rollout("run", "session-000")
            self.assertEqual(len(rollout["records"]), 2)
            self.assertEqual(rollout["events"], FailingPolicy.events)
            self.assertIsNotNone(rollout["initial_observation"])
