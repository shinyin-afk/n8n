"""Interactive REPL for the tutor agent.

Commands (typed instead of a normal prompt):

  :learner <id>   switch to a different learner (creates if new)
  :profile        show the current learner's capability profile
  :stuck          tell the tutor the last hint was not enough
  :solved         tell the tutor the learner finished
  :verbose        toggle the metadata line (topic, rung, capability)
  :quit           exit

Run with:  python -m tutor.cli [--memory FILE] [--learner ID]
"""

from __future__ import annotations

import argparse
import os
import sys

from tutor.agent import TutorAgent
from tutor.hints import LEVEL_LABELS
from tutor.llm import make_renderer
from tutor.memory import LearnerMemory


def _read_multiline(first: str) -> str:
    """Read a prompt; a trailing blank line continues reading."""
    lines = [first]
    while True:
        line = input("... ")
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Hint-based programming tutor")
    parser.add_argument(
        "--memory",
        default=os.environ.get("TUTOR_MEMORY", os.path.expanduser("~/.tutor-memory.json")),
        help="path to the JSON memory file",
    )
    parser.add_argument("--learner", default="default", help="learner id")
    args = parser.parse_args(argv)

    memory = LearnerMemory(args.memory)
    agent = TutorAgent(memory, renderer=make_renderer())
    learner_id = args.learner
    verbose = False

    print("Hint-based programming tutor (type :help for commands, :quit to exit)")
    print(f"learner: {learner_id}  |  memory: {args.memory}")

    while True:
        try:
            raw = input(f"\n[{learner_id}] > ").rstrip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if raw == "":
            continue

        if raw.startswith(":"):
            cmd, _, arg = raw.partition(" ")
            cmd = cmd.lower()
            if cmd in (":quit", ":q", ":exit"):
                break
            if cmd == ":help":
                print(":learner <id> | :profile | :stuck | :solved | :verbose | :quit")
                continue
            if cmd == ":learner":
                learner_id = arg.strip() or learner_id
                print(f"now talking to learner: {learner_id}")
                continue
            if cmd == ":profile":
                profile = agent.profile(learner_id)
                if profile is None:
                    print("no history for this learner yet")
                else:
                    print(profile)
                continue
            if cmd == ":stuck":
                if agent.feedback(learner_id, "stuck"):
                    print("noted: still stuck.  the next hint will go one rung deeper.")
                else:
                    print("nothing to mark stuck yet")
                continue
            if cmd == ":solved":
                if agent.feedback(learner_id, "solved"):
                    print("nice!  recorded as solved.")
                else:
                    print("nothing to mark solved yet")
                continue
            if cmd == ":verbose":
                verbose = not verbose
                print(f"verbose: {verbose}")
                continue
            print(f"unknown command: {cmd}")
            continue

        response = agent.respond(learner_id, raw)
        if verbose:
            level_label = LEVEL_LABELS[response.hint_level] if response.hint_level is not None else "-"
            print(
                f"  [topic: {response.topic} | rung: {level_label} | "
                f"capability: {response.band} ({response.capability:.2f})]"
            )
        print(response.message)

    memory.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
