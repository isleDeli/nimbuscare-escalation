# ARCHITECT brief

Project root: `/Users/delilahbeverly/Projects/Agents/nimbuscare-escalation`. Hackathon, hard deadline 2026-10-11 15:00. Your document is due 15 minutes after you start. The human must approve it before any more code is written, so it must be short enough to read in 3 minutes.

## What to build

`docs/architecture.md`: the technical approach for the billing-support agent. No code.

Submission requirement: "A working agent workflow that takes the provided billing-dispute policy set and knowledge-base excerpt, handles the provided multi-turn customer conversation, applies the policy layer that actually governs each question (including the narrow exception), and explicitly declines or escalates rather than answering when the retrieved evidence does not support a response. A reviewer can run it against the provided conversation and see, per turn, which policy and which retrieved article drove each reply." Delivered as `agent_prototype.zip` with a run script or README at the root.

The human adds: "it should be a prototype of a workflow that will not make the same mistakes", and the policy file and the knowledge-base excerpt in `data/` are the only source of truth.

## Why it matters

A first prototype already exists (`run.sh`, `agent/`, built before this document). It gets the provided conversation right (26/26 checks) but scores 87/101 on ten other test chats because keywords pick canned replies. Your design decides what the builder keeps and what it changes in the roughly 40 minutes of build time left.

## Decisions to return to the lead (do not ask the human yourself)

Give each as multiple choice with your recommendation, at the top of the document under `## Decisions for the human`:
1. Offline and rule-based only (runs with no setup, current approach) versus a language model in the loop (needs an API key or a logged-in CLI on the reviewer's machine) versus rule-based core with an optional model mode.
2. Anything else that changes scope. Keep it to three at most.

## Build steps

1. Read `data/policy-bil-pol-014.md`, `data/kb-billing-credits.md`, the transcript in `data/`, `docs/interface.md` (the output contract already in use), the code in `agent/`, and the evaluator's cases and raw results in `evals/cases/` and `evals/results/`.
2. Write `docs/architecture.md`, at most 120 lines:
   - Decisions for the human (above)
   - The pipeline per customer turn, as a numbered list or a small diagram: load documents, track conversation state, classify the question from state first, retrieve, choose the governing rule (specific beats general, never blend), check escalation, check that quoted evidence supports each claim, reply or hand off
   - The mistake guards: each wrong answer the workflow must block and the step that blocks it ($75.00 ceiling on an outage credit; 60-day window quoted for an outage credit; answering without supporting evidence; front-line credit where Tier 2 must decide; retention, device or proration article used for a dispute)
   - What stands in for real systems (`data/fixtures.json`) and what a real deployment would replace
   - Keep / change / drop for the existing code, as a short list the builder can act on, covering the evaluator failures: "prorated" routed to the plan-change article (case 05); any tax question escalated with the outage reply (case 10); ticket not looked up from a date (case 02); goodwill reply never states the amount (case 07); one clarify question for everything; escalation replies with no reason
   - Out of scope for today
3. Do not change `docs/interface.md` field names; you may propose added fields.

## Rules

- Write only `docs/architecture.md` and `work/architect/STATUS.md` (sections: Done, Next, NEEDS HUMAN, Log). No code. Do not touch `STATE.md`.
- Standard library Python 3 is the default stack unless decision 1 changes it. Nothing external is pushed, published or sent.

## Start here

Read the files in step 1, then write the document. Final report to lead: the decisions for the human, and the keep / change / drop list.
