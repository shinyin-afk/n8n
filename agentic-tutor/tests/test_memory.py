"""Tests for the learner profile store."""

import json
import os
import tempfile
import unittest

from app.memory import (
    EVIDENCE_INDEPENDENT,
    EVIDENCE_STRUGGLE,
    EVIDENCE_WITH_HINTS,
    ProfileStore,
)


class ProfileStoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "profile.json")
        self.store = ProfileStore(self.path)

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_file_returns_empty_profile(self):
        profile = self.store.load()
        self.assertEqual(profile["concepts"], {})
        self.assertEqual(profile["exercises"], [])
        self.assertFalse(self.store.exists())

    def test_corrupt_file_returns_empty_profile(self):
        with open(self.path, "w") as handle:
            handle.write("{not json")
        self.assertEqual(self.store.load()["concepts"], {})

    def test_record_evidence_and_summarize(self):
        self.store.record_evidence("for_loops", EVIDENCE_INDEPENDENT, "traced a loop")
        self.store.record_evidence("for_loops", EVIDENCE_WITH_HINTS, "fixed off-by-one")
        self.store.record_evidence("for_loops", EVIDENCE_STRUGGLE, "stuck on range")
        summary = self.store.summarize()
        entry = summary["concepts"]["for_loops"]
        self.assertEqual(entry["independent_successes"], 1)
        self.assertEqual(entry["successes_with_hints"], 1)
        self.assertEqual(entry["struggles"], 1)

    def test_two_independent_successes_clear_misconceptions(self):
        self.store.record_misconception("for_loops", "range(n) includes n")
        self.store.record_evidence("for_loops", EVIDENCE_INDEPENDENT, "a")
        entry = self.store.load()["concepts"]["for_loops"]
        self.assertEqual(entry["misconceptions"], ["range(n) includes n"])
        self.store.record_evidence("for_loops", EVIDENCE_INDEPENDENT, "b")
        entry = self.store.load()["concepts"]["for_loops"]
        self.assertEqual(entry["misconceptions"], [])

    def test_misconception_dedup(self):
        self.store.record_misconception("lists", "indexing starts at 1")
        self.store.record_misconception("lists", "indexing starts at 1")
        entry = self.store.load()["concepts"]["lists"]
        self.assertEqual(entry["misconceptions"], ["indexing starts at 1"])

    def test_record_hint_increments(self):
        self.store.record_hint("strings")
        self.store.record_hint("strings")
        self.assertEqual(self.store.load()["concepts"]["strings"]["hints_used"], 2)

    def test_record_exercise_appends(self):
        self.store.record_exercise("loops", "practice", "solved_with_hints", 2)
        exercises = self.store.load()["exercises"]
        self.assertEqual(len(exercises), 1)
        self.assertEqual(exercises[0]["outcome"], "solved_with_hints")
        self.assertEqual(exercises[0]["hints_used"], 2)

    def test_reset_keeps_goals_clears_progress(self):
        self.store.add_goal("learn loops")
        self.store.record_evidence("loops", EVIDENCE_INDEPENDENT, "x")
        self.store.reset_progress()
        profile = self.store.load()
        self.assertEqual(profile["goals"], ["learn loops"])
        self.assertEqual(profile["concepts"], {})

    def test_delete(self):
        self.store.add_goal("g")
        self.assertTrue(self.store.delete())
        self.assertFalse(self.store.exists())
        self.assertFalse(self.store.delete())

    def test_correct_allowed_and_rejected_fields(self):
        self.store.correct("goals", ["revised goal"])
        self.assertEqual(self.store.load()["goals"], ["revised goal"])
        with self.assertRaises(ValueError):
            self.store.correct("version", 99)

    def test_saved_file_is_valid_json(self):
        self.store.add_goal("g")
        with open(self.path) as handle:
            json.load(handle)


if __name__ == "__main__":
    unittest.main()
