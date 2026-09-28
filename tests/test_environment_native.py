"""Opt-in integration tests: SM64_NATIVE_TESTS=1 make test."""

import copy
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

from sm64_policy import Action, CheckpointMismatch, Level, SM64Env, SM64VectorEnv, SpawnState


@unittest.skipUnless(os.environ.get("SM64_NATIVE_TESTS") == "1", "requires a built native engine")
class NativeEnvironmentTests(unittest.TestCase):
    def test_vector_matches_independent_steps_and_resets_one_lane(self):
        with SM64VectorEnv(2) as batch, SM64Env() as serial:
            initial = batch.reset()
            self.assertEqual(initial[0], serial.reset())
            self.assertNotEqual(batch.envs[0]._process.pid, batch.envs[1]._process.pid)
            for step in range(40):
                action = Action(stick_y=64, a=step % 16 < 3)
                outcomes = batch.step([action, Action(stick_x=40)], 1)
                self.assertEqual(outcomes[0], serial.step(action, 1))
            self.assertEqual(batch.envs[0]._history, [])
            with self.assertRaisesRegex(RuntimeError, "checkpoint_history"):
                batch.envs[0].save_state()
            untouched = batch.envs[0].get_state()
            self.assertEqual(batch.reset_at(1).frame, 0)
            self.assertEqual(batch.envs[0].get_state(), untouched)
            batch.step_async([Action(), Action()], 1)
            with self.assertRaises(RuntimeError):
                batch.envs[0].render()
            self.assertEqual([s.frame for s in batch.step_wait()], [41, 1])

    def test_async_close_and_crashed_lane_recovery(self):
        with SM64VectorEnv(2) as batch:
            batch.reset()
            batch.envs[1]._process.kill()
            batch.envs[1]._process.join()
            with self.assertRaises((RuntimeError, OSError)):
                batch.step([Action(), Action()], 1)
            self.assertTrue(all(env._process is None for env in batch.envs))
            batch.reset()
            batch.step_async([Action(), Action()], 1)
            processes = [env._process for env in batch.envs]
        self.assertTrue(all(process._closed for process in processes))

    def test_first_star_and_early_stop_recording(self):
        from sm64_policy.config import EpisodeConfig
        from sm64_policy.episode import run_episode
        from sm64_policy.paths import DEFAULT_LIBRARY

        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                EpisodeConfig(
                    session_dir=directory,
                    library=str(DEFAULT_LIBRARY),
                    policy="first-star",
                    steps=1200,
                    frame_skip=1,
                    record_every=7,
                )
            )
            self.assertTrue(result["task"]["success"])
            self.assertEqual(result["task"]["initial_mask"], 0)
            self.assertEqual(result["task"]["final_mask"], 32)
            self.assertEqual(result["stars_gained"], 1)
            self.assertEqual(result["steps"], result["task"]["success_frame"] + 60)
            self.assertEqual(result["termination"], "task_success")
            metadata = json.loads((Path(directory) / "rollout.json").read_text())
            self.assertEqual(metadata["frames"][-1]["frame"], result["steps"])
            self.assertTrue(any(e["kind"] == "star_collected" for e in metadata["events"]))

    def test_render_checkpoint_and_continuation(self):
        with SM64Env() as env:
            initial = env.reset(Level.BOB)
            self.assertEqual(initial.level, 9)
            for step in range(40):
                env.step(Action(stick_y=64, a=step % 16 < 3), 4)
            state = env.get_state()
            image = env.render()
            self.assertEqual(image.frame, state.frame)
            self.assertEqual(len(image.rgb), image.width * image.height * 3)
            self.assertGreater(len(set(image.rgb)), 20)
            self.assertEqual(env.get_state(), state, "render must not advance physics")
            checkpoint = env.save_state()
            future = [env.step(Action(stick_y=64), 4) for _ in range(30)]
            self.assertEqual(env.load_state(checkpoint), state)
            self.assertEqual([env.step(Action(stick_y=64), 4) for _ in range(30)], future)
            corrupted = copy.deepcopy(checkpoint)
            corrupted["observation_sha256"] = "bad"
            with self.assertRaises(CheckpointMismatch):
                env.load_state(corrupted)

    def test_oracle_geometry_objects_and_basic_trajectory(self):
        with SM64Env() as oracle, SM64Env(observation_mode="basic") as basic:
            state, reference = oracle.reset(), basic.reset()
            self.assertEqual(state.frame, 0)
            self.assertEqual(state.mario.position, state.position)
            self.assertIsNotNone(state.mario.floor)
            self.assertAlmostEqual(sum(x * x for x in state.mario.floor.normal), 1, places=4)
            self.assertTrue(0 < state.camera.fov_degrees < 180)
            self.assertEqual(len(state.geometry.rays), 18)
            self.assertEqual(state.progress.course, 1)
            self.assertEqual(state.progress.collected_star_masks, (0,) * 26)
            self.assertFalse(state.progress.credits_active)
            self.assertGreater(len(state.objects.items), 0)
            ids = {obj.id: obj.behavior_id for obj in state.objects.items}
            self.assertEqual(len(ids), len(state.objects.items))
            for obj in state.objects.items:
                self.assertGreater(obj.id, 0)
                self.assertAlmostEqual(
                    math.dist(obj.position, state.position), obj.distance, delta=0.002
                )
            snapshot = state.to_dict()
            for step in range(120):
                action = Action(stick_y=64, a=step % 24 < 3)
                state, reference = oracle.step(action), basic.step(action)
                self.assertEqual(
                    {key: state.to_dict()[key] for key in reference.to_dict()}, reference.to_dict()
                )
                self.assertEqual(state.frame, (step + 1) * 4)
                self.assertEqual(state.last_action_frames, 4)
                self.assertEqual(oracle.get_state(), state)
            for obj in state.objects.items:
                if obj.id in ids:
                    self.assertEqual(obj.behavior_id, ids[obj.id])
            self.assertEqual(snapshot["frame"], 0)
            json.dumps(state.to_dict(), allow_nan=False)

    def test_start_pause_and_exit_to_castle(self):
        with SM64Env(gameplay_mode="progression") as env:
            env.reset(Level.BOB)
            for frame in range(160):
                env.step(Action(a=frame % 8 == 0), 1)
            env.step(Action(start=True), 1)
            paused = env.step(Action(), 3)
            self.assertEqual(paused.ui.play_mode, 2)
            for _ in range(2):
                env.step(Action(stick_y=-80), 1)
                env.step(Action(), 3)
            env.step(Action(a=True), 1)
            state = env.step(Action(), 80)
            self.assertEqual((state.level, state.area), (6, 1))
            self.assertEqual(state.ui.play_mode, 0)
            self.assertEqual(state.ui.menu_mode, -1)

    def test_level_and_spawn_reset(self):
        with SM64Env() as env:
            self.assertEqual(env.reset(Level.WF).level, 24)
            spawn = SpawnState((-6558.0, 200.0, 6464.0), yaw=16384)
            state = env.reset(Level.BOB, spawn)
            self.assertEqual(state.position, spawn.position)
            self.assertEqual(state.velocity, (0, 0, 0))
            with self.assertRaises(ValueError):
                env.step(Action(), 0)
            self.assertEqual(env.step(Action(), 1).level, 9)


if __name__ == "__main__":
    unittest.main()
