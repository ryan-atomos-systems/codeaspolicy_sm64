import unittest
from types import SimpleNamespace

from test_star_policy import observation

from sm64_policy.control import GroundPoundObject, air_steer, steer
from sm64_policy.decision_trace import capture_decision


class DecisionTraceTests(unittest.TestCase):
    def test_logging_preserves_controls_and_scopes_nested_decisions(self):
        state = observation(mario=SimpleNamespace(face_angle=(0, 0, 0), forward_velocity=10))
        target = (400, 800)
        plain = (steer(state, target), air_steer(state, target))
        with capture_decision(0) as outer:
            logged = (steer(state, target), air_steer(state, target))
            with capture_decision(4) as inner:
                steer(state, (10, 20))
            steer(state, target)
        self.assertEqual(logged, plain)
        self.assertEqual(len(outer["controls"]), 3)
        self.assertEqual(len(inner["controls"]), 1)
        self.assertEqual(outer["controls"][0]["target_xz"], target)
        self.assertEqual(outer["controls"][1]["action"], plain[1].to_dict())
        self.assertIsNone(steer(state, target).to_dict().get("decision"))

    def test_ground_pound_records_actual_gate_values(self):
        state = observation(
            mario=SimpleNamespace(face_angle=(0, 0, 0), forward_velocity=0, airborne=False)
        )
        post = SimpleNamespace(position=(0, 0, 0), id=1)
        with capture_decision(state.frame) as trace:
            GroundPoundObject(205).act(state, post)
        gate = trace["gates"][0]
        self.assertEqual(gate["conditions"]["airborne"], state.mario.airborne)
        self.assertEqual(gate["height_above_top"], state.position[1] - 205)
