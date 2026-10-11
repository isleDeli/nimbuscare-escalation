# BUILDER brief

Project root: this repository (`nimbuscare-escalation/`). Hackathon, hard deadline 2026-10-11 15:00. Your code must run end to end by 13:50 and be finished by 14:15.

## What to build

A runnable billing-support agent, Python 3 standard library only, at the project root: `run.sh`, a package `agent/`, `data/fixtures.json`, and a 15-line `README.md` (the writer expands it later). The contract is `docs/interface.md`: follow it exactly.

Submission requirement (from the hackathon): "A working agent workflow that takes the provided billing-dispute policy set and knowledge-base excerpt, handles the provided multi-turn customer conversation, applies the policy layer that actually governs each question (including the narrow exception), and explicitly declines or escalates rather than answering when the retrieved evidence does not support a response. A reviewer can run it against the provided conversation and see, per turn, which policy and which retrieved article drove each reply."

## Why it matters

A reviewer will unzip it and run one command with no setup. So: deterministic, offline, no API key. What they score is the per-turn trace: which rule governed, which article was retrieved, and a clear handoff when the documents do not support an answer.

## Decisions

None for the human. If you hit one, do not ask the human: finish what you can and return the question to the lead in your final report.

## Build steps

1. Loaders: parse `data/policy-bil-pol-014.md` into Rule 1..5 and `data/kb-billing-credits.md` into KB-1001..1010 (id, title, category, text). Parse the transcript per `docs/interface.md`. Text comes from the files, not from strings in code.
2. Retrieval: stdlib TF-IDF or BM25 over articles, queried with the customer turn plus known conversation facts. Return top 3 with scores.
3. Conversation state across turns: identity verified, disputed line item, outage dates, NOC ticket (looked up in fixtures by account and dates), account history.
4. Policy layer: pick the governing rule before any calculation. The more specific rule governs; never blend two rules. Outage with a verified ticket, over 4 consecutive hours, requested within 30 days of resolution -> Rule 3 (the exception to Rule 2), credit = (monthly recurring charge / 30) x full days without service. Otherwise Rule 2 with the $75.00 rolling 12-month ceiling. Record the rule you rejected and why.
5. Escalation: Rule 4a only for Rule 2 credits; Rule 4b for outage credits (over $300.00, over 30 days, ticket not verifiable); Rule 4c / Rule 5 repeat dispute within 90 days; fraud flags. Dispute outside the 60-day window (Rule 1) needs Tier 2.
6. Evidence check: a reply may only state what a quoted sentence from a rule or article supports. If nothing retrieved supports the question, the decision is `escalate` (in scope) or `decline` (other team: KB-1008 retention, KB-1009 device protection) and the reply says so plainly.
7. Output: readable per-turn trace by default, JSON with `--json`. Show governing rule, rejected rule, retrieved articles with scores, driving article, quoted evidence, numbers, decision, reply.
8. Run it on the provided conversation and compare with the expected results below. Then make sure it is not hard-coded: change the fixture (3-hour outage, no ticket, a prior dispute 40 days ago) and check the decision changes.

## Expected results on the provided conversation (customer turns)

- 14:02 dispute opened: `clarify`, ask for identity (Rule 1, KB-1001).
- 14:04 account and card: verified against fixtures; `clarify`, ask for dates and line item (KB-1001).
- 14:06 dates and $225.00 charge: ticket OUT-58823 found, Rule 3 governs, 11 full days, credit $82.50, no escalation (under $300.00 and 30 days), within both time limits; `answer` (KB-1004 / KB-1005).
- 14:09 "isn't the limit $75?": `answer`, no; Rule 3 is not capped by Rule 2, and Rule 4a does not apply (KB-1004 / KB-1006). Rejected: Rule 2.
- 14:11 taxes and surcharges: the documents only say the credit applies to the recurring plan charge (KB-1004); nothing says whether taxes or surcharges are adjusted. `escalate` to a Tier 2 Billing Specialist, stating only the supported part. KB-1003 may be retrieved but does not answer it.
- 14:13 deadline: `answer`, 30 calendar days from the resolution date, so 2026-10-21; this request (2026-10-05) is in time. Rejected: Rule 1's 60 days from statement date.

## Rules

- You normally delegate to the Codex CLI. If Codex is not producing working code within 5 minutes, write the code directly.
- Never push, publish, deploy, post or send anything external. No secrets or personal data in files beyond the sample data provided.
- Edit only inside the project root; do not touch `STATE.md`, the briefs, `evals/` or the three source files in `data/`.
- Keep `work/builder/STATUS.md` current (sections: Done, Next, NEEDS HUMAN, Log).

## Start here

Read `docs/interface.md` and the three files in `data/`, then build step 1. Final report to lead: what runs, the exact command, the `--json` decisions per turn, anything unfinished.

## Added 2026-10-11: company sources only (human request)

- The agent's only knowledge is `data/policy-bil-pol-014.md` and `data/kb-billing-credits.md`. No web search, no network calls, no model calls, no facts written into code that are not in those files.
- Every `evidence` quote must be verbatim from one of the two documents. The evaluator's scorer checks this, scans `agent/` for network code, and runs the agent with the network blocked.
- Show it in the trace: a header line naming the two source files and "network: none", and a customer asking for an outside lookup gets a reply that the agent answers only from Nimbus policy and help articles.
- You (the builder) and Codex also do not search the web for this task.
