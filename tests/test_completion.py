"""Reject partial runs and credits-only claims; preserve pre-ending evidence."""

import unittest
from dataclasses import replace
from types import SimpleNamespace

from test_star_policy import observation

from sm64_policy.completion import SixteenStarCompletion
from sm64_policy.state import NearbyObjects


class CompletionTests(unittest.TestCase):
    def test_requires_both_keys_defeat_grand_star_and_credits(self):
        initial = observation(level=16)
        task = SixteenStarCompletion(initial)
        masks = (1, 32, 55, 0, 0, 0, 1, 23, 0, 1) + (0,) * 9 + (3, 0, 0, 0, 0, 1, 0)
        progress = replace(initial.progress, stars=16, collected_star_masks=masks, save_flags=64)
        state = replace(initial, progress=progress, frame=1)
        self.assertFalse(task.update(state))
        # The first key has been spent, so the unlocked-door flag is valid evidence.
        state = replace(state, progress=replace(progress, save_flags=128), frame=2)
        self.assertFalse(task.update(state))
        state = replace(
            state,
            level=34,
            frame=3,
            objects=NearbyObjects(
                6000, 64, 1, False, (SimpleNamespace(behavior_name="bhvBowser", health=0),)
            ),
        )
        self.assertFalse(task.update(state))
        state = replace(state, frame=4, mario=SimpleNamespace(action=0x1909))
        self.assertFalse(task.update(state))
        # Credits clear transient save flags; earlier evidence must remain latched.
        state = replace(
            state, level=16, frame=5, progress=replace(progress, save_flags=0, credits_active=True)
        )
        self.assertTrue(task.update(state))
        self.assertEqual(task.to_dict()["success_frame"], 5)
        self.assertFalse(task.update(state))
        self.assertFalse(task.to_dict()["autonomous_policy_validation"])

    def test_credits_alone_do_not_prove_completion(self):
        initial = observation(level=16)
        task = SixteenStarCompletion(initial)
        self.assertFalse(
            task.update(replace(initial, progress=replace(initial.progress, credits_active=True)))
        )
        self.assertIsNone(task.success_frame)
