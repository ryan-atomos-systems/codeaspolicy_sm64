"""Batch ordering, validation and failure recovery without native dependencies."""

import unittest
from typing import ClassVar
from unittest.mock import patch

from sm64_policy import Action, SM64VectorEnv
from sm64_policy.environment import SM64Env


class Lane:
    calls: ClassVar[list] = []
    count = 0

    def __init__(self, **options):
        self.index = Lane.count
        Lane.count += 1
        self.options = options
        self.fail = False
        self.state = None
        self.pending = False

    def reset_async(self, level, spawn):
        self.calls.append(("reset_send", self.index))
        self.pending = True

    def reset_wait(self):
        self.calls.append(("reset_wait", self.index))
        self.pending = False
        self.state = self.index
        return self.state

    def _idle(self):
        if self.pending:
            raise RuntimeError("pending")

    def get_state(self):
        if self.state is None:
            raise RuntimeError("not reset")
        return self.state

    _validate_step = staticmethod(SM64Env._validate_step)

    def step_async(self, action, count):
        self.calls.append(("step_send", self.index))
        self.pending = True

    def step_wait(self):
        self.calls.append(("step_wait", self.index))
        if self.fail:
            raise TimeoutError("failed lane")
        self.pending = False
        return self.index

    def _stop(self):
        self.calls.append(("stop", self.index))
        self.pending = False
        self.state = None

    def close(self):
        self.calls.append(("close", self.index))


class VectorTests(unittest.TestCase):
    def setUp(self):
        Lane.calls, Lane.count = [], 0
        self.patch = patch("sm64_policy.vector.SM64Env", Lane)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_dispatches_entire_batch_before_wait_and_preserves_lane_order(self):
        with SM64VectorEnv(3) as env:
            self.assertEqual(env.reset(), (0, 1, 2))
            self.assertEqual(
                Lane.calls,
                [("reset_send", i) for i in range(3)] + [("reset_wait", i) for i in range(3)],
            )
            self.assertFalse(env.envs[0].options["checkpoint_history"])
            Lane.calls.clear()
            env.step_async([Action()] * 3, [1, 2, 4])
            with self.assertRaises(RuntimeError):
                env.step_async([Action()] * 3)
            self.assertEqual(env.step_wait(), (0, 1, 2))
            self.assertEqual(
                Lane.calls,
                [("step_send", i) for i in range(3)] + [("step_wait", i) for i in range(3)],
            )

    def test_bad_batch_does_not_partially_advance(self):
        with SM64VectorEnv(2) as env:
            env.reset()
            Lane.calls.clear()
            for actions, frames in [
                ([Action()], 1),
                ([Action(), object()], 1),
                ([Action()] * 2, [1, 0]),
            ]:
                with self.assertRaises((TypeError, ValueError)):
                    env.step_async(actions, frames)
            self.assertEqual(Lane.calls, [])

    def test_failed_lane_discards_partial_batch_and_can_reset(self):
        with SM64VectorEnv(2) as env:
            env.reset()
            env.envs[1].fail = True
            with self.assertRaises(TimeoutError):
                env.step([Action()] * 2)
            self.assertTrue(all(e.state is None and not e.pending for e in env.envs))
            self.assertEqual(env.reset(), (0, 1))
            env.envs[1].fail = False
            self.assertEqual(env.step([Action()] * 2), (0, 1))
        with self.assertRaises(RuntimeError):
            env.reset()
