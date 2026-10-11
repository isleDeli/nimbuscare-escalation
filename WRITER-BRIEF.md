# WRITER brief

Project root: this repository (`nimbuscare-escalation/`). Hackathon, hard deadline 2026-10-11 15:00. You have 15 minutes.

## What to build

`README.md` at the project root (replace the builder's short one) and `docs/demo.md` (a 2-minute demo script). Depends on: builder (`run.sh`, `agent/`) and evaluator (`evals/report.md`) being finished.

## Why it matters

The submission is a zip with "a run script or README at the root", and a reviewer must be able to "run it against the provided conversation and see, per turn, which policy and which retrieved article drove each reply." The README is the first thing they open.

## Decisions

None for the human. Return any question to the lead in your final report.

## Build steps

1. Run `./run.sh` and `python3 evals/score.py` yourself and read the output. Describe only what exists and works.
2. README, in this order, one screen if possible:
   - what it is, in two sentences
   - how to run it (one command, Python 3 only, no setup)
   - how to read the per-turn trace, with a real excerpt of one turn
   - the three open questions in the provided conversation and what the agent does with each: credit under the outage exception (Rule 3) rather than the $75.00 limit (Rule 2); the 30-day deadline rather than the 60-day one; the taxes and surcharges question handed to a human because the documents do not answer it
   - how it works: load, retrieve, pick the governing rule, check escalation, check evidence, reply
   - what stands in for real systems (`data/fixtures.json`) and known limits
   - how to run the evaluation, with the real score
3. `docs/demo.md`: what to type, what to point at, what to say, in order.

## Rules

- Do not change code, data or `evals/`. Do not touch `STATE.md`.
- Never push, publish, deploy, post or send anything external.
- Keep `work/writer/STATUS.md` current (sections: Done, Next, NEEDS HUMAN, Log).

## Start here

Run the two commands in step 1. Final report to lead: files written and anything in the project that did not work as described.

## Added 2026-10-11: company sources only (human request)

- Do not search the web. Describe in the README that the agent uses only the two company documents and how the evaluation proves it (the sources check in `evals/score.py`).
