# NimbusCare billing-support agent (prototype)

An offline, rule-based agent that replays a billing-support chat and, for each customer turn, shows which policy rule governed, which retrieved knowledge-base article drove the reply, which mistake it avoided, and whether it answered, asked for information, escalated to a human or declined. It is for a reviewer who wants to check that every reply rests on company documents, and that the agent stops when they do not support an answer.

Its only knowledge sources are `data/policy-bil-pol-014.md` (the billing policy, Rules 1 to 5) and `data/kb-billing-credits.md` (ten help articles, KB-1001 to KB-1010). No network, no language model, no installs.

## Run it

Requires Python 3 only (checked with Python 3.11). From the project root:

```
./run.sh
```

This replays the provided conversation, `data/transcript-dana-whitfield-2026-10-05.txt`, and prints one block per customer turn followed by a summary table. The output is the same on every run.

```
./run.sh --json                                           # same trace, machine-readable
./run.sh --handoff                                        # only the note for the specialist
./run.sh --conversation FILE.txt --fixtures FILE.json     # another chat and account
```

If `./run.sh` is not executable after unzipping, `python3 -m agent` from the project root does the same thing.

## What it does

- Works out the issue (outage, general billing error, or none yet) from the facts in the conversation so far, and the question type from the current turn.
- Retrieves the top three knowledge-base articles for the turn and marks the one that drove the reply.
- Picks one governing policy rule and records the rule it rejected, with the reason.
- Checks the escalation thresholds for that rule, then checks that every claim in the reply rests on a sentence quoted from the two documents.
- Makes one of four decisions: `answer`, `clarify` (needs information from the customer), `escalate` (policy requires a human, or the documents do not answer the question) or `decline` (another team's topic). It never issues a credit; it states what the policy allows.

## How to read the trace

Turn 6 of the provided conversation, copied from `./run.sh`:

```
== TURN 6/6  14:13 =============================================== [ANSWER] ==
CUSTOMER    Dana Whitfield: Sounds good. One more thing while I have you —
            how long do I actually have to submit a request like this after
            an outage gets fixed? Just want to make sure I'm not about to
            miss some deadline.
ISSUE       outage (question: deadline)
ARTICLES      KB-1001  How to File a Billing Dispute  17.1
            > KB-1004  Service-Outage Credits: Eligibility & C...  15.9  DROVE
              KB-1005  How to Request a Service-Outage Credit  15.6
RULE        > Rule 3  Service-Outage Credit Policy (Exception to R...  GOVERNS
            x Rule 1  rejected: The 60-day statement window is not the outage
                                request deadline.
            x Rule 2  rejected: The separate outage policy is not capped by
                                the general $75.00 ceiling; Rule 4a does not
                                apply.
ESCALATION  - none checked
EVIDENCE    Rule 3  "The customer requests the credit within 30 calendar days
                     of the outage's resolution date (not the billing...
            KB-1004  "To request this credit, you'll need the NOC outage
                      ticket number (agents can look this up by service...
NUMBERS     deadline 2026-10-21 = 2026-09-21 + 30 days
AVOIDED     ! 60-day window used as the deadline: blocked the statement
            window; used 30 days from 2026-09-21 to 2026-10-21
DECISION    ANSWER - Rule 3 uses 30 calendar days from resolution.
REPLY       NimbusCare agent (automated): The request window is 30 calendar
            days from outage resolution on 2026-09-21, with deadline
            2026-10-21. Your request on 2026-10-05 is in time.
ORIGINAL    Jordan R. (human agent, not evidence): That's a good one to nail
            down too. Let me pull everything together — the credit amount...
```

Rows print in the order the agent works:

| Row | Meaning |
|---|---|
| header | Turn number, time, and the decision tag |
| `CUSTOMER` | The customer's name and words, verbatim |
| `ISSUE` | Issue track and question type |
| `ARTICLES` | Top three retrieved articles with scores; `>` and `DROVE` mark the one the reply rests on. It is not always the top-ranked one: the driving article must hold the sentences the reply needs |
| `RULE` | `>` the governing rule; `x` a rejected rule and why |
| `ESCALATION` | The thresholds tested and the result |
| `EVIDENCE` | Sentences quoted from the rule and the article (cut to two lines here, in full in `--json`). `GAP` means no document answers part of the question |
| `NUMBERS` | Figures and dates the reply uses, with the working |
| `AVOIDED` | The wrong answer that was blocked on this turn |
| `DECISION`, `REPLY` | The decision with its reason, then the automated agent's text for the customer |
| `ORIGINAL` | What the human agent (named) said in the transcript. Shown for comparison, never used as evidence |

The run ends with a summary table. When any turn goes to a human, a `HANDOFF NOTE (prepared, not sent)` for the specialist prints after it, so they do not have to re-read the chat. For the provided conversation it is addressed to the Tier 2 Billing Specialist and has six parts:

| Part | Content |
|---|---|
| `CUSTOMER` | Name, account and plan |
| `DECISION NEEDED` | The customer's question, what to decide, and what is already known |
| `WHY A HUMAN` | Here: "Evidence gap: the documents do not answer this question." |
| `WHAT HAPPENED` | One line per turn |
| `ALREADY SETTLED` | Identity, ticket OUT-58823, the $82.50 credit, the 2026-10-21 deadline |
| `NOT PROMISED` | What the customer was not told, and that the agent applied nothing |

`./run.sh --handoff` prints only that note. The JSON fields are described in `docs/interface.md`; the output also has top-level `participants` (customer and human agent names) and `handoff_notes` (the same six parts per note).

## The three traps in the provided conversation

Dana Whitfield's service was out from September 10 to September 21, 2026 and she was charged the full $225.00. In the transcript the human agent leaves three questions open. The agent closes two and hands off the third.

| Turn | Question | The easy wrong answer | What the agent does |
|---|---|---|---|
| 3, 4 | How much credit? "Isn't your refund limit only $75?" | Cap the credit at the $75.00 general limit (Rule 2) | Answers. Rule 3, the outage exception, governs and Rule 2 is rejected. Credit is $82.50 = $225.00 / 30 x 11 full days, confirmed by outage ticket OUT-58823, and within the $300.00 and 30-day limits of Rule 4b, so no specialist approval is needed |
| 6 | How long do I have to request this? | Quote the 60-day dispute window (Rule 1) | Answers. Rule 3 gives 30 calendar days from the outage resolution date: 2026-09-21 + 30 days = 2026-10-21. Rules 1 and 2 are rejected |
| 5 | Does the credit also reduce the taxes and regulatory surcharges? | Guess yes or no | Escalates to a Tier 2 Billing Specialist. It confirms the one thing the documents say (KB-1004: the credit applies to the recurring plan charge only), states that the documents do not say whether those other charges are adjusted, and tells the customer a handoff note has been prepared for the specialist. The trace labels the avoided mistake `credit scope`. KB-1003 ranked first on this turn, but KB-1004 holds the supporting sentence and drove the reply |

Turns 1 and 2 are `clarify`: the agent verifies identity and asks for the outage dates before it says anything about a credit.

## How it works

The policy and the knowledge base are read once at start. Then, for each customer turn:

1. **Load and update state**: identity check, dates, line item, amount. The outage ticket is looked up from the account and any known date. The issue track is set from facts before keywords: a date that overlaps an outage ticket on the account means an outage; an amount, a bill date and an error description mean a billing error.
2. **Classify the question** from this turn's words, with the issue track taken from state. Once an outage is verified and qualifies under Rule 3, limit and deadline questions are always answered under Rule 3.
3. **Retrieve** the top three articles by keyword ranking. The query is built only from the customer's words and the conversation state; nothing chosen later may enter it.
4. **Pick the governing rule**: test Rule 3's conditions. If all pass, Rule 3 governs and Rule 2 is rejected; otherwise the reverse. One rule does the calculation, never both.
5. **Check escalation**, only for the governing rule: Rule 4a for Rule 2, Rule 4b for Rule 3, Rule 1 outside 60 days, Rule 5 for a repeat dispute or fraud flag. Some triggers apply whatever the rule: a customer-reported fraud indicator (an unauthorized charge, a SIM or device not on the account) escalates under Rule 4d and Rule 5 before any credit is stated; an explicit request for a human hands off; a clarifying question already asked once with no new information hands off instead of being asked again; an outage ticket that covers only part of the claimed dates confirms only its own period and the rest is escalated.
6. **Check evidence**: choose the driving article from the three retrieved and require a quoted sentence for every claim. Numbers and dates must come from a quote or a shown calculation. If nothing retrieved supports the reply, there is no driving article and the turn is handed off.
7. **Reply or hand off**. A handoff reply has three parts: Confirmed, Not covered, Next. A turn with one covered and one uncovered request answers the first and names the second as not covered. Handoff replies end "A handoff note has been prepared for them."; nothing is sent anywhere.

Files:

| Path | What it is |
|---|---|
| `run.sh` | Runs the agent |
| `agent/` | The code: `loaders.py`, `state.py`, `retrieval.py`, `policy.py`, `respond.py`, `handoff.py`, `render.py` |
| `data/` | The two company documents, the provided transcript, and `fixtures.json` |
| `evals/` | Test chats, the scorer `score.py`, and the evaluator's `report.md` |
| `design_memo.md` | One-page memo: which replies are grounded, the hardest policy boundary, how to measure next |
| `docs/` | `architecture.md`, `design/trace.md`, `interface.md`, `demo.md` |
| `docs/workflow-review.md` | An independent review of the escalation workflow. Since it was written: findings 2, 4, 5, 6, 7 and 8 addressed; 1 and 3 partly; 9 and 10 open |

## Tech stack

- Python 3 standard library
- Keyword ranking (BM25-style) over the ten articles; no embeddings
- Two markdown documents and one JSON fixtures file; no database
- Runs locally; no hosting, no network, no API key

## Evaluation

```
python3 evals/score.py              # all cases
python3 evals/score.py --verbose    # also print each scored reply
```

The scorer runs the agent on each chat in `evals/cases/` and compares every customer turn with that case's `expected.json` on six things: decision, governing rule, driving article, numbers, reply wording, and handoff.

Result when last run (2026-10-11 15:17). All cases pass and the scorer exits with status 0.

| Group | Checks passed | Cases passed |
|---|---|---|
| 1. Provided conversation (case 01) | 26/26 | 1/1 |
| 2. Synthetic chats visible to the builder (cases 02 to 15) | 128/128 | 14/14 |
| 3. Chats written after the first code freeze (cases 16 and 17) | 28/28 | 2/2 |
| 4. Chats written for the workflow-review findings, not read by the builder (cases 18 to 23) | 35/35 | 6/6 |
| **All cases** | **217/217 (100%)** | **23/23** |
| Sources check | 4/4 parts pass | |

How much each group proves:

1. **Case 01** is the provided conversation.
2. **Cases 02 to 15** are fourteen synthetic chats written for this project: short outages, an outage with no ticket, a credit over $300.00, late requests, duplicate-charge and promo-code disputes, a repeat dispute, retention and device credits, a late-fee waiver, and a customer asking the agent to search the web. All pass, but all were visible to the builder while fixing. Cases 12 to 15 were written as held-out chats with new wording and first scored 24/45; in one of them the agent wrongly confirmed the $75.00 limit for an outage described as "no signal". They were then used for fixes, so they no longer count as unseen.
3. **Cases 16 and 17** were written after the first code freeze. When first scored, unseen, they passed 25 of 28 checks with no unsafe reply. The three failed checks were one turn of case 17, which was then fixed (below), so case 17 no longer counts as unseen. Recognition of unfamiliar wording remains the weak point and fails towards a human rather than a wrong answer.
4. **Cases 18 to 23** were written by the evaluator after an independent review (`docs/workflow-review.md`) found escalation gaps: a charge from an unknown SIM, a request for a person, a covered request mixed with an uncovered one, a claim longer than the ticket, a deadline question with no ticket, and a short problem statement. The builder fixed the agent against these but saw only their pass/fail lines, not the chats.

The last failure, case 17 turn 3, was fixed at 15:17: a cracked tablet screen on the protection plan used to be handed to a Tier 2 Billing Specialist as "not covered"; it is now declined and pointed to the Device Protection team (KB-1009). A perfect score here means every known bug is fixed, not that the agent is finished: all 23 chats have now been used for fixes or seen by pass/fail.

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

The evaluator's full report is in `evals/report.md`.

**Sources check.** This is how the evaluation proves the agent uses only the two company documents and never the network. It has four parts and fails the run if any part fails:

1. Static scan: no network or model-client code and no URLs in `run.sh` and `agent/`.
2. Run time: every case is re-run with sockets replaced by functions that record the attempt and raise. Zero attempts, and the output is identical to the normal run.
3. Files: in that same run every file open is recorded. Knowledge is read only from the two company documents.
4. Quotes: every evidence string appears verbatim in one of the two documents, and every rule and article id in the output exists in them.

In case 11 the customer asks the agent to "google what the FCC says". The agent replies that it can only answer from Nimbus billing policy and help articles, and hands the question to a Tier 2 Billing Specialist.

## Stand-ins and limits

- **`data/fixtures.json` stands in for two real systems**: the account system (identity check, monthly charge, goodwill credits in the last 12 months, resolved disputes, fraud flags) and the NOC outage-ticket lookup. Nothing is looked up live.
- **Question types and some wording are matched from phrase lists.** Outages and billing errors are recognised from facts first, but the question type is not. Unfamiliar wording falls back to a clarifying question or a handoff to a human, which can be the wrong queue (as case 17 was before its fix). This is the main weakness.
- **Small test set**: one provided conversation plus twenty-two synthetic chats written by the same team that built the agent. All of them have now been used for fixes or seen by their pass/fail lines, so none is a truly unseen test any more.
- **Nothing is carried out, and no handoff is delivered** (review finding 1). The agent does not issue credits, open cases or send the handoff note to a queue; the note is printed and marked "prepared, not sent".
- **The customer's claim is not checked against an invoice** (review finding 3). A billing-error reply says the amount is within what a front-line agent may credit "once the error is confirmed on the invoice", but nothing confirms it. Missing credit history in the fixtures is read as $0.00.
- **The mixed-request check is a heuristic** on question sentences, so an uncovered request phrased another way can be missed.
- **Open review findings 9 and 10**: state can carry over if a chat changes account or issue, and a failure (bad file, missing data) exits with an error and no reply for the customer.
- **"SIM stolen" goes to the fraud path**, not to Device Protection.
- **Fixed scope**: one account per chat, English only, policy BIL-POL-014 and this knowledge-base excerpt only. Reply wording is fixed text, not free-form.

Next steps: deliver the handoff note to a real queue, check claims against the invoice, replace the phrase lists for question types with something less tied to wording, connect the real account and outage-ticket services, queue handoffs for Tier 2, and test on real chats with expected results written by someone outside the team.
