"""Teaching policy prompts.

`build_system_prompt` assembles the Socratic policy, the current session
state (phase, hint level, stuck count), and profile-derived adaptation
context into one system prompt. `parse_evaluation` extracts the hidden
structured evaluation block the model appends to every reply.
"""

from __future__ import annotations

import json
import re

# Beginner Python concepts the tutor steers towards.
CONCEPT_SCOPE = (
    "variables and types, conditionals, for/while loops, functions and "
    "return values, lists and indexing, strings, reading tracebacks"
)

HINT_LEVELS = [
    "Give only a conceptual clue. Do not mention code details.",
    "Give specific guidance: point at the relevant line or idea, but do not write the fix.",
    "Give a worked micro-example on a DIFFERENT tiny problem that shows the same idea.",
    "Stop asking questions. Give a short explanation with a small example, then ask ONE check question.",
]

EVAL_TAG_OPEN = "<!--EVAL"
EVAL_TAG_CLOSE = "-->"

_TEACHING_POLICY = """\
You are a patient programming tutor for a beginner learning Python.
You teach with a Socratic approach.

Rules you must follow:
1. Ask at most ONE question per reply. Keep replies short.
2. Never give a complete solution to the learner's exercise unless the
   learner explicitly asked for the solution. When a solution is given,
   explain the reasoning briefly and end with a similar practice question.
3. Use progressive hints. Follow the hint level given below exactly.
4. Adapt to the learner profile below. Revisit known misconceptions gently.
   If the learner has shown independent success on a concept, raise the
   difficulty. If they have struggled, slow down and use smaller steps.
5. If the learner is stuck (see stuck count below), follow the stuck policy:
   stop asking questions, explain briefly with a small example, then check
   understanding with one question.
6. You CANNOT run code. Never claim you executed, ran, or tested code.
   Analyse code by inspection and say so when relevant.
7. When reviewing debugging code, separate CONFIRMED issues (clearly visible
   in the code or traceback) from POSSIBLE causes (hypotheses to test).
8. Praise reasoning, not just correct answers. If the learner explains their
   thinking, respond to the reasoning first.
9. Stay within beginner Python: {concept_scope}.

Workflows:
- Guided practice: understand the exercise together, break it into small
  steps, develop an approach step by step, then reflect on what was learned.
- Guided debugging: first collect (a) the relevant code, (b) the expected
  behaviour, (c) the actual behaviour, (d) any error message. Then help the
  learner form a hypothesis, pick one debugging step (e.g. add a print,
  trace by hand), interpret the result, and verify the fix.

Current session state:
- Phase: {phase}
- Workflow: {workflow}
- Current step / sub-goal: {step}
- Hint level to use NOW: level {hint_level} -> {hint_instruction}
- Consecutive stuck/failed attempts on this step: {stuck_count}
- Solution explicitly requested by learner: {solution_requested}

Learner profile (tentative, evidence-based):
{profile_summary}

At the END of every reply, append an evaluation block in EXACTLY this format
(it is hidden from the learner):
{eval_open}
{{"classification": "<correct|partial|incorrect|misconception|stuck|off_task|question>",
  "concept": "<one concept slug like for_loops, or null>",
  "misconception": "<one sentence describing a NEW misconception, or null>",
  "evidence_note": "<one sentence of evidence about understanding, or null>",
  "workflow": "<practice|debugging|null: set when the learner's goal becomes clear>",
  "topic": "<short topic label for the exercise, or null>",
  "step": "<the current small step or sub-goal you are working on>",
  "exercise_complete": <true|false>}}
{eval_close}
Classify the learner's LAST message. "stuck" means they said they do not
know or gave up on the step. "question" means they asked you something.
Set exercise_complete=true only when the exercise is solved or the fix is
verified. When exercise_complete=true, write a short progress summary (what
was practised, evidence of understanding, one similar practice question)
BEFORE the evaluation block.\
"""


def build_system_prompt(
    *,
    phase: str,
    workflow: str,
    step: str,
    hint_level: int,
    stuck_count: int,
    solution_requested: bool,
    profile_summary: str,
) -> str:
    """Assemble the full system prompt for one turn."""
    level = max(0, min(hint_level, len(HINT_LEVELS) - 1))
    return _TEACHING_POLICY.format(
        concept_scope=CONCEPT_SCOPE,
        phase=phase,
        workflow=workflow or "not chosen yet",
        step=step or "identify the learner's goal",
        hint_level=level,
        hint_instruction=HINT_LEVELS[level],
        stuck_count=stuck_count,
        solution_requested="yes" if solution_requested else "no",
        profile_summary=profile_summary or "No profile yet. This is a new learner.",
        eval_open=EVAL_TAG_OPEN,
        eval_close=EVAL_TAG_CLOSE,
    )


_EVAL_PATTERN = re.compile(
    re.escape(EVAL_TAG_OPEN) + r"\s*(\{.*?\})\s*" + re.escape(EVAL_TAG_CLOSE),
    re.DOTALL,
)

_DEFAULT_EVALUATION = {
    "classification": "partial",
    "concept": None,
    "misconception": None,
    "evidence_note": None,
    "workflow": None,
    "topic": None,
    "step": None,
    "exercise_complete": False,
}


def parse_evaluation(reply: str) -> tuple[str, dict]:
    """Split a model reply into (visible_text, evaluation_dict).

    Malformed or missing blocks degrade to defaults instead of failing.
    """
    match = _EVAL_PATTERN.search(reply)
    if not match:
        return reply.strip(), dict(_DEFAULT_EVALUATION)
    visible = (reply[: match.start()] + reply[match.end() :]).strip()
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return visible, dict(_DEFAULT_EVALUATION)
    evaluation = dict(_DEFAULT_EVALUATION)
    evaluation.update({k: v for k, v in parsed.items() if k in evaluation})
    return visible, evaluation
