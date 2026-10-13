"""Hint-based programming tutor: a standalone, testable prototype.

Three headline behaviours:

* **Hint-focused** — a five-rung hint ladder, never a full answer.
* **Memory** — every prompt, topic, rung, and outcome is stored per learner.
* **Capability-aware** — a profiler scores each learner and picks how
  indirect each hint should be.
"""

from tutor.agent import TutorAgent
from tutor.hints import HintLevel

__all__ = ["TutorAgent", "HintLevel"]
__version__ = "0.1.0"
