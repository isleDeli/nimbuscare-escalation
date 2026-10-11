# Demo script (about 2 minutes)

Setup before you start: a terminal at the project root, at least 80 columns wide, font large enough to read from the back. Run `./run.sh` once beforehand so you know where each turn sits when you scroll.

## Pitch (one paragraph)

A billing agent that sounds confident and is wrong costs money and trust. This prototype replays a real support chat and, for every customer turn, shows its working: the policy rule that governed, the help article that drove the reply, the exact sentence it quoted, and the wrong answer it avoided. When the company's documents do not answer a question, it says so and hands the question to a human. It runs offline on Python 3 with no model and no network, so the same input always gives the same, checkable output.

## 1. The problem (20 seconds)

Say: "Dana's service was out for eleven days and she was charged the full $225.00. In the original chat the human agent answers three questions with 'let me check'. Each one has an easy wrong answer: cap the credit at $75.00, quote the 60-day dispute window, or guess about taxes."

## 2. Run it (10 seconds)

Type:

```
./run.sh
```

Point at the `SOURCES` line at the top: one policy file, one knowledge-base file, `network: none`.

Say: "One command, no setup. These two documents are everything it knows."

## 3. Turn 4: the $75 trap (30 seconds)

Scroll to `== TURN 4/6`. Point at, in order:

- `CUSTOMER`: Dana Whitfield, "isn't your refund limit only $75?"
- `RULE`: `> Rule 3 ... GOVERNS` and `x Rule 2  rejected`
- `ARTICLES`: `> KB-1004 ... DROVE`
- `NUMBERS`: `credit $82.50 = $225.00 / 30 x 11 full days   ticket OUT-58823`
- `REPLY`, from "NimbusCare agent (automated)": "No. The $75.00 limit is for general billing-error credits and does not cap an outage credit."

Say: "The outage exception governs, the general limit is rejected with a reason, and the credit is $82.50. Every row is one step of the pipeline: retrieve, pick the rule, check escalation, check evidence, reply."

## 4. Turn 5: it stops when the documents stop (30 seconds)

Scroll to `== TURN 5/6`, tagged `[ESCALATE]`. Point at:

- `CUSTOMER`: does the credit also reduce taxes and regulatory surcharges?
- `EVIDENCE`: the `GAP` line, "no rule or retrieved article answers the escalated part"
- `ARTICLES`: KB-1003 ranked first but KB-1004 drove
- `AVOIDED`: "credit scope: did not infer adjustment of other charges from plan-only eligibility"
- `REPLY`: Confirmed, Not covered, Next

Say: "The documents say the credit applies to the plan charge. They do not say what happens to taxes and surcharges. So it confirms the supported part, says what is not covered, and hands the rest to a Tier 2 Billing Specialist. The top-ranked article was a general billing explainer; the one that drove the reply is the one holding the quoted sentence."

## 5. Turn 6, the summary and the handoff note (20 seconds)

Scroll to `== TURN 6/6`, then the `SUMMARY` table, then the `HANDOFF NOTE` below it. Point at:

- `RULE`: `x Rule 1  rejected: The 60-day statement window is not the outage request deadline.` (Rule 2 is rejected on this turn too)
- `NUMBERS`: `deadline 2026-10-21 = 2026-09-21 + 30 days`
- Summary line: `6 turns: 3 answer, 2 clarify, 1 escalate, 0 decline`
- `== HANDOFF NOTE (prepared, not sent) for Tier 2 Billing Specialist`: point at `DECISION NEEDED`, `ALREADY SETTLED` and `NOT PROMISED`

Say: "Thirty days from the day the outage was fixed, not sixty from the statement. Six turns: three answered, two asking for details, one handed to a human. And the specialist gets a note: the one decision needed, what is already settled, and what the customer was not promised, so nobody asks Dana to repeat herself."

## 6. The result (20 seconds)

Type:

```
python3 evals/score.py
```

Point at the `TOTAL` row and the four `[PASS]` lines under `sources check`.

Say: "214 of 217 checks, 22 of 23 chats. The provided conversation scores 26 of 26. The fourteen synthetic chats we built against all pass, but the builder could see them. So we wrote eight more that the builder did not read: 60 of 63 checks, no unsafe reply, one miss. The sources check re-runs every chat with sockets disabled and records every file opened: no network attempt, only the two company documents read, every quote verbatim."

(Numbers as of the run at 15:17 on 2026-10-11: 217/217 checks, 23/23 cases, exit status 0; earlier text here may mention one failing case, which is now fixed. Read the totals from the screen; if the scorer prints different numbers, say the ones it prints. The scorer exits with status 1 and prints a FAILURES list of three lines for case 17; that is expected.)

## 7. What is next (15 seconds)

Point at the FAILURES list.

Say: "The last miss we fixed: a cracked tablet screen on the protection plan used to go to a billing specialist; it now goes to the Device Protection team. Question types are still matched from phrase lists, so unfamiliar wording falls back to a clarifying question or a human, not to a wrong rule. Earlier today a held-out chat caught a worse version of this, a wrong answer on the $75.00 limit, and that is fixed: outages are now recognised from the ticket and dates, not from the word 'outage'. The account system and the outage-ticket lookup are a JSON file today. Next: fix that routing, connect the real services, and test on real chats."

## If asked

- "Is there a model?" No. Rules and keyword retrieval, Python 3 standard library.
- "Does it issue the credit?" No. It states what the policy allows and who decides.
- "What if I ask something it does not know?" It asks a clarifying question or escalates. That can be the wrong queue, as case 17 was before we fixed it. Case 11 in `evals/cases/` asks it to search the web; it replies that it can only answer from Nimbus policy and help articles and hands off.
- "Machine-readable output?" `./run.sh --json`; fields are in `docs/interface.md`.
- "What does the human get?" `./run.sh --handoff` prints only the note for the specialist.
