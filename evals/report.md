# Evaluation report: NimbusCare billing agent

Final run: 2026-10-11 14:01, on the frozen code (agent files last modified 13:59).
Assembled by the lead from the evaluator's results. The agent is offline and deterministic, so the numbers below reproduce exactly.

    python3 evals/score.py            # add --verbose to print every reply, --case 17 for one case

Raw outputs are in `evals/results/<case>.json`, the tally in `evals/results/summary.json`.
As of 15:17 every case passes and the scorer exits zero; the sections from 14:01 below are kept as the record of that run.

## Final score, 15:17 (supersedes the 14:01 numbers below)

**217 of 217 checks pass. 23 of 23 cases pass in full. Sources check: 4 of 4 parts pass.**
The last failure, case 17 turn 3 (a device-protection request sent to Tier 2 Billing), was fixed at 15:17; it now
declines to the Device Protection team from KB-1009. Case 17 was unseen when it failed (25/28 on cases 16-17) and was
fixed after being seen, so no case is a truly unseen test any more. A perfect score means every known bug is fixed.

What changed after the 14:01 run:

- 14:17: the output gained speaker names and a HANDOFF NOTE for the specialist (rendering only).
- 14:33: an ad-hoc chat outside the test set showed two misses, both fixed: a request for lost-income
  compensation got the credit answer repeated instead of a handoff, and a deadline question asked in
  the same turn as the cap question was ignored.
- 15:07: findings from an independent review (`docs/workflow-review.md`) were addressed: customer-reported
  fraud now escalates (finding 2); an explicit request for a human, or a clarifying question that stalls,
  hands off (5); mixed requests name the uncovered part (6); a ticket covering only part of the claimed
  dates confirms only its own period (7); a deadline question with no ticket escalates (8); short problem
  statements are not treated as thanks (4); handoff wording now says a note was "prepared, not sent" (1, wording only).
- Still open from that review: no real handoff delivery (1); a customer's claim is answered without an
  invoice check and missing credit history is read as $0.00 (3, wording only); state carried across
  accounts (9); failure recovery (10).

| group | cases | checks | how independent |
|---|---|---|---|
| Provided conversation | 01 | 26/26 | The hackathon's own input; decisions unchanged by every later fix. |
| Synthetic, seen by the builder | 02-15 | 128/128 | Visible to the builder while fixing. |
| Fresh, written after the 13:59 freeze | 16-17 | 28/28 | First scored unseen at 25/28; case 17 turn 3 then fixed. |
| Written for the review findings | 18-23 | 35/35 | Written by the evaluator in parallel with the fixes; the builder did not read them but saw their pass/fail lines when running the scorer. |

The 14:01 sections below are kept as the record of that run; cases 18-23 are not in its tables.

## Bugs fixed before submission

Every bug below was found by this project's own evaluation or review, then fixed and re-scored.

| Bug | Found by | Fixed |
|---|---|---|
| The driving article was chosen by keyword and then made to look retrieved | builder's code review, 13:11 | 13:47 |
| Keyword-triggered canned replies on six test chats | evaluator, first score 87/101 | 13:47 |
| The $75.00 cap was confirmed on a qualifying outage described as "no signal" | held-out case 12 | 13:59 |
| Outages and promo-code errors in unfamiliar wording were handed off as "not covered" | held-out cases 12, 13, 15 | 13:59 |
| A lost-income compensation request got the credit answer repeated instead of a handoff | ad-hoc chat | 14:33 |
| A deadline question asked with the cap question was ignored | ad-hoc chat | 14:33 |
| Customer-reported fraud got a front-line answer | workflow review, finding 2 | 15:07 |
| Requests for a human and stalled clarifying questions did not hand off | workflow review, finding 5 | 15:07 |
| The uncovered part of a mixed request was dropped | workflow review, finding 6 | 15:07 |
| A ticket covering part of the claimed dates was accepted for all of them | workflow review, finding 7 | 15:07 |
| A deadline question skipped the missing-ticket handoff | workflow review, finding 8 | 15:07 |
| Short problem statements were treated as "thanks" | workflow review, finding 4 | 15:07 |
| Handoff wording claimed the question was "passed on" | workflow review, finding 1 (wording) | 15:07 |
| A device-protection request went to Tier 2 Billing instead of the Device Protection team | fresh case 17 | 15:17 |

Not fixed: see "Stand-ins and limits" in the README.

## Score at 14:01 (17 cases)

**179 of 182 checks pass (98.4%). 16 of 17 cases pass in full. Sources check: 4 of 4 parts pass.**

| check | passed | what it checks |
|---|---|---|
| decision | 47/48 | answer / clarify / escalate / decline |
| policy | 28/28 | governing rule(s), including rules that must not be listed |
| article | 31/32 | driving article in the accepted set (null where nothing supports a reply) |
| numbers | 12/12 | credit, full days, deadline, rolling total |
| phrases | 37/37 | reply has no forbidden claim and has the required fact |
| handoff | 24/25 | Tier 2 named on escalation, right team named on decline, no handoff on answers |

## How far to trust the score

The 17 cases are not equally strong evidence.

| group | cases | checks | how independent |
|---|---|---|---|
| Provided conversation | 01 | 26/26 | The hackathon's own input. |
| Synthetic, seen by the builder | 02-11 | 83/83 | The builder could read these while fixing. |
| Written as held-out, then used for fixes | 12-15 | 45/45 | First scored 24/45, with one unsafe reply. Fixed afterwards, so no longer unseen. |
| Fresh, written after the code was frozen | 16-17 | 25/28 | Never seen by the builder. The only untainted number. |

On the only two cases the agent has never seen it passed 25 of 28 checks with no unsafe reply. Its one miss was a device-protection question sent to Tier 2 instead of the right team. The policy logic and the hand-off-when-unsure behaviour can be trusted; recognition of unfamiliar wording is the remaining weak point, and it fails towards a human rather than a wrong answer.

## The provided conversation (case 01)

| turn | customer | decision | governing rule | driving article | result |
|---|---|---|---|---|---|
| 1 | disputes the charge after an outage | clarify | Rule 1 | KB-1001 | asks for identity |
| 2 | account and card | clarify | Rule 1 | KB-1001 | verified; asks for dates and charge |
| 3 | dates and the $225.00 charge | answer | Rule 3 (Rule 2 rejected) | KB-1005 | ticket OUT-58823, 11 full days, credit $82.50 |
| 4 | "isn't the limit $75?" | answer | Rule 3 (Rule 2 rejected) | KB-1004 | no; the $75.00 limit does not cap an outage credit |
| 5 | taxes and surcharges | escalate | Rule 3 | KB-1004 | states "recurring plan charge only"; the rest goes to a Tier 2 Billing Specialist (evidence gap) |
| 6 | deadline | answer | Rule 3 (Rules 1 and 2 rejected) | KB-1004 | 30 days from resolution: 2026-10-21; request is in time |

## Sources check (company documents only)

| part | result | detail |
|---|---|---|
| 1. No network code | PASS | `run.sh` and every file under `agent/` scanned for network, process and model-client use: no hits |
| 2. No network at run time | PASS | all 17 cases re-run with sockets disabled: no attempt recorded, output identical |
| 3. Only company documents read | PASS | knowledge read only from `data/policy-bil-pol-014.md` and `data/kb-billing-credits.md` |
| 4. Every quote is real | PASS | every evidence string is verbatim in one of the two documents; every rule and article id exists |

The check was itself tested against a throwaway agent that opened sockets, read an outside file and invented quotes; all were caught.

## The one failure at 14:01 (fixed later, see above)

**Case 17, turn 3.** "My tablet's screen cracked ... I pay for the protection plan ... sort out a replacement."

- Expected: `decline`, driven by KB-1009, pointing to the Device Protection team.
- Actual: `escalate` to a Tier 2 Billing Specialist, no article, "Not covered: These documents do not address this question."
- Safe, but wrong: the customer goes to the wrong queue and is told the documents are silent when KB-1009 covers it. Cause: "tablet" and "protection plan" are not in the phrases the agent recognises as a device request.

Not fixed on purpose: fixing it would use up the last unseen case.

## What the evaluation found along the way

1. **First version (13:11): 87/101.** Keyword-triggered canned replies; the driving article was chosen by keyword and then made to look retrieved.
2. **Rebuilt to the approved architecture (13:47): 109/109** on the 11 cases the builder had seen.
3. **Held-out cases 12-15 (13:50): 24/45.** One unsafe reply: on a verified, qualifying outage described as "no signal", the agent confirmed the $75.00 cap. Other misses were needless handoffs ("lost signal", "stopped working", a promo code not applied).
4. **Fix (13:59): 154/154.** Outages and billing errors recognised from facts (a date overlapping an outage ticket; an amount plus a bill date plus an error description), and a lock so the $75.00 cap cannot be confirmed while a qualifying outage is in play.
5. **Fresh cases 16-17 (14:01): 25/28**, nothing unsafe.

## Known limits

- Question types and some wording are matched from phrase lists. Unfamiliar wording falls back to a clarifying question or a Tier 2 handoff.
- The agent quotes only what that turn's retrieval returned. In case 14 turn 3 the "recurring plan charge only" sentence is left out of a handoff because KB-1004 was not in the top 3 for that question.
- Minor wording: some clarifying questions are long, and one reply states the outage as "380.417 hours".
- Not covered by any case: fraud flags (Rule 4d), PIN in place of card digits, a total-bill complaint with no line item, a customer pressing the agent to skip an escalation.
- Policy readings that could be scored either way: an outage with no ticket escalates under Rule 4b; an outage that fails Rule 3 treats the disputed charge as the amount asked for under Rule 2.
- One provided conversation plus 16 synthetic chats written by the same team. Account and outage-ticket data are stand-ins in `fixtures.json`.
