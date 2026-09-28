"""Seed pairing and verified action replay contracts."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from sm64_policy import CheckpointMismatch, SM64Env
from sm64_policy.config import EpisodeConfig, SuiteConfig
from sm64_policy.paths import DEFAULT_LIBRARY


class SeedTests(unittest.TestCase):
    def test_validation(self):
        for seed in (-1, 2**32, True, 1.5):
            with self.assertRaises(ValueError):
                SM64Env(game_seed=seed)
        with self.assertRaises(ValueError):
            SuiteConfig(Path("unused"), DEFAULT_LIBRARY, seeds=(1, 2), game_seeds=(3,))

    @unittest.skipUnless(os.environ.get("SM64_NATIVE_TESTS") == "1", "requires native engine")
    def test_seeded_replay_with_render_and_drift_rejection(self):
        from sm64_policy.episode import run_episode
        from sm64_policy.replay import replay

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("a", "b"):
                run_episode(
                    EpisodeConfig(
                        str(root / name),
                        str(DEFAULT_LIBRARY),
                        policy="random",
                        seed=7,
                        game_seed=123,
                        steps=120,
                        frame_skip=1,
                        trace_mode="compact",
                    )
                )
            a = json.loads((root / "a/replay.json").read_text())
            b = json.loads((root / "b/replay.json").read_text())
            self.assertEqual(a, b)
            result = replay(root / "a/replay.json", output=root / "frames", record_every=20)
            self.assertTrue(result["verified"])
            self.assertEqual(result["recorded_frames"], 7)
            a["observation_history_sha256"] = "0" * 64
            (root / "bad.json").write_text(json.dumps(a))
            with self.assertRaises(CheckpointMismatch):
                replay(root / "bad.json")
            with SM64Env(game_seed=123) as env:
                env.reset()
                checkpoint = env.save_state()
                checkpoint["game_seed"] = 456
                with self.assertRaises(CheckpointMismatch):
                    env.load_state(checkpoint)

    @unittest.skipUnless(os.environ.get("SM64_NATIVE_TESTS") == "1", "requires native engine")
    def test_policy_error_retains_partial_action_replay(self):
        from unittest.mock import patch

        from sm64_policy import Action
        from sm64_policy.episode import run_episode
        from sm64_policy.replay import replay

        class FailingPolicy:
            def act(self, observation, step):
                if step == 3:
                    raise RuntimeError("intentional policy failure")
                return Action(stick_y=64)

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "episode"
            with (
                patch("sm64_policy.episode.load_policy", return_value=FailingPolicy()),
                self.assertRaisesRegex(RuntimeError, "intentional"),
            ):
                run_episode(
                    EpisodeConfig(
                        str(path),
                        str(DEFAULT_LIBRARY),
                        game_seed=123,
                        steps=10,
                        trace_mode="compact",
                    )
                )
            result = replay(path / "replay.json")
            self.assertTrue(result["verified"])
            self.assertEqual(result["decisions"], 3)
