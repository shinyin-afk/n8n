# Agentic AI Programming Learning Assistant

Research prototype for *"Exploration of Agentic AI for Programming Learning
Assistance"*. A chat-based tutor that helps beginner programmers learn Python
fundamentals and debugging skills using a Socratic teaching approach: it asks
questions and gives progressive hints instead of handing out solutions.

## What it does

- **Guided practice** — breaks an exercise into small steps and coaches the
  learner through an approach, then reflects on what was learned.
- **Guided debugging** — collects code, expected vs. actual behaviour and
  error messages, then guides hypothesis → debugging step → interpretation →
  verification.
- **Learner memory** — keeps a per-concept profile (evidence of
  understanding, misconceptions, exercises, hints used, goals) in a local
  JSON file, and uses it to adapt difficulty and hint depth.
- **Learner control** — `/profile`, `/goal`, `/reset`, `/delete` commands to
  inspect, correct, or erase stored data.

See [docs/DESIGN.md](docs/DESIGN.md) for the full proposal (MVP scope,
architecture, learning loop, memory structure, acceptance criteria) and
[docs/EVALUATION.md](docs/EVALUATION.md) for the evaluation plan and test
scenarios.

## Requirements

- Python 3.11+ (standard library only — no packages to install)
- For live mode: an API key for an OpenAI-compatible Chat Completions
  endpoint (OpenAI, Azure OpenAI, Ollama, LM Studio, ...)

## Setup

```bash
cd agentic-tutor
cp .env.example .env        # then edit .env and add your key
export $(grep -v '^#' .env | xargs)   # or export the variables yourself
python3 -m app.server
```

Open <http://127.0.0.1:8000> and start chatting.

Offline mode (no API key, scripted mock responses — useful to try the UI):

```bash
MOCK_LLM=1 python3 -m app.server
```

For multiple study participants, give each a separate profile file:

```bash
PROFILE_PATH=data/participant-03.json python3 -m app.server
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LLM_API_KEY` | — | API key. Required unless `MOCK_LLM=1`. |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint. |
| `LLM_MODEL` | `gpt-4o-mini` | Model name. |
| `MOCK_LLM` | — | Set to `1` for offline mock mode. |
| `PORT` | `8000` | Server port (loopback only). |
| `PROFILE_PATH` | `data/profile.json` | Learner profile file. |

## Chat commands

| Command | Effect |
|---|---|
| `/hint` | Get a more specific hint (counts as a hint used). |
| `/solution` | Explicitly request the full worked solution. |
| `/end` | End and record the current exercise. |
| `/profile` | Show everything stored about your learning. |
| `/goal <text>` | Add a learning goal. |
| `/reset` | Clear progress (keeps goals and preferences). |
| `/delete` | Delete the stored profile entirely. |
| `/help` | List commands. |

## Example interaction (practice workflow)

> **Learner:** I need to write a function that counts vowels in a string and
> I don't know where to start.
>
> **Tutor:** Good one to practise. Before any code: if I gave you the word
> `"apple"` and a pencil, how would *you* count the vowels by hand?
>
> **Learner:** go letter by letter and keep a tally?
>
> **Tutor:** Exactly — that IS the algorithm. Which Python tool lets you
> look at each letter of a string one at a time?
>
> *(... guided steps continue; if the learner is stuck twice on the same
> step, the tutor switches to a short explanation plus a check question ...)*
>
> **Tutor:** You solved it with 2 hints. Summary: you practised loops and
> conditionals, and you traced your own code correctly at the end. Try this
> similar one on your own: count how many digits are in a string.

## Running the tests

```bash
cd agentic-tutor
python3 -m unittest discover -s tests -v
```

34 tests cover the profile store, the prompt builder/parser, the learning
loop (hint escalation, stuck policy, evidence recording, graceful API
failure), and the learner commands. All run offline.

## Limitations

- **No code execution.** Analysis is by inspection only; the assistant says
  so and never claims to have run code. Debugging verification relies on the
  learner reporting results.
- **Single agent, single language.** Python beginner concepts only.
- **Classification depends on the LLM.** The engine trusts the model's
  per-turn evaluation block; a malformed block degrades to "partial" and
  simply records less evidence. Rule-based parts (hint escalation, stuck
  policy, outcome recording) do not depend on the model.
- **In-memory sessions.** Restarting the server loses the conversation (the
  profile persists). Intended for supervised single-user study sessions.
- **Hint quality varies with the underlying model.** Fix one model for
  comparable evaluation runs.
