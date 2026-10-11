# DESIGNER brief

Project root: this repository (`nimbuscare-escalation/`). Hackathon, hard deadline 2026-10-11 15:00. Your spec is due 15 minutes after you start. The human must approve it before any more code is written, so it must be readable in 3 minutes.

## What to build

`docs/design/trace.md`: how the agent's output looks when a reviewer runs `./run.sh` in a terminal. No product code.

The reviewer's test, from the hackathon: they "run it against the provided conversation and see, per turn, which policy and which retrieved article drove each reply", and can see that the agent "explicitly declines or escalates rather than answering when the retrieved evidence does not support a response." The human adds that it must be visibly "a workflow that will not make the same mistakes."

## Why it matters

The trace is the whole interface. A reviewer who has to hunt for the governing rule or the escalation will mark it down. A first version exists: run `./run.sh` to see it and improve on it.

## Decisions to return to the lead (do not ask the human yourself)

At the top of the spec under `## Decisions for the human`, multiple choice with your recommendation:
1. Terminal trace only, versus terminal trace plus a single self-contained HTML report file the run writes (`out/trace.html`, no server, no installs). Say what each costs in build time.
2. Whether the human agent's original replies from the transcript are shown beside the agent's, for comparison.

## Build steps

1. Read `docs/interface.md` (the fields available per turn, plus an added `guards` list of mistakes avoided), the transcript in `data/`, and run `./run.sh` and `./run.sh --json`.
2. Write `docs/design/trace.md`, at most 100 lines:
   - Decisions for the human (above)
   - One turn drawn exactly as it should print, in a code block, using real content from the provided conversation: once for an `answer` turn (the $82.50 credit) and once for the `escalate` turn (taxes and surcharges)
   - Order of information in a turn and why: customer text, decision, governing rule and rejected rule, retrieved articles with the driving one marked, quoted evidence, numbers, mistake avoided, reply
   - How the four decisions (`answer`, `clarify`, `escalate`, `decline`) are told apart at a glance: labels first, colour second; must stay readable with colour off (piped output, `NO_COLOR`) and at 80 columns
   - The end-of-run summary: one line per turn with time, decision, rule, article
   - Wording rules for the customer-facing reply when handing off: say what is confirmed, say what is not covered, say who decides next; never apologise for the policy or guess
3. Standard library Python only: no colour or table libraries. Plain ANSI codes at most.

## Rules

- Write only inside `docs/design/` and `work/designer/STATUS.md` (sections: Done, Next, NEEDS HUMAN, Log). Do not change code, `data/`, `evals/` or `STATE.md`.
- Nothing external is pushed, published or sent.

## Start here

Run `./run.sh`, then write the spec. Final report to lead: the decisions for the human and the two example turns.
