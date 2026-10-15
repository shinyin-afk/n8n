# Evaluation Plan

Small-scale user testing plan for the prototype. Designed for 5–10
participants (beginner programmers), individual 30–45 minute sessions,
screen recording with consent.

## 1. Research questions and measures

| Question | Measure | How to collect |
|---|---|---|
| Is guidance correct and relevant? | % of tutor turns rated correct/relevant by an expert reviewer | Blind rating of session transcripts (2 raters, report agreement) |
| Does it follow the Socratic approach? | Questions-per-turn ≤ 1; solutions only after threshold/request; hint-level sequence respected | Transcript coding checklist (below) + unit tests |
| Do hints adapt to demonstrated understanding? | Hint specificity rises only after failed attempts; profile misconceptions referenced in later turns | Transcript coding + `data/profile.json` inspection |
| Can learners transfer? | Learner solves/explains a similar problem unaided after the session | Transfer task scored 0–2 (no/partial/full) |
| Learner experience and over-reliance | Post-session questionnaire (5-point Likert + free text); count of `/solution` requests and immediate hint requests without attempting | Questionnaire + command counts |

### Transcript coding checklist (per tutor turn)

1. At most one question?
2. No complete solution (unless explicitly requested or stuck threshold hit)?
3. Hint matches the engine's current hint level?
4. Reasoning acknowledged before correctness?
5. Confirmed issues vs. possible causes separated (debugging workflow)?
6. No claim of having executed code?

## 2. Representative test scenarios

Run each scenario with a fixed model and temperature 0.4. Scenarios A–E map
to the required coverage.

### A. Novice learner (guided practice)

- **Setup:** fresh profile. Participant: "I've done one week of Python."
- **Task:** "Write a function `count_vowels(text)` that returns the number
  of vowels in a string."
- **Expected tutor behaviour:** intake questions about prior knowledge;
  decomposes into steps (loop, condition, counter); one question at a time;
  summary with a similar practice question at the end.
- **Profile check:** `functions`, `for_loops`, `conditionals` entries with
  evidence; outcome recorded.

### B. Recurring misconception

- **Setup:** pre-seed the profile with misconception `"range(n) includes n"`
  under `for_loops` (or elicit it live in session 1 and re-test in session 2).
- **Task:** an exercise using `range`.
- **Expected:** tutor notices the off-by-one reasoning, addresses the known
  misconception explicitly, and records evidence. After two independent
  successes the misconception is cleared from the profile.

### C. Debugging task

- **Setup:** learner pastes:

  ```python
  def average(numbers):
      total = 0
      for n in numbers:
          total = total + n
      return total / len(numbers)

  print(average([]))
  ```

  with the `ZeroDivisionError` traceback.
- **Expected:** tutor collects expected vs. actual behaviour, separates the
  CONFIRMED issue (division by zero on empty input, visible in traceback)
  from POSSIBLE causes, guides the learner to pick a check (e.g. print
  `len(numbers)`), and asks the learner to verify the fix themselves. The
  tutor must not claim it ran the code.

### D. Learner who remains stuck

- **Setup:** participant answers "I don't know" twice on the same step.
- **Expected:** after the second stuck turn, the tutor stops asking
  questions, gives a short explanation with a small example on a different
  problem, then asks one check question (unit-tested; confirm live).
  Evidence recorded as `struggled`, not as failure of the learner.

### E. Incorrect or uncertain AI guidance

- **Setup:** evaluator deliberately follows a subtly wrong hint, or injects
  a wrong claim ("you told me list[1] is the first element") mid-session.
- **Expected:** when the learner's result contradicts the hint, the tutor
  acknowledges the mismatch, re-inspects, and corrects itself. The evaluator
  logs each occurrence; these feed the limitations section. If the model
  produces a malformed evaluation block, the session continues and simply
  records less evidence (unit-tested).

## 3. Procedure per participant

1. Consent + 3-question pre-check (loop, condition, function) — 5 min.
2. Two tasks: one practice (A or B), one debugging (C) — 25 min.
3. Transfer task: similar problem, no assistant — 5 min.
4. Questionnaire + short interview — 10 min. Include: "Did you ever just
   wait for the tutor to tell you?" (over-reliance probe).
5. Show the participant their `/profile`; offer `/delete` (withdrawal).

## 4. Success thresholds (prototype-level)

- ≥ 80% of tutor turns pass the coding checklist.
- ≥ 60% of participants solve the transfer task fully or partially.
- Zero turns claiming code execution.
- Stuck policy triggered correctly in every occurrence of scenario D.

## 5. Known limitations to report

- No code execution: verification depends on learner-reported results.
- Evaluation-block parsing is best-effort; misclassification can mis-record
  evidence (mitigation: participants can inspect and correct the profile).
- Small concept scope; unknown transfer to other languages.
- Single-session memory of conversation; profile persists but chat does not.
