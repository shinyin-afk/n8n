"""Learner profile store.

Persists a per-learner JSON profile: goals, preferences, per-concept
evidence and misconceptions, and exercise history. No LLM calls here.

Design rules (see docs/DESIGN.md section 5):
- Understanding is tracked per concept via dated evidence entries.
- `independent_success` is distinguished from `solved_with_hints`.
- Misconceptions are tentative: two independent successes on a concept
  clear its misconceptions.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

PROFILE_VERSION = 1

# Evidence kinds recorded after each evaluated learner response.
EVIDENCE_INDEPENDENT = "independent_success"
EVIDENCE_WITH_HINTS = "solved_with_hints"
EVIDENCE_STRUGGLE = "struggled"

# Number of independent successes that clear a recorded misconception.
SUCCESSES_TO_CLEAR_MISCONCEPTION = 2


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_profile() -> dict:
    return {
        "version": PROFILE_VERSION,
        "created_at": _now(),
        "goals": [],
        "preferences": {},
        "concepts": {},
        "exercises": [],
    }


class ProfileStore:
    """Load/save/update a learner profile stored as a JSON file."""

    def __init__(self, path: str) -> None:
        self.path = path

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def load(self) -> dict:
        if not self.exists():
            return empty_profile()
        try:
            with open(self.path, encoding="utf-8") as handle:
                profile = json.load(handle)
        except (json.JSONDecodeError, OSError):
            # A corrupt or unreadable profile must not break a session.
            return empty_profile()
        base = empty_profile()
        base.update({k: v for k, v in profile.items() if k in base})
        return base

    def save(self, profile: dict) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(profile, handle, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.path)

    def delete(self) -> bool:
        """Delete the profile file entirely. Returns True if one existed."""
        if self.exists():
            os.remove(self.path)
            return True
        return False

    def reset_progress(self) -> dict:
        """Clear concepts and exercise history; keep goals and preferences."""
        profile = self.load()
        profile["concepts"] = {}
        profile["exercises"] = []
        self.save(profile)
        return profile

    # --- update operations -------------------------------------------------

    def add_goal(self, goal: str) -> dict:
        profile = self.load()
        if goal and goal not in profile["goals"]:
            profile["goals"].append(goal)
            self.save(profile)
        return profile

    def set_preference(self, key: str, value: str) -> dict:
        profile = self.load()
        profile["preferences"][key] = value
        self.save(profile)
        return profile

    def record_evidence(self, concept: str, kind: str, note: str) -> dict:
        """Append one dated evidence entry for a concept.

        Independent successes also count towards clearing misconceptions.
        """
        profile = self.load()
        entry = profile["concepts"].setdefault(
            concept, {"evidence": [], "misconceptions": [], "hints_used": 0}
        )
        entry["evidence"].append({"date": _today(), "kind": kind, "note": note})
        if kind == EVIDENCE_INDEPENDENT:
            independent = sum(
                1 for e in entry["evidence"] if e["kind"] == EVIDENCE_INDEPENDENT
            )
            if independent >= SUCCESSES_TO_CLEAR_MISCONCEPTION:
                entry["misconceptions"] = []
        self.save(profile)
        return profile

    def record_misconception(self, concept: str, description: str) -> dict:
        profile = self.load()
        entry = profile["concepts"].setdefault(
            concept, {"evidence": [], "misconceptions": [], "hints_used": 0}
        )
        if description and description not in entry["misconceptions"]:
            entry["misconceptions"].append(description)
        self.save(profile)
        return profile


    def record_hint(self, concept: str) -> dict:
        profile = self.load()
        entry = profile["concepts"].setdefault(
            concept, {"evidence": [], "misconceptions": [], "hints_used": 0}
        )
        entry["hints_used"] += 1
        self.save(profile)
        return profile

    def record_exercise(
        self, topic: str, workflow: str, outcome: str, hints_used: int
    ) -> dict:
        profile = self.load()
        profile["exercises"].append(
            {
                "date": _today(),
                "topic": topic,
                "workflow": workflow,
                "outcome": outcome,
                "hints_used": hints_used,
            }
        )
        self.save(profile)
        return profile

    def correct(self, field: str, value) -> dict:
        """Learner-facing correction of a top-level field.

        Allowed fields: goals, preferences, concepts, exercises. The value
        must already be valid JSON-compatible data.
        """
        allowed = {"goals", "preferences", "concepts", "exercises"}
        if field not in allowed:
            raise ValueError(f"Cannot correct field {field!r}. Allowed: {sorted(allowed)}")
        profile = self.load()
        profile[field] = value
        self.save(profile)
        return profile

    def summarize(self) -> dict:
        """Compact per-concept summary used to adapt prompts."""
        profile = self.load()
        concepts = {}
        for name, entry in profile["concepts"].items():
            independent = sum(
                1 for e in entry["evidence"] if e["kind"] == EVIDENCE_INDEPENDENT
            )
            with_hints = sum(
                1 for e in entry["evidence"] if e["kind"] == EVIDENCE_WITH_HINTS
            )
            struggles = sum(1 for e in entry["evidence"] if e["kind"] == EVIDENCE_STRUGGLE)
            concepts[name] = {
                "independent_successes": independent,
                "successes_with_hints": with_hints,
                "struggles": struggles,
                "misconceptions": list(entry["misconceptions"]),
                "hints_used": entry["hints_used"],
            }
        return {
            "goals": list(profile["goals"]),
            "preferences": dict(profile["preferences"]),
            "concepts": concepts,
            "exercise_count": len(profile["exercises"]),
        }
