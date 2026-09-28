import ctypes
import json
import tempfile
import unittest
from pathlib import Path

from sm64_policy.api import Action, Observation
from sm64_policy.config import EpisodeConfig, SuiteConfig
from sm64_policy.native_abi import GameState
from sm64_policy.policies import Explore, Random
from sm64_policy.suite import WorkerPool, run_suite


class CrashPolicy:
    def __init__(self, seed):
        pass

    def act(self, observation, step):
        raise RuntimeError("intentional policy failure")


class SlowPolicy(CrashPolicy):
    def act(self, observation, step):
        import time

        time.sleep(10)
        return Action()


class PolicyTests(unittest.TestCase):
    def test_controller_bounds(self):
        for invalid in (-81, 81, 1.5, True):
            with self.assertRaises(ValueError):
                Action(stick_x=invalid)
        with self.assertRaises(ValueError):
            Action(a=1)

    def test_native_pixel_dimensions_match_c_order(self):
        self.assertEqual(GameState.width.offset, ctypes.sizeof(ctypes.c_void_p))
        self.assertEqual(GameState.height.offset, GameState.width.offset + 4)

    def test_stalled_explorer_turns_and_releases_jump(self):
        policy = Explore(seed=0)
        observation = Observation((0, 0, 0), (0, 0, 0), 8)
        actions = [policy.act(observation, i) for i in range(30)]
        self.assertTrue(any(action.stick_x for action in actions))
        self.assertTrue(any(action.a for action in actions))
        self.assertTrue(any(not action.a for action in actions))

    def test_seeded_policy_replay(self):
        observation = Observation((0, 0, 0), (0, 0, 0), 8)
        first, second = Random(seed=7), Random(seed=7)
        self.assertEqual(
            [first.act(observation, i) for i in range(100)],
            [second.act(observation, i) for i in range(100)],
        )

    def test_parallel_sessions_are_isolated_and_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            runs = []
            for name in ("first", "second"):
                args = SuiteConfig(
                    output=Path(directory) / name,
                    library=Path("/unused"),
                    backend="synthetic",
                    workers=3,
                    steps=1000,
                    frame_skip=4,
                    policies=["noop", "random", "explore"],
                    seeds=[0, 1],
                    timeout=15,
                )
                self.assertEqual(run_suite(args)["status"], "ok")
                runs.append(json.loads((Path(args.output) / "summary.json").read_text()))
            first, second = runs
            self.assertEqual(first["total_sessions"], 6)
            self.assertEqual(len({r["pid"] for r in first["sessions"]}), 6)
            self.assertEqual(len({r["port"] for r in first["sessions"]}), 6)
            self.assertEqual(
                [r["trace_sha256"] for r in first["sessions"]],
                [r["trace_sha256"] for r in second["sessions"]],
            )
            self.assertTrue(all(r["game_beaten"] is None for r in first["sessions"]))

    def test_worker_failure_and_timeout_leave_results(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, expected in (("CrashPolicy", "error"), ("SlowPolicy", "timeout")):
                session = Path(directory) / name
                session.mkdir()
                result = WorkerPool().run(
                    EpisodeConfig(
                        session_dir=str(session),
                        backend="synthetic",
                        policy=f"tests.test_policy_harness:{name}",
                        seed=0,
                        steps=1,
                        frame_skip=4,
                        library="/unused",
                        port=12345,
                    ),
                    1,
                )
                self.assertEqual(result["status"], expected)
                self.assertTrue((session / "result.json").is_file())


if __name__ == "__main__":
    unittest.main()
