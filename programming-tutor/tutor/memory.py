"""Persistent per-learner memory, backed by a single JSON file.

The file has this shape::

    {
      "version": 1,
      "learners": {
        "<learner_id>": {
          "created_at": "<iso-8601>",
          "interactions": [
            {
              "ts": "<iso-8601>",
              "prompt": "...",
              "topic": "recursion",
              "complexity": 0.7,
              "terminology": 0.2,
              "hint_level": 1,
              "kind": "question | followup | answer_request",
              "outcome": null | "solved" | "stuck"
            }
          ]
        }
      }
    }

Writes are atomic (temp file + ``os.replace``) so a crash mid-write never
corrupts the store.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List

_SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LearnerMemory:
    def __init__(self, path: str):
        self.path = path
        self._data: Dict[str, Any] = {"version": _SCHEMA_VERSION, "learners": {}}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict) and isinstance(loaded.get("learners"), dict):
            self._data = loaded
            self._data.setdefault("version", _SCHEMA_VERSION)

    def save(self) -> None:
        directory = os.path.dirname(os.path.abspath(self.path)) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def get(self, learner_id: str) -> Dict[str, Any] | None:
        return self._data["learners"].get(learner_id)

    def get_or_create(self, learner_id: str) -> Dict[str, Any]:
        if learner_id not in self._data["learners"]:
            self._data["learners"][learner_id] = {
                "created_at": _now_iso(),
                "interactions": [],
            }
            self.save()
        return self._data["learners"][learner_id]

    def list_learners(self) -> List[str]:
        return sorted(self._data["learners"].keys())

    def interactions(self, learner_id: str) -> List[Dict[str, Any]]:
        learner = self.get(learner_id)
        return list(learner["interactions"]) if learner else []

    def record_interaction(self, learner_id: str, interaction: Dict[str, Any]) -> None:
        learner = self.get_or_create(learner_id)
        record = {"ts": _now_iso(), **interaction}
        learner["interactions"].append(record)
        self.save()

    def set_outcome(self, learner_id: str, outcome: str) -> bool:
        """Set the outcome on the most recent interaction.  Returns False if none."""
        learner = self.get(learner_id)
        if not learner or not learner["interactions"]:
            return False
        learner["interactions"][-1]["outcome"] = outcome
        self.save()
        return True
