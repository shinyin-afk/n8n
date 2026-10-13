"""The hint ladder: five rungs, from most indirect to near-solution.

Rung order (higher = more help, closer to the answer):

0. RESTATE   — rephrase the problem, check understanding, ask a question.
1. CONCEPT   — name the concept involved, ask a guiding question.
2. STRATEGY  — a general plan / step list.  No code.
3. ANALOGY   — a related-but-different example, with code.
4. SKELETON  — a near-solution with a deliberate gap to fill.

The policy (which rung to start on, how to escalate) lives in the profiler
and agent.  This module only builds the *content* for a given rung, which
keeps it deterministic and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List

from tutor.topics import Topic


class HintLevel(IntEnum):
    RESTATE = 0
    CONCEPT = 1
    STRATEGY = 2
    ANALOGY = 3
    SKELETON = 4


LEVEL_LABELS = {
    HintLevel.RESTATE: "restate & clarify",
    HintLevel.CONCEPT: "point at the concept",
    HintLevel.STRATEGY: "general strategy",
    HintLevel.ANALOGY: "analogous example",
    HintLevel.SKELETON: "near-solution",
}


@dataclass(frozen=True)
class Hint:
    level: HintLevel
    title: str
    sections: List[str] = field(default_factory=list)
    code: str | None = None

    def render_text(self) -> str:
        """Render the hint as plain text (used by the deterministic renderer)."""
        parts: List[str] = [self.title]
        parts.extend(self.sections)
        if self.code is not None:
            parts.append("```\n" + self.code.rstrip("\n") + "\n```")
        return "\n\n".join(parts)


def build_hint(topic: Topic, prompt: str, level: HintLevel) -> Hint:
    """Build a hint at the given rung for the given topic and prompt."""
    if level == HintLevel.RESTATE:
        return Hint(
            level=level,
            title="Let's make sure we understand the problem first.",
            sections=[
                "Can you restate, in one sentence, what the input is and what "
                "the output must be?",
                "What is one small example you could work through by hand?",
            ],
        )
    if level == HintLevel.CONCEPT:
        return Hint(
            level=level,
            title=f"This problem is really about {topic.label}.",
            sections=[topic.concept_question],
        )
    if level == HintLevel.STRATEGY:
        steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(topic.plan_steps))
        return Hint(
            level=level,
            title="Here is a general plan.  Try to fill in each step yourself.",
            sections=[steps],
        )
    if level == HintLevel.ANALOGY:
        return Hint(
            level=level,
            title="Here is a related example (not your answer) to show the idea.",
            sections=[topic.analogy],
            code=_analogy_code(topic),
        )
    if level == HintLevel.SKELETON:
        return Hint(
            level=level,
            title="Almost there.  Complete the gap marked TODO.",
            sections=["This is a skeleton.  Fill in the missing part and "
                      "explain to yourself why it works."],
            code=topic.skeleton,
        )
    raise ValueError(f"unknown hint level: {level}")


def _analogy_code(topic: Topic) -> str:
    """Return the code for the analogy rung, or a generic prompt if absent."""
    if topic.analogy:
        # The analogy text is prose; provide a light code illustration by
        # reusing the skeleton as a scaffold with a note.  Most topics supply
        # a skeleton that doubles as a readable illustration.
        return topic.skeleton
    return "# work the related example here by hand\n"
