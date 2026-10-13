"""Capability estimation from a learner's interaction history.

The profiler turns a learner's past prompts and outcomes into a single score
in ``[0, 1]`` (0 = beginner, 1 = advanced) plus per-topic scores.  A higher
score means the learner gets *more indirect* hints and is trusted to bridge
bigger gaps on their own.

Signals used (all documented as heuristic):

* **terminology** — presence of precise technical vocabulary in the prompt.
* **complexity** — how hard the topic is (from the topic knowledge base).
* **outcome** — solving with little help raises the score; needing many
  escalations ("still stuck") lowers it.

Known limitation: a beginner who *asks* "what is recursion?" still uses the
word "recursion", so terminology is only a weak positive signal, never a
strong one.  The history outcome signals dominate over time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from tutor.hints import HintLevel


# Precise technical vocabulary that weakly signals experience.  Matches are
# substring-based and case-insensitive.
_TECH_TERMS: List[str] = [
    "complexity", "big o", "o(n)", "o(log", "o(1)", "memoization", "cache",
    "closure", "decorator", "generator", "lambda", "polymorphism",
    "inheritance", "interface", "serialize", "race condition", "deadlock",
    "mutex", "atomic", "async", "transaction", "normalization", "schema",
    "pointer", "stack", "heap", "algorithm", "data structure", "binary",
    "linked list", "deque", "dynamic programming", "dependency injection",
    "garbage collection", "immutable", "tail call", "recursion",
]


def terminology_score(text: str) -> float:
    """Return a 0..1 score for how technical the prompt's vocabulary is."""
    low = text.lower()
    hits = sum(1 for term in _TECH_TERMS if term in low)
    return min(1.0, hits / 5.0)


@dataclass
class Capability:
    overall: float
    confidence: float
    topics: Dict[str, float] = field(default_factory=dict)


def _interaction_score(interaction: dict) -> float:
    """Score one interaction as a 0..1 estimate of competence shown in it."""
    score = 0.5
    score += 0.2 * float(interaction.get("terminology", 0.0))
    score += 0.2 * float(interaction.get("complexity", 0.5))

    outcome = interaction.get("outcome")
    level = int(interaction.get("hint_level", 0))
    if outcome == "solved":
        # Solving after little help is a strong positive signal.
        if level <= 1:
            score += 0.15
        elif level == 2:
            score += 0.05
        elif level == 3:
            score += 0.0
        else:
            score -= 0.05
    elif outcome == "stuck":
        score -= 0.15
    # "answer_request" and "open" are neutral here.

    return max(0.0, min(1.0, score))


def _confidence(n: int) -> float:
    """Ramp from 0 to 1 as the number of interactions grows to 5."""
    return min(1.0, n / 5.0)


def _shrink(mean: float, confidence: float) -> float:
    """Blend a mean toward the neutral 0.5 when evidence is thin."""
    return 0.5 + confidence * (mean - 0.5)


def estimate_capability(interactions: List[dict]) -> Capability:
    """Estimate overall and per-topic capability from a list of interactions."""
    if not interactions:
        return Capability(overall=0.5, confidence=0.0, topics={})

    by_topic: Dict[str, List[dict]] = {}
    for item in interactions:
        by_topic.setdefault(item.get("topic", "general"), []).append(item)

    topic_scores: Dict[str, float] = {}
    for topic, items in by_topic.items():
        mean = sum(_interaction_score(x) for x in items) / len(items)
        topic_scores[topic] = _shrink(mean, _confidence(len(items)))

    overall = sum(topic_scores.values()) / len(topic_scores)
    return Capability(
        overall=overall,
        confidence=_confidence(len(interactions)),
        topics=topic_scores,
    )


def start_hint_level(score: float) -> HintLevel:
    """Map capability to the first rung of the hint ladder.

    Higher capability -> more indirect start (lower rung number), because a
    strong learner is trusted to self-diagnose.  A weaker learner starts at a
    more concrete rung (a general strategy) so they are not left lost.
    """
    if score < 0.35:
        return HintLevel.STRATEGY  # beginner: a concrete plan, no code
    if score < 0.65:
        return HintLevel.CONCEPT    # intermediate: name the idea
    return HintLevel.RESTATE        # advanced: challenge them to self-diagnose


def describe(score: float) -> str:
    """Return a human band name for a capability score."""
    if score < 0.35:
        return "beginner"
    if score < 0.65:
        return "intermediate"
    return "advanced"
