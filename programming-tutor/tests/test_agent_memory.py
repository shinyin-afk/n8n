"""Tests for the learner memory store and the tutor agent's decision flow."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tutor.agent import TutorAgent
from tutor.hints import HintLevel
from tutor.memory import LearnerMemory


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "mem.json")
        self.memory = LearnerMemory(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_or_create(self):
        learner = self.memory.get_or_create("alice")
        self.assertEqual(learner["interactions"], [])

    def test_record_and_outcome(self):
        self.memory.record_interaction("alice", {"prompt": "hi", "hint_level": 1})
        self.memory.set_outcome("alice", "solved")
        self.assertEqual(self.memory.interactions("alice")[-1]["outcome"], "solved")

    def test_persists_across_reopen(self):
        self.memory.record_interaction("alice", {"prompt": "hi", "hint_level": 1})
        reopened = LearnerMemory(self.path)
        self.assertEqual(len(reopened.interactions("alice")), 1)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory = LearnerMemory(os.path.join(self.tmp.name, "mem.json"))
        self.agent = TutorAgent(self.memory)

    def tearDown(self):
        self.tmp.cleanup()

    def test_answer_request_is_redirected(self):
        response = self.agent.respond("alice", "just give me the code to sort a list")
        self.assertEqual(response.kind, "answer_request")
        self.assertIn("won't hand over", response.message)

    def test_stuck_escalates_one_rung(self):
        first = self.agent.respond("alice", "how do I loop over a list?")
        self.assertEqual(first.hint_level, HintLevel.CONCEPT)  # neutral capability
        self.agent.feedback("alice", "stuck")
        second = self.agent.respond("alice", "still stuck on the loop")
        self.assertEqual(second.kind, "followup")
        self.assertEqual(second.hint_level, HintLevel.STRATEGY)

    def test_advanced_learner_starts_more_indirect(self):
        for _ in range(5):
            self.memory.record_interaction(
                "expert",
                {"prompt": "memoize this dynamic programming problem",
                 "topic": "dynamic-programming", "complexity": 0.9,
                 "terminology": 0.8, "hint_level": 0, "kind": "question",
                 "outcome": "solved"},
            )
        response = self.agent.respond("expert", "how do I memoize a recursive fn?")
        self.assertEqual(response.hint_level, HintLevel.RESTATE)


if __name__ == "__main__":
    unittest.main()
