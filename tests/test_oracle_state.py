"""Schema/translation tests that require no ROM or compiled library."""

import ctypes as ct
import json
import pickle
import unittest
from dataclasses import asdict, replace

from sm64_policy import Observation
from sm64_policy.native_state import Oracle, OracleReader
from sm64_policy.state import record_from_dict
from sm64_policy.storage import observation_hash


class Function:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


class FakeLibrary:
    def __init__(self):
        from sm64_policy.native_state import Camera, Mario, Object, Progress, Ray, Surface

        records = (Oracle, Mario, Camera, Progress, Object, Ray, Surface)
        self.sm64_policy_state_size = Function(lambda index: ct.sizeof(records[index]))
        self.sm64_policy_read_state = Function(lambda *args: 1)
        self.sm64_policy_behavior_name = Function(lambda *args: b"bhvYellowCoin")


class OracleStateTests(unittest.TestCase):
    def test_missing_geometry_and_identity_translate_without_fabricated_zeros(self):
        reader = OracleReader(FakeLibrary())
        reader.buffer.version = 1
        reader.buffer.object_count = 1
        reader.buffer.objects_in_radius = 70
        reader.buffer.object_radius = 6000
        obj = reader.buffer.objects[0]
        obj.id = 1025
        obj.position[:] = (10, 20, 30)
        obj.interaction_type = 1 << 4
        reader.buffer.progress.star_masks[1] = 1 << 6
        values = reader.read((1, 2, 3), (0, 0, 0), 128, 72)
        state = Observation((1, 2, 3), (0, 0, 0), 8, **values)
        self.assertIsNone(state.camera)
        self.assertIsNone(state.mario.floor)
        self.assertIsNone(state.mario.floor_height)
        self.assertIsNone(state.mario.held_object_id)
        self.assertIsNone(state.geometry.rays[0].hit_distance)
        self.assertTrue(state.objects.truncated)
        self.assertEqual(state.objects.items[0].relative_position, (9, 18, 27))
        self.assertEqual(state.objects.items[0].affordances, ("coin",))
        self.assertTrue(state.progress.has_star(1, 7))
        self.assertFalse(state.progress.has_star(1, 1))
        with self.assertRaises(ValueError):
            state.progress.has_star(1, 0)
        json.dumps(state.to_dict(), allow_nan=False)
        restored = pickle.loads(pickle.dumps(state))
        self.assertEqual(restored, state)
        self.assertEqual(restored.to_dict(), state.to_dict())
        for key in ("mario", "camera", "geometry", "objects", "progress"):
            self.assertEqual(asdict(state)[key], state.to_dict()[key])
        decoded = record_from_dict(Observation, json.loads(json.dumps(state.to_dict())))
        self.assertEqual(decoded, state)
        self.assertEqual(observation_hash(decoded), observation_hash(state))
        self.assertNotEqual(observation_hash(replace(state, frame=1)), observation_hash(state))
        changed = replace(
            state,
            objects=replace(state.objects, items=(replace(state.objects.items[0], timer=99),)),
        )
        self.assertNotEqual(observation_hash(changed), observation_hash(state))
        # No mutable reference to reused ctypes buffers escapes into old observations.
        obj.position[0] = 999
        self.assertEqual(state.objects.items[0].position, (10, 20, 30))

    def test_rejects_incompatible_native_layout(self):
        library = FakeLibrary()
        library.sm64_policy_state_size = Function(lambda _: 1)
        with self.assertRaisesRegex(RuntimeError, "size mismatch"):
            OracleReader(library)
