"""Tests for prompt assembly and evaluation parsing."""

import unittest

from app import prompts


class ParseEvaluationTest(unittest.TestCase):
    def test_valid_block_is_parsed_and_stripped(self):
        reply = (
            'Good thinking! What comes next?\n<!--EVAL\n'
            '{"classification": "partial", "concept": "for_loops", '
            '"misconception": null, "evidence_note": null, "workflow": "practice", '
            '"topic": "loops", "step": "trace the loop", "exercise_complete": false}\n-->'
        )
        visible, evaluation = prompts.parse_evaluation(reply)
        self.assertEqual(visible, "Good thinking! What comes next?")
        self.assertEqual(evaluation["classification"], "partial")
        self.assertEqual(evaluation["concept"], "for_loops")
        self.assertEqual(evaluation["workflow"], "practice")
        self.assertFalse(evaluation["exercise_complete"])

    def test_missing_block_gives_defaults(self):
        visible, evaluation = prompts.parse_evaluation("Just a plain reply.")
        self.assertEqual(visible, "Just a plain reply.")
        self.assertEqual(evaluation["classification"], "partial")
        self.assertIsNone(evaluation["concept"])

    def test_malformed_json_gives_defaults_but_keeps_text(self):
        reply = "Some text\n<!--EVAL\n{broken json}\n-->"
        visible, evaluation = prompts.parse_evaluation(reply)
        self.assertEqual(visible, "Some text")
        self.assertEqual(evaluation["classification"], "partial")

    def test_unknown_fields_are_dropped(self):
        reply = 'Text <!--EVAL {"classification": "correct", "surprise": 1} -->'
        _, evaluation = prompts.parse_evaluation(reply)
        self.assertNotIn("surprise", evaluation)
        self.assertEqual(evaluation["classification"], "correct")


class BuildSystemPromptTest(unittest.TestCase):
    def test_contains_state_and_profile(self):
        prompt = prompts.build_system_prompt(
            phase="practice",
            workflow="practice",
            step="trace the loop",
            hint_level=1,
            stuck_count=1,
            solution_requested=False,
            profile_summary='{"concepts": {"for_loops": {"misconceptions": ["off-by-one"]}}}',
        )
        self.assertIn("level 1", prompt)
        self.assertIn("specific guidance", prompt)
        self.assertIn("off-by-one", prompt)
        self.assertIn("trace the loop", prompt)

    def test_stuck_policy_at_highest_hint_level(self):
        prompt = prompts.build_system_prompt(
            phase="practice",
            workflow="practice",
            step="",
            hint_level=3,
            stuck_count=2,
            solution_requested=False,
            profile_summary="",
        )
        self.assertIn("Stop asking questions", prompt)
        self.assertIn("new learner", prompt.lower())

    def test_hint_level_is_clamped(self):
        prompt = prompts.build_system_prompt(
            phase="practice",
            workflow="",
            step="",
            hint_level=99,
            stuck_count=0,
            solution_requested=False,
            profile_summary="",
        )
        self.assertIn("level 3", prompt)


if __name__ == "__main__":
    unittest.main()
