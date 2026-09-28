import unittest
from dataclasses import replace
from types import SimpleNamespace

from sm64_policy import Observation
from sm64_policy.control import air_steer, query_covers, steer
from sm64_policy.first_star import FirstStar
from sm64_policy.state import NearbyObjects, ProgressState
from sm64_policy.tasks import StarTask


def observation(mask=0, **kwargs):
    masks = (0, mask) + (0,) * 24
    progress = ProgressState(
        level=9,
        area=1,
        act=0,
        course=1,
        save_file=1,
        stars=mask.bit_count(),
        coins=0,
        lives=4,
        save_flags=1,
        collected_star_masks=masks,
        cannon_unlocked_mask=0,
        last_completed_course=0,
        last_completed_star=0,
        credits_active=False,
    )
    return Observation((0, 0, 0), (0, 0, 0), 8, progress=progress, **kwargs)


class StarPolicyTests(unittest.TestCase):
    def test_success_requires_target_bit_transition(self):
        initial = observation()
        task = StarTask(FirstStar.goal, initial)
        self.assertFalse(task.update(observation(mask=1, frame=4)))  # Wrong star.
        self.assertTrue(task.update(observation(mask=33, frame=7)))
        self.assertFalse(task.update(observation(mask=33, frame=8)))  # Emit only once.
        self.assertEqual(task.success_frame, 7)
        with self.assertRaisesRegex(ValueError, "already present"):
            StarTask(FirstStar.goal, observation(mask=32))
        with self.assertRaisesRegex(ValueError, "oracle progress"):
            StarTask(FirstStar.goal, replace(initial, progress=None))

    def test_control_handles_heading_wrap_and_air_braking(self):
        mario = SimpleNamespace(face_angle=(0, 32760, 0), forward_velocity=20)
        state = observation(mario=mario)
        action = steer(state, (-1, -1000))
        self.assertGreater(action.stick_y, 60)
        self.assertLess(abs(action.stick_x), 2)
        mario.face_angle = (0, 0, 0)
        self.assertLess(steer(state, (100, 0)).stick_x, 0)
        self.assertLess(air_steer(state, (0, 5)).stick_y, 0)  # Brake an overshoot.
        self.assertTrue(air_steer(state, (0, 5)).a)

    def test_object_absence_requires_query_coverage(self):
        state = observation(objects=NearbyObjects(6000, 64, 0, False, ()))
        self.assertTrue(query_covers(state, (0, 0, 1500)))
        self.assertFalse(query_covers(state, (0, 0, 6100)))
        state = replace(state, objects=NearbyObjects(6000, 64, 80, True, ()))
        self.assertFalse(query_covers(state, (0, 0, 1500)))
        self.assertFalse(query_covers(replace(state, objects=None), (0, 0, 0)))

    def test_policy_rejects_missing_oracle(self):
        with self.assertRaisesRegex(ValueError, "oracle"):
            FirstStar().act(Observation((0, 0, 0), (0, 0, 0), 8), 0)

    def test_bridge_recovery_uses_the_side_of_the_fall(self):
        mario = SimpleNamespace(face_angle=(0, 0, 0), forward_velocity=0, airborne=False)
        for z, target in ((6200, (-500, 6650)), (4700, (-1400, 4500))):
            policy = FirstStar()
            policy.waypoint = 2
            state = replace(
                observation(level=9, mario=mario, objects=NearbyObjects(6000, 64, 0, False, ())),
                position=(-1200, 0, z),
                frame=400,
            )
            policy.act(state, 400)
            self.assertEqual(policy.target, target)
            self.assertEqual(policy.recoveries, 1)

    def test_dying_mario_does_not_raise_missing_post_error(self):
        policy = FirstStar()
        policy.waypoint = len(policy.route)
        state = replace(
            observation(
                level=9, mario=SimpleNamespace(), objects=NearbyObjects(6000, 64, 0, False, ())
            ),
            health=0,
        )
        from sm64_policy import Action

        self.assertEqual(policy.act(state, 0), Action())

    def test_auto_respawn_discards_an_old_trench_detour(self):
        policy = FirstStar()
        policy.bridge_recovery = 0
        policy.recovery_route = ((-500, 6650),)
        mario = SimpleNamespace(face_angle=(0, 0, 0), forward_velocity=0, airborne=False)
        state = replace(
            observation(level=9, mario=mario, objects=NearbyObjects(6000, 64, 0, False, ())),
            died=True,
            position=(-6558, 0, 6464),
        )
        policy.act(state, 0)
        self.assertIsNone(policy.bridge_recovery)
        self.assertEqual(policy.target, policy.route[0])
