# Hint-based Programming Tutor

A standalone prototype of an agentic AI tutor that **hints instead of
answering**, **remembers each learner**, and **adapts the level of help** to
what the learner has shown they can do.

No n8n dependency, no third-party packages.  It runs on plain Python 3.10+.

## What it does

1. **Hint ladder** — five rungs, from most indirect to near-solution.  The
   agent never produces a full answer on its own:

   | rung | name | what the learner gets |
   |------|------|-----------------------|
   | 0 | restate & clarify | rephrase the problem, ask a guiding question |
   | 1 | point at the concept | name the idea, ask a focused question |
   | 2 | general strategy | a step list, no code |
   | 3 | analogous example | a related-but-different example with code |
   | 4 | near-solution | a skeleton with a deliberate `TODO` gap |

2. **Memory** — every prompt, the detected topic, the rung given, and the
   outcome (solved / stuck) is persisted per learner in a JSON file.

3. **Capability profiler** — scores each learner in `[0, 1]` (and per topic)
   from signals in their history: technical vocabulary, topic complexity, and
   how much help they needed to finish.  A stronger learner starts at a more
   indirect rung; a weaker learner starts at a concrete strategy rung.

## Run it

```bash
cd programming-tutor
python -m tutor.cli                 # interactive REPL
python -m tutor.cli --learner alice # start as a named learner
```

Inside the REPL:

- type a normal question to get a hint
- `:stuck` after a hint that was not enough (the next hint goes one rung deeper)
- `:solved` after you finish (this teaches the profiler you are capable)
- `:profile` to see the current learner's capability score
- `:verbose` to toggle the metadata line (topic, rung, capability)
- `:learner <id>` to switch learner, `:quit` to exit

Try this to see the adaptive behaviour:

```text
> how do I sum a list of numbers?
> :stuck
> still stuck
> :solved
> :profile
```

A brand-new learner starts neutral (intermediate).  Learners who repeatedly
solve with little help become "advanced" and get more indirect hints; learners
who keep getting stuck drift toward "beginner" and get more concrete help.

## Tests

```bash
cd programming-tutor
python -m unittest discover -s tests -v
```

## Optional: real LLM phrasing

By default the agent renders hints with a deterministic template (no network,
no keys).  To phrase hints through an OpenAI-compatible model, set:

```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://api.openai.com/v1   # optional
export OPENAI_MODEL=gpt-4o-mini                     # optional
```

The model only *rephrases* an already-approved hint; the policy of never
revealing the answer is enforced in code, not left to the model.

## Design notes

- **Policy vs. content are separated.**  The profiler decides the rung, the
  topic knowledge base builds the content, and the renderer only phrases it.
  This keeps the "never give the answer" guarantee testable and independent of
  any model.
- **Deterministic by default.**  The whole pipeline is reproducible without an
  API key, which is what makes the unit tests meaningful.
- **Known heuristic limits.**  Terminology is a weak signal (a beginner who
  asks "what is recursion?" still types the word), so history outcomes carry
  more weight as the learner accumulates interactions.
