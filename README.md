# AI Interview Simulator

A small, fully offline mock-interview practice CLI. It asks you behavioral
and technical interview questions, scores your typed answers with simple
heuristics, and gives you immediate, actionable feedback.

**No LLM, no API keys, no network calls.** Everything is pure Python
string/regex analysis over a local question bank (`data/questions.json`).

## How it works

Three signals are combined into a single score for each answer:

1. **Keyword coverage** - each question has a list of expected
   keywords/concepts (e.g. `situation`, `action`, `result`, `resolv*`).
   A trailing `*` matches any suffix (simple stemming), so `resolv*`
   matches "resolve", "resolved", "resolving". The score is the fraction
   of expected keywords found in your answer.
2. **STAR-structure detection** - a lexical heuristic looks for markers
   typical of **S**ituation, **T**ask, **A**ction, and **R**esult framing
   (e.g. "the situation was...", "so I decided...", "as a result...")
   plus a past-tense narrative signal, and labels the answer
   `well-structured`, `partial`, or `rambling`.
3. **Filler-word and length feedback** - counts filler words/phrases
   ("um", "like", "basically", "you know", ...) and flags answers that
   are too short to contain real substance.

These combine into an `overall_score` (0-100%) plus a short list of
concrete suggestions (missing concepts, missing STAR components, filler
words to cut, "expand your answer", etc.).

At the end of a session you get a summary: average score across all
questions, your weakest question, and a de-duplicated list of the top
suggestions from the whole session.

All of this logic lives in `interview_sim/scoring.py` and
`interview_sim/session.py` as plain functions/classes with **no
`input()`/`print()` calls**, so it can be driven programmatically (by
tests, or any other UI) with canned answer strings. The interactive
REPL that actually calls `input()` lives only in `interview_sim/cli.py`.

## Question bank

`data/questions.json` bundles 50 questions across two tracks:

- `general behavioral` (25 questions) - classic STAR-style behavioral
  questions (conflict, failure, leadership, deadlines, feedback, ...).
- `software engineering` (25 questions) - technical concept questions
  (TCP vs UDP, CAP theorem, hashing, caching, design patterns, ...) plus
  technical/behavioral hybrids (debugging a production issue, code
  review approach, technical-debt tradeoffs).

Each question is a JSON object:

```json
{
  "id": "beh-001",
  "track": "general behavioral",
  "type": "behavioral",
  "question": "Tell me about a time you handled a conflict with a coworker.",
  "keywords": ["situation", "task", "action", "result", "communicat*", "resolv*", "conflict", "compromise"]
}
```

## Running it

Requires Python 3.11+ (stdlib only, no third-party dependencies).

```bash
python3 main.py
```

You'll be asked to pick a track and how many questions to answer, then
each question is presented one at a time with immediate feedback, and a
session summary is printed at the end.

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

22 unit tests cover keyword-coverage scoring on strong vs. weak answers,
STAR-structure detection on structured vs. rambling answers, filler-word
detection, session-summary aggregation (average + weakest question),
empty/very-short answer handling, and question-bank validation
(required fields, empty keywords, duplicate ids).

A GitHub Actions workflow (`.github/workflows/tests.yml`) runs the same
suite on every push/PR against Python 3.11 and 3.12.

## Example session transcript

```
==================================================
  AI Interview Simulator (mock, offline, no LLM)
==================================================

Available tracks:
  1. general behavioral
  2. software engineering
Pick a track (number): 1
How many questions? (1-25, default 5): 2

Starting a 2-question session on 'general behavioral'.

Q1/2: Tell me about a time you handled a conflict with a coworker.
Your answer> In my previous role I faced a situation where a coworker and I
disagreed about task priorities. So I decided to set up a meeting to
communicate openly, and we found a compromise. As a result we resolved the
conflict and delivered on time.

--- Feedback for Q1 ---
Q: Tell me about a time you handled a conflict with a coworker.
Overall score: [#########################-----] 85%
Keyword coverage: 88% (matched 7/8)
STAR structure: well-structured (4/4 components detected)
Length: Your answer length (44 words) is in a reasonable range.

Q2/2: Describe a time you had to work under ambiguous or unclear instructions.
Your answer> Um, like, basically I don't know, stuff happened I guess.

--- Feedback for Q2 ---
Q: Describe a time you had to work under ambiguous or unclear instructions.
Overall score: [------------------------------] 0%
Keyword coverage: 0% (matched 0/6)
STAR structure: rambling (0/4 components detected)
Length: Your answer was quite short (10 words). Try to add more concrete detail.
Filler words detected: 4 (basically, like, stuff, um)
Suggestions:
  - Try to mention concepts like: ambigu*, clarif*, assum*, situation, action.
  - Structure your answer with a clear Situation, Task, Action, and Result.
  - Reduce filler words (found 4: basically, like, stuff, um).
  - Expand your answer with more concrete detail.

==================================================
  Session Summary
==================================================
Questions answered: 2
Average score: [#############------------------] 42%
Weakest question: "Describe a time you had to work under ambiguous or unclear
instructions." (score 0%)

Top suggestions for improvement:
  - Try to mention concepts like: ambigu*, clarif*, assum*, situation, action.
  - Structure your answer with a clear Situation, Task, Action, and Result.
  - Reduce filler words (found 4: basically, like, stuff, um).
  - Expand your answer with more concrete detail.
```

## Project layout

```
ai-interview-simulator/
├── data/questions.json          # 50-question bank (2 tracks)
├── interview_sim/
│   ├── scoring.py                # keyword coverage, STAR detection, filler/length
│   ├── session.py                # question bank loading, Session, SessionSummary
│   └── cli.py                    # input()/print() REPL wrapper only
├── tests/
│   ├── test_scoring.py
│   └── test_session.py
├── main.py                       # entry point: python main.py
└── .github/workflows/tests.yml
```

## License

MIT - see [LICENSE](LICENSE).
