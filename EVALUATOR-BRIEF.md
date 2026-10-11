# EVALUATOR brief

Project root: this repository (`nimbuscare-escalation/`). Hackathon, hard deadline 2026-10-11 15:00. Your cases and scorer must be ready by 13:50; the scored report by 14:30.

## What to build

In `evals/`: a set of test conversations with expected results, a scorer `evals/score.py` (Python 3 standard library only), and a report `evals/report.md`. The contract you test against is `docs/interface.md`.

## Why it matters

The hackathon scores whether the agent "applies the policy layer that actually governs each question (including the narrow exception), and explicitly declines or escalates rather than answering when the retrieved evidence does not support a response." Your cases prove that on more than the one provided conversation, and catch an agent that is hard-coded to it.

## Decisions

None for the human. If you hit one, return it to the lead in your final report; do not ask the human.

## Build steps

1. Read `data/policy-bil-pol-014.md`, `data/kb-billing-credits.md`, the transcript in `data/`, and `docs/interface.md`.
2. Write the cases now, without waiting for the builder. Each case is a folder `evals/cases/<name>/` with `conversation.txt`, `fixtures.json` and `expected.json`. `expected.json` lists, per customer turn: `decision`, `governing_policy`, an acceptable set for `driving_article`, any `computed` numbers or dates, and phrases the reply must not contain (for example "$75" presented as the cap on an outage credit).
3. Cases to cover, 8 to 10 in total, one or two customer turns each after identity is given:
   - the provided conversation (expected results are in `BUILDER-BRIEF.md`)
   - outage of 3 hours with a ticket -> Rule 2, not Rule 3
   - outage claimed, no NOC ticket -> not Rule 3; escalate (Rule 4b)
   - long outage on an expensive plan, credit over $300.00 -> Rule 3, escalate (Rule 4b)
   - outage credit requested 45 days after resolution -> Rule 2 with the $75.00 ceiling
   - duplicate charge of $40.00 with $50.00 of goodwill credit already used -> Rule 2, escalate (Rule 4a)
   - duplicate charge of $20.00, clean history -> Rule 2, answer
   - second dispute 40 days after a resolved one -> escalate (Rule 4c / Rule 5) even for a small amount
   - retention credit or device replacement question -> decline, point to the right team (KB-1008 / KB-1009)
   - a question the documents do not cover (for example late-fee waiver) -> escalate, no invented policy
4. Write `evals/score.py`: for each case run `./run.sh --json --conversation ... --fixtures ...` from the project root, compare with `expected.json`, print a table and a total, exit non-zero on any failure. Score separately: decision, governing policy, driving article, numbers, forbidden phrases.
5. When `run.sh` exists (check `work/builder/STATUS.md`; if it is not there yet, finish the cases and wait for the lead to message you), run the scorer and write `evals/report.md`: score per case, each failure with the turn, what was expected and what came back. Check your expected values by hand against the policy before blaming the agent.

## Rules

- Report findings; do not edit `agent/`, `run.sh`, `data/` or `STATE.md`.
- Never push, publish, deploy, post or send anything external. Sample names and account numbers only, clearly made up.
- Keep `work/evaluator/STATUS.md` current (sections: Done, Next, NEEDS HUMAN, Log).

## Start here

Read the files in step 1 and write the first case. Final report to lead: number of cases, the command to run the scorer, the score if run, and every failure.
