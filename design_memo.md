# Design memo: NimbusCare billing-support agent

Of the six replies on the provided conversation, three are fully grounded and three are partly grounded; none states a policy fact the documents contradict.
The hardest boundary was Rule 3 against Rule 2; the next step is a claim-level audit.

## 1. Which replies are grounded in the evidence

Each sentence of `reply` (from `./run.sh --json`) was compared with that turn's `evidence` quotes. "Computed" means arithmetic on a quoted formula. Identity, the monthly charge and ticket OUT-58823 come from `data/fixtures.json`, a stand-in, not from the two documents.

| Turn | Decision | Verdict | What is not a quote |
|---|---|---|---|
| 1 | clarify | Fully grounded | Nothing: asks for the identity items KB-1001 lists |
| 2 | clarify | Partly | "Identity is verified" is a fixture fact. The quoted KB-1001 sentence asks for the disputed line item; the sentence that asks for outage dates (KB-1005) is not quoted |
| 3 | answer | Partly | 264 hours is ticket data; 11 full days and $82.50 are computed. The $300.00 and 30-day limits sentence rests on Rule 4b, shown in the ESCALATION row but not quoted in EVIDENCE |
| 4 | answer | Fully grounded | $82.50 is computed; the "$75.00 does not cap it" claim is quoted from Rule 3 and KB-1004 |
| 5 | escalate | Partly, by design | The plan-charge sentence is quoted. The rest is explicitly not answered and left to a Tier 2 Billing Specialist. The handoff note is "prepared", and marked not sent |
| 6 | answer | Fully grounded | The 30 days is quoted; the 2026-10-21 deadline and "in time" are computed from the ticket's end date and the chat date |

## 2. Hardest point in the policy hierarchy

Rule 3 (service-outage credit, a narrow exception) against Rule 2 (general $75.00 ceiling), and with it the Rule 4 arm: 4a only for Rule 2 credits, 4b for outage credits.

Our evaluation caught it breaking (`evals/report.md`): on a held-out chat a verified, qualifying outage was described as "no signal", and an earlier version confirmed the $75.00 cap. The fix: decide the governing rule from facts (a date overlapping an outage ticket) before wording, and lock the cap so it cannot be confirmed while a qualifying outage is in play.

The source text is also ambiguous: with no ticket, Rule 3 says evaluate under Rule 2 while Rule 4b says escalate. We escalate. An independent review then found escalation gaps outside the hierarchy (fraud reports, requests for a human, partial ticket overlap); these were fixed and are covered by cases 18 to 23.

## 3. Next step: a claim-level audit

Today `evals/score.py` checks the decision, governing rule, driving article, numbers, required and forbidden phrases, and that every evidence quote is verbatim. It does not check that each reply sentence is supported by those quotes; section 1 was done by hand. Build that check: split every reply into claims and label each quoted, computed from a quoted formula, or unsupported.

- Hallucination rate = unsupported claims / total claims.
- Instruction-adherence rate = turns where the governing rule, the escalation arm and the answer-or-handoff decision all match a human-labelled expectation / total turns.

Run it on real, anonymised transcripts labelled by two billing specialists, with a fresh unseen batch each release. Report both rates and the unsafe-reply count; gate releases on zero unsafe replies.

Baseline today: 217/217 checks on 23 chats, every known bug fixed; when first scored unseen, the eight chats the builder had not read gave 60/63 with no unsafe reply.

See `README.md` for how to run it and `docs/demo.md` for the 2-minute demo.
