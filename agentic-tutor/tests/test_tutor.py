"""Tests for the tutoring engine's learning loop.

Uses MockLLMClient scripts, so no network or API key is needed.
"""

import json
import os
import tempfile
import unittest

from app.llm import MockLLMClient
from app.memory import ProfileStore
from app.tutor import PHASE_INTAKE, PHASE_PRACTICE, TutorEngine


def eval_block(**overrides):
    base = {
        "classification": "partial",
        "concept": None,
        "misconception": None,
        "evidence_note": None,
        "workflow": None,
        "topic": None,
        "step": None,
        "exercise_complete": False,
    }
    base.update(overrides)
    return "<!--EVAL\n" + json.dumps(base) + "\n-->"


def reply(text, **evaluation):
    return text + "\n" + eval_block(**evaluation)


class TutorLoopTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = ProfileStore(os.path.join(self.dir.name, "profile.json"))

    def tearDown(self):
        self.dir.cleanup()

    def make_engine(self, script=None, fail=False):
        llm = MockLLMClient(script=script, fail=fail)
        return TutorEngine(llm, self.store), llm

    def test_eval_block_is_hidden_from_learner(self):
        engine, _ = self.make_engine([reply("What should the loop print?", workflow="practice")])
        result = engine.handle_message("s1", "I want to practice loops")
        self.assertEqual(result["reply"], "What should the loop print?")
        self.assertNotIn("EVAL", result["reply"])
        self.assertFalse(result["error"])

    def test_workflow_transitions_phase(self):
        engine, _ = self.make_engine(
            [reply("ok", workflow="practice", topic="for_loops", step="trace loop")]
        )
        result = engine.handle_message("s1", "I want to practice loops")
        self.assertEqual(result["phase"], PHASE_PRACTICE)

    def test_correct_answer_records_independent_evidence(self):
        engine, _ = self.make_engine(
            [reply("right!", classification="correct", concept="for_loops",
                   evidence_note="traced the loop correctly")]
        )
        engine.handle_message("s1", "it prints 0 1 2")
        entry = self.store.load()["concepts"]["for_loops"]
        self.assertEqual(entry["evidence"][0]["kind"], "independent_success")

    def test_correct_after_hints_records_success_with_hints(self):
        engine, _ = self.make_engine(
            [
                reply("h", classification="stuck", concept="loops"),
                reply("hint offered", classification="partial", concept="loops"),
                reply("yes!", classification="correct", concept="loops",
                      evidence_note="got it after hint"),
            ]
        )
        engine.handle_message("s1", "no idea")
        engine.handle_message("s1", "/hint")
        engine.handle_message("s1", "now I see, it stops at n-1")
        kinds = [e["kind"] for e in self.store.load()["concepts"]["loops"]["evidence"]]
        self.assertIn("solved_with_hints", kinds)

    def test_stuck_escalates_hint_level_in_prompt(self):
        engine, llm = self.make_engine(
            [
                reply("h0", classification="stuck", concept="loops"),
                reply("h1", classification="stuck", concept="loops"),
                reply("explanation follows", classification="partial"),
            ]
        )
        engine.handle_message("s1", "idk")
        engine.handle_message("s1", "still idk")
        engine.handle_message("s1", "third")
        # The third call's system prompt must carry the explain-don't-ask policy.
        system_prompt = llm.calls[2][0]["content"]
        self.assertIn("Stop asking questions", system_prompt)
        self.assertIn("level 3", system_prompt)

    def test_correct_resets_stuck_count(self):
        engine, _ = self.make_engine(
            [
                reply("h", classification="stuck", concept="loops"),
                reply("good", classification="correct", concept="loops",
                      evidence_note="recovered"),
            ]
        )
        session = engine.get_session("s1")
        engine.handle_message("s1", "idk")
        self.assertEqual(session.stuck_count, 1)
        engine.handle_message("s1", "oh, it prints 0 1 2")
        self.assertEqual(session.stuck_count, 0)
        self.assertEqual(session.hint_level, 0)


    def test_misconception_recorded_and_injected_next_turn(self):
        engine, llm = self.make_engine(
            [
                reply("not quite", classification="misconception", concept="lists",
                      misconception="list indexing starts at 1"),
                reply("next question", classification="partial"),
            ]
        )
        engine.handle_message("s1", "so list[1] is the first element")
        engine.handle_message("s1", "ok what next")
        entry = self.store.load()["concepts"]["lists"]
        self.assertEqual(entry["misconceptions"], ["list indexing starts at 1"])
        system_prompt = llm.calls[1][0]["content"]
        self.assertIn("list indexing starts at 1", system_prompt)

    def test_exercise_complete_records_outcome_and_resets(self):
        engine, _ = self.make_engine(
            [
                reply("done!", classification="correct", concept="loops",
                      evidence_note="solved", topic="loops", workflow="practice",
                      exercise_complete=True)
            ]
        )
        result = engine.handle_message("s1", "finished!")
        exercises = self.store.load()["exercises"]
        self.assertEqual(exercises[0]["outcome"], "solved_independently")
        self.assertEqual(result["phase"], PHASE_INTAKE)

    def test_graceful_failure_preserves_state(self):
        engine, _ = self.make_engine(fail=True)
        result = engine.handle_message("s1", "help me with loops")
        self.assertTrue(result["error"])
        self.assertIn("trouble", result["reply"])
        # The user turn was kept so a retry continues the conversation.
        session = engine.get_session("s1")
        self.assertEqual(session.history[-1]["content"], "help me with loops")


class TutorCommandTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = ProfileStore(os.path.join(self.dir.name, "profile.json"))
        self.llm = MockLLMClient(script=[reply("here is a hint")])
        self.engine = TutorEngine(self.llm, self.store)

    def tearDown(self):
        self.dir.cleanup()

    def test_help_and_unknown(self):
        self.assertIn("/profile", self.engine.handle_message("s", "/help")["reply"])
        self.assertIn("/help", self.engine.handle_message("s", "/nope")["reply"])

    def test_profile_command_shows_stored_data(self):
        self.store.add_goal("learn loops")
        result = self.engine.handle_message("s", "/profile")
        self.assertIn("learn loops", result["reply"])

    def test_goal_command(self):
        self.engine.handle_message("s", "/goal get better at debugging")
        self.assertEqual(self.store.load()["goals"], ["get better at debugging"])

    def test_hint_escalates_and_calls_llm(self):
        session = self.engine.get_session("s")
        result = self.engine.handle_message("s", "/hint")
        self.assertEqual(session.hint_level, 1)
        self.assertEqual(session.hints_this_exercise, 1)
        self.assertEqual(len(self.llm.calls), 1)
        self.assertEqual(result["reply"], "here is a hint")

    def test_solution_sets_explicit_request(self):
        self.llm.script.append(reply("solution and practice question"))
        session = self.engine.get_session("s")
        self.engine.handle_message("s", "/solution")
        self.assertTrue(session.solution_requested)
        system_prompt = self.llm.calls[-1][0]["content"]
        self.assertIn("Solution explicitly requested by learner: yes", system_prompt)

    def test_end_records_outcome(self):
        self.engine.handle_message("s", "/end")
        self.assertEqual(self.store.load()["exercises"][0]["outcome"], "ended_by_learner")

    def test_reset_and_delete(self):
        self.store.record_evidence("loops", "independent_success", "x")
        self.engine.handle_message("s", "/reset")
        self.assertEqual(self.store.load()["concepts"], {})
        result = self.engine.handle_message("s", "/delete")
        self.assertIn("deleted", result["reply"])
        self.assertFalse(self.store.exists())


if __name__ == "__main__":
    unittest.main()
