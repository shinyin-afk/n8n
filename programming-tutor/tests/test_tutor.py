"""Tests for topic classification, the hint ladder, and the profiler.

Run from the project root (``programming-tutor``)::

    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tutor.hints import HintLevel, build_hint
from tutor.profiler import (
    describe,
    estimate_capability,
    start_hint_level,
    terminology_score,
)
from tutor.topics import classify_topic


class TopicClassificationTests(unittest.TestCase):
    def test_loop_prompt(self):
        self.assertEqual(classify_topic("write a loop to sum numbers").key, "loops")

    def test_list_prompt(self):
        self.assertEqual(classify_topic("how do I reverse a list").key, "lists")

    def test_recursion_prompt(self):
        self.assertEqual(
            classify_topic("I need a base case for my recursive function").key,
            "recursion",
        )

    def test_sql_prompt(self):
        self.assertEqual(classify_topic("a GROUP BY query joining two tables").key, "sql")

    def test_unknown_prompt_falls_back(self):
        self.assertEqual(classify_topic("hello there").key, "general")


class HintTests(unittest.TestCase):
    def setUp(self):
        self.topic = classify_topic("recursion base case")

    def test_each_level_builds(self):
        for level in HintLevel:
            hint = build_hint(self.topic, "recursion", level)
            self.assertEqual(hint.level, level)
            self.assertTrue(hint.render_text())

    def test_skeleton_includes_code_and_gap(self):
        hint = build_hint(self.topic, "recursion", HintLevel.SKELETON)
        self.assertIsNotNone(hint.code)
        self.assertIn("TODO", hint.code)

    def test_strategy_has_no_code(self):
        hint = build_hint(self.topic, "recursion", HintLevel.STRATEGY)
        self.assertIsNone(hint.code)


class ProfilerTests(unittest.TestCase):
    def test_empty_terminology_is_zero(self):
        self.assertEqual(terminology_score("please help"), 0.0)

    def test_terminology_is_capped(self):
        text = "complexity big o recursion memoization deadlock mutex atomic schema"
        self.assertEqual(terminology_score(text), 1.0)

    def test_no_history_is_neutral(self):
        cap = estimate_capability([])
        self.assertAlmostEqual(cap.overall, 0.5)

    def test_start_level_by_capability(self):
        self.assertEqual(start_hint_level(0.1), HintLevel.STRATEGY)
        self.assertEqual(start_hint_level(0.5), HintLevel.CONCEPT)
        self.assertEqual(start_hint_level(0.9), HintLevel.RESTATE)

    def test_describe_bands(self):
        self.assertEqual(describe(0.1), "beginner")
        self.assertEqual(describe(0.5), "intermediate")
        self.assertEqual(describe(0.9), "advanced")

    def test_solved_with_little_help_raises_score(self):
        low = estimate_capability(
            [{"topic": "loops", "terminology": 0.0, "complexity": 0.2,
              "hint_level": 4, "outcome": "stuck"}]
        )
        high = estimate_capability(
            [{"topic": "recursion", "terminology": 0.8, "complexity": 0.7,
              "hint_level": 0, "outcome": "solved"}]
        )
        self.assertGreater(high.overall, low.overall)


if __name__ == "__main__":
    unittest.main()
