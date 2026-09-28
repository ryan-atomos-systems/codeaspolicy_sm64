"""Independent campaign evidence and configuration regression checks."""

import unittest
from dataclasses import replace
from pathlib import Path

from test_star_policy import observation

from sm64_policy.campaign.cannon import ballistic_pitch
from sm64_policy.config import SuiteConfig
from sm64_policy.tasks import CampaignGoal, CampaignTask


class CampaignTests(unittest.TestCase):
    def test_tower_alignment_does_not_stall_in_controller_dead_zone(self):
        from types import SimpleNamespace

        from sm64_policy.campaign.tower import Tower
        from sm64_policy.control import steer

        # Linux failure: waiting to jump from the diagonal platform to the
        # north platform, while the original -5 lateral input is discarded.
        s = replace(
            observation(level=24, frame=36000),
            position=(264.0, 4185.0, -527.193115234375),
            mario=SimpleNamespace(
                face_angle=(0, -24576, 0), airborne=False, platform_id=11438, floor=None
            ),
            ui=SimpleNamespace(dialog_id=-1),
            objects=SimpleNamespace(
                items=(
                    SimpleNamespace(
                        id=18607,
                        behavior_name="bhvWfSolidTowerPlatform",
                        position=(0.0, 4183.0, -704.0),
                        velocity=(0.0, 0.0, 0.0),
                    ),
                )
            ),
        )
        self.assertEqual(steer(s, (0, -704), 24).stick_x, -5)
        tower = Tower()
        tower.index = 4
        action = tower.act(s)
        self.assertLessEqual(action.stick_x, -8)
        self.assertFalse(action.a)  # Align before jumping, rather than bypassing the gate.

    def test_alignment_turns_both_directions_without_changing_forward_input(self):
        from types import SimpleNamespace

        from sm64_policy.control import steer

        s = observation(mario=SimpleNamespace(face_angle=(0, 0, 0)))
        for x in (-20, 20):
            with self.subTest(x=x):
                walking = steer(s, (x, 100), 24)
                aligning = steer(s, (x, 100), 24, ensure_turn=True)
                self.assertLess(abs(walking.stick_x), 8)
                self.assertGreaterEqual(abs(aligning.stick_x), 8)
                self.assertLess(aligning.stick_x * x, 0)
                self.assertEqual(aligning.stick_y, walking.stick_y)
        self.assertEqual(steer(s, (0, 100), 24, ensure_turn=True).stick_x, 0)

    def test_eight_unique_bits_and_key_are_both_required(self):
        initial = observation(level=16)
        task = CampaignTask(CampaignGoal(), initial)
        masks = [0] * 26
        masks[1], masks[2], masks[19], masks[24] = 32, 23, 3, 1
        progress = replace(initial.progress, collected_star_masks=tuple(masks), stars=8)
        state = replace(initial, progress=progress, frame=100)
        self.assertFalse(task.update(state))
        self.assertEqual(task.earned_stars, 8)
        self.assertEqual(len(task.events), 8)
        self.assertFalse(task.update(state))
        self.assertEqual(len(task.events), 8)
        self.assertTrue(
            task.update(replace(state, progress=replace(progress, save_flags=17), frame=200))
        )
        self.assertFalse(
            task.update(replace(state, progress=replace(progress, save_flags=17), frame=201))
        )
        self.assertEqual(task.success_frame, 200)
        seven = masks.copy()
        seven[24] = 0
        task = CampaignTask(CampaignGoal(), initial)
        fake_hud = replace(progress, collected_star_masks=tuple(seven), stars=99, save_flags=17)
        self.assertFalse(task.update(replace(state, progress=fake_hud)))

    def test_start_requires_empty_save_and_castle_grounds(self):
        with self.assertRaisesRegex(ValueError, "empty save"):
            CampaignTask(CampaignGoal(), observation(mask=32, level=16))
        with self.assertRaisesRegex(ValueError, "castle grounds"):
            CampaignTask(CampaignGoal(), observation(level=9))

    def test_campaign_settings_reach_each_worker(self):
        suite = SuiteConfig(Path("unused"), Path("library"), level=16, gameplay_mode="progression")
        episode = suite.episode(Path("unused/session"), 7777, "first-bowser", 0)
        self.assertEqual((episode.level, episode.gameplay_mode), (16, "progression"))

    def test_cannon_ballistics_select_the_pole_arc(self):
        distance = ((-2495 + 1844) ** 2 + (-256 - 3893) ** 2) ** 0.5
        error, pitch = ballistic_pitch(distance, 1036, 1850)
        self.assertEqual(pitch, 4180)
        self.assertLess(error, 2)

    def test_battle_death_resumes_at_pipe_checkpoint(self):
        from sm64_policy.campaign.policy import FirstBowser

        policy = FirstBowser()
        policy.level = 30
        state = observation(level=17)
        policy.enter(state)
        self.assertTrue(policy.skill.upper_ready)
        self.assertEqual(policy.skill.finish.stairs.phase, "pipe")

    def test_game_over_uses_lobby_route(self):
        from sm64_policy.campaign.policy import FirstBowser

        policy = FirstBowser()
        policy.level = 16
        policy.enter(replace(observation(level=6), stars=8))
        self.assertEqual(policy.route.points[0], (-1024, 600))
        self.assertEqual(policy.route.points[-1], (-5513, -4324))

    def test_retries_vary_timing_without_delaying_the_first_attempt(self):
        from sm64_policy.campaign.policy import FirstBowser

        policy = FirstBowser()
        policy.level = 6
        policy.enter(observation(level=17, frame=100))
        self.assertEqual(policy.retry_until, 100)
        policy.level = 6
        policy.enter(observation(level=17, frame=200))
        self.assertEqual(policy.retry_until, 237)

    def test_upper_course_ignores_goombas_on_another_floor(self):
        from types import SimpleNamespace

        from sm64_policy.campaign.upper_bitdw import Upper
        from sm64_policy.state import NearbyObjects

        skill = Upper()
        skill.phase = "route"
        skill.route.index = 9
        enemy = SimpleNamespace(behavior_name="bhvGoomba", position=(-1680, -1433, 500), action=0)
        s = replace(
            observation(level=17),
            position=(-1750, 1024, 500),
            ui=SimpleNamespace(dialog_id=-1),
            mario=SimpleNamespace(airborne=False, face_angle=(0, 0, 0), forward_velocity=0),
            objects=NearbyObjects(6000, 64, 1, False, (enemy,)),
        )
        skill.act(s)
        self.assertTrue(skill.approach_cleared)
        self.assertEqual(skill.target, (-1750, -60))
