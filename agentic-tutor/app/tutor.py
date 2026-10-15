"""Tutoring engine: the explicit learning loop.

One agent, one loop per learner message:
  identify goal -> choose next step -> act (question/hint/action) ->
  evaluate response -> update profile -> adjust -> summarize at the end.

No HTTP or network code here. The engine depends on an LLM client with a
`chat(messages)` method and a ProfileStore.
"""

from __future__ import annotations

import json

from . import memory, prompts
from .llm import LLMError

# Phases of the session state machine.
PHASE_INTAKE = "intake"
PHASE_PRACTICE = "practice"
PHASE_DEBUGGING = "debugging"

# After this many consecutive stuck/failed attempts on one step, the next
# turn switches to "explain with an example, then check" (highest hint level).
STUCK_THRESHOLD = 2

# Evaluations that count as a failed/stuck attempt on the current step.
_STUCK_CLASSES = {"stuck", "incorrect", "misconception"}

MAX_HISTORY_MESSAGES = 40

_FALLBACK_REPLY = (
    "I'm having trouble reaching the language model right now, so I can't "
    "give you a proper response. Your work so far is saved. Please try "
    "again in a moment - or tell me where you got up to and we will "
    "continue from there."
)


class Session:
    """In-memory state for one learner conversation."""

    def __init__(self) -> None:
        self.phase = PHASE_INTAKE
        self.workflow: str | None = None
        self.topic: str | None = None
        self.step: str | None = None
        self.hint_level = 0
        self.stuck_count = 0
        self.hints_this_exercise = 0
        self.solution_requested = False
        self.history: list[dict] = []


class TutorEngine:
    """Runs the learning loop and updates the learner profile."""

    def __init__(self, llm, store: memory.ProfileStore) -> None:
        self.llm = llm
        self.store = store
        self.sessions: dict[str, Session] = {}

    def get_session(self, session_id: str) -> Session:
        return self.sessions.setdefault(session_id, Session())

    # --- public entry point -------------------------------------------------

    def handle_message(self, session_id: str, text: str) -> dict:
        """Process one learner message and return the assistant reply."""
        session = self.get_session(session_id)
        text = text.strip()
        if text.startswith("/"):
            return self._handle_command(session, text)
        return self._run_learning_loop(session, text)

    # --- the learning loop ---------------------------------------------------

    def _run_learning_loop(self, session: Session, text: str) -> dict:
        session.history.append({"role": "user", "content": text})
        system_prompt = self._system_prompt(session)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(session.history[-MAX_HISTORY_MESSAGES:])

        try:
            raw_reply = self.llm.chat(messages)
        except LLMError:
            # Graceful failure: state and history are preserved, the learner
            # can simply retry.
            return {"reply": _FALLBACK_REPLY, "phase": session.phase, "error": True}

        visible, evaluation = prompts.parse_evaluation(raw_reply)
        self._apply_evaluation(session, evaluation)
        session.history.append({"role": "assistant", "content": raw_reply})
        return {
            "reply": visible,
            "phase": session.phase,
            "error": False,
            "evaluation": {
                "classification": evaluation["classification"],
                "concept": evaluation["concept"],
                "hint_level": session.hint_level,
                "stuck_count": session.stuck_count,
            },
        }

    def _system_prompt(self, session: Session) -> str:
        summary = self.store.summarize()
        if summary["concepts"] or summary["goals"]:
            profile_text = json.dumps(summary, indent=2)
        else:
            profile_text = ""
        return prompts.build_system_prompt(
            phase=session.phase,
            workflow=session.workflow or "",
            step=session.step or "",
            hint_level=session.hint_level,
            stuck_count=session.stuck_count,
            solution_requested=session.solution_requested,
            profile_summary=profile_text,
        )

    def _apply_evaluation(self, session: Session, evaluation: dict) -> None:
        """Update session state and the persistent profile (loop step 5)."""
        classification = evaluation["classification"]
        concept = evaluation.get("concept")

        # Phase transitions driven by the identified workflow.
        if evaluation.get("workflow") in ("practice", "debugging"):
            session.workflow = evaluation["workflow"]
            session.phase = (
                PHASE_PRACTICE if session.workflow == "practice" else PHASE_DEBUGGING
            )
        if evaluation.get("topic"):
            session.topic = evaluation["topic"]
        if evaluation.get("step"):
            session.step = evaluation["step"]

        # Stuck tracking and hint escalation (rule-based, not LLM-decided).
        if classification in _STUCK_CLASSES:
            session.stuck_count += 1
            level = session.stuck_count
            if session.stuck_count >= STUCK_THRESHOLD:
                level += 1  # jump to explain-with-example after the threshold
            session.hint_level = min(level, len(prompts.HINT_LEVELS) - 1)
            if concept and evaluation.get("evidence_note"):
                self.store.record_evidence(
                    concept, memory.EVIDENCE_STRUGGLE, evaluation["evidence_note"]
                )
        elif classification == "correct":
            session.stuck_count = 0
            session.hint_level = 0
            if concept:
                kind = (
                    memory.EVIDENCE_WITH_HINTS
                    if session.hints_this_exercise > 0
                    else memory.EVIDENCE_INDEPENDENT
                )
                note = evaluation.get("evidence_note") or "answered correctly"
                self.store.record_evidence(concept, kind, note)

        if classification == "misconception" and concept and evaluation.get("misconception"):
            self.store.record_misconception(concept, evaluation["misconception"])

        # Exercise completion: record the outcome and return to intake.
        if evaluation.get("exercise_complete"):
            outcome = (
                "solved_independently"
                if session.hints_this_exercise == 0
                else "solved_with_hints"
            )
            self.store.record_exercise(
                topic=session.topic or "unspecified",
                workflow=session.workflow or "practice",
                outcome=outcome,
                hints_used=session.hints_this_exercise,
            )
            self._reset_exercise_state(session)

    def _reset_exercise_state(self, session: Session) -> None:
        session.phase = PHASE_INTAKE
        session.workflow = None
        session.topic = None
        session.step = None
        session.hint_level = 0
        session.stuck_count = 0
        session.hints_this_exercise = 0
        session.solution_requested = False

    # --- learner-facing commands ---------------------------------------------

    def _handle_command(self, session: Session, text: str) -> dict:
        command, _, argument = text.partition(" ")
        command = command.lower()
        argument = argument.strip()

        if command == "/profile":
            profile = self.store.load()
            reply = (
                "Here is everything I have stored about your learning:\n\n"
                "```json\n" + json.dumps(profile, indent=2) + "\n```"
            )
        elif command == "/reset":
            self.store.reset_progress()
            reply = (
                "Done. I cleared your concept progress and exercise history. "
                "Your goals and preferences were kept."
            )
        elif command == "/delete":
            deleted = self.store.delete()
            reply = (
                "Your learner profile has been deleted."
                if deleted
                else "There was no stored profile to delete."
            )
        elif command == "/goal" and argument:
            self.store.add_goal(argument)
            reply = "Noted. I added this learning goal: " + argument
        elif command == "/hint":
            # A requested hint escalates one level and counts towards the
            # hints-used record for this exercise.
            session.hint_level = min(session.hint_level + 1, len(prompts.HINT_LEVELS) - 1)
            session.hints_this_exercise += 1
            if session.topic:
                self.store.record_hint(session.topic)
            return self._run_learning_loop(session, "I would like a hint, please.")
        elif command == "/solution":
            session.solution_requested = True
            return self._run_learning_loop(
                session,
                "Please give me the full solution, explain the reasoning, "
                "and then give me a similar practice question.",
            )
        elif command == "/end":
            self.store.record_exercise(
                topic=session.topic or "unspecified",
                workflow=session.workflow or "practice",
                outcome="ended_by_learner",
                hints_used=session.hints_this_exercise,
            )
            self._reset_exercise_state(session)
            reply = (
                "Exercise ended and recorded. What would you like to work on "
                "next - more practice, or some debugging?"
            )
        elif command == "/help":
            reply = (
                "Commands:\n"
                "- `/profile` - show everything stored about your learning\n"
                "- `/goal <text>` - add a learning goal\n"
                "- `/hint` - get a more specific hint\n"
                "- `/solution` - ask for the full worked solution\n"
                "- `/end` - end the current exercise and record it\n"
                "- `/reset` - clear progress (keeps goals)\n"
                "- `/delete` - delete your stored profile entirely"
            )
        else:
            reply = "I did not recognise that command. Try `/help`."
        return {"reply": reply, "phase": session.phase, "error": False}
