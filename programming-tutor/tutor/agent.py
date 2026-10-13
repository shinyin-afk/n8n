"""The tutor agent: ties memory, profiling, the hint ladder, and rendering.

The flow of :meth:`TutorAgent.respond`:

1. Detect a direct "give me the answer" request and gently redirect it.
2. Classify the prompt's topic.
3. Estimate the learner's capability from their history.
4. Choose a rung: the capability-based starting rung, or an escalation if the
   learner signals they are still stuck.
5. Build and render the hint, then record the interaction to memory.

Outcomes (solved / stuck) are fed back through :meth:`TutorAgent.feedback`
so the profiler learns from how much help each learner actually needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from tutor.hints import HintLevel, build_hint
from tutor.llm import Renderer, TemplateRenderer
from tutor.memory import LearnerMemory
from tutor.profiler import (
    describe,
    estimate_capability,
    start_hint_level,
    terminology_score,
)
from tutor.topics import classify_topic


_ANSWER_REQUEST_PHRASES = [
    "just give me the code", "give me the answer", "just the answer",
    "write the code", "solve it for me", "full solution", "complete code",
    "do it for me", "write the whole", "give me the solution", "answer for me",
    "paste the code",
]

_STUCK_PHRASES = [
    "still stuck", "still lost", "doesn't work", "not working", "didn't work",
    "still confused", "no idea", "help again", "still not", "i'm stuck",
    "im stuck", "can't figure", "cant figure", "still can't", "still cant",
]


@dataclass
class Response:
    message: str
    kind: str  # "question" | "followup" | "answer_request"
    topic: str
    hint_level: Optional[int]
    capability: float
    band: str


def _is_answer_request(prompt: str) -> bool:
    low = prompt.lower()
    return any(phrase in low for phrase in _ANSWER_REQUEST_PHRASES)


def _is_stuck(prompt: str) -> bool:
    low = prompt.lower()
    return any(phrase in low for phrase in _STUCK_PHRASES)


class TutorAgent:
    def __init__(self, memory: LearnerMemory, renderer: Optional[Renderer] = None):
        self.memory = memory
        self.renderer = renderer or TemplateRenderer()

    def respond(self, learner_id: str, prompt: str) -> Response:
        learner = self.memory.get_or_create(learner_id)
        prompt = prompt.strip()
        topic = classify_topic(prompt)
        term = terminology_score(prompt)
        capability = estimate_capability(learner["interactions"])

        answer_request = _is_answer_request(prompt)
        stuck = _is_stuck(prompt)
        previous = learner["interactions"][-1] if learner["interactions"] else None
        previous_level = previous["hint_level"] if previous else None

        if answer_request:
            level = HintLevel.CONCEPT
            kind = "answer_request"
        elif stuck and previous_level is not None:
            level = HintLevel(min(int(previous_level) + 1, int(HintLevel.SKELETON)))
            kind = "followup"
        else:
            level = start_hint_level(capability.overall)
            kind = "question"

        hint = build_hint(topic, prompt, level)
        body = self.renderer.render(hint, prompt)
        if answer_request:
            body = (
                "I won't hand over the full answer — the struggle is where the "
                "learning happens.  Here's a hint to get you unstuck instead:\n\n"
                + body
            )

        self.memory.record_interaction(
            learner_id,
            {
                "prompt": prompt,
                "topic": topic.key,
                "complexity": topic.complexity,
                "terminology": term,
                "hint_level": int(level),
                "kind": kind,
                "outcome": None,
            },
        )

        return Response(
            message=body,
            kind=kind,
            topic=topic.label,
            hint_level=int(level),
            capability=capability.overall,
            band=describe(capability.overall),
        )

    def feedback(self, learner_id: str, outcome: str) -> bool:
        """Record 'solved' or 'stuck' on the learner's last interaction."""
        return self.memory.set_outcome(learner_id, outcome)

    def profile(self, learner_id: str) -> Optional[Dict[str, object]]:
        learner = self.memory.get(learner_id)
        if not learner:
            return None
        interactions: List[dict] = learner["interactions"]
        capability = estimate_capability(interactions)
        return {
            "interactions": len(interactions),
            "capability": round(capability.overall, 3),
            "band": describe(capability.overall),
            "confidence": round(capability.confidence, 3),
            "topics": {k: round(v, 3) for k, v in capability.topics.items()},
        }
