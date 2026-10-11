# Trace design: what `./run.sh` prints (designer, 2026-10-11)
Direction: one fixed block per customer turn, read top to bottom as an audit record: question, decision, rule, article, quote, numbers, mistake avoided, reply. Every row has a fixed left label, so the governing rule and the handoff sit in the same place on every turn. Plain ASCII layout, 78 columns, colour only on the decision tag.

## Decisions for the human
1. **Output format.** a) Terminal trace only: no extra build time. b) Terminal plus `out/trace.html` written by the run: about 25 to 30 minutes of builder time plus a second layout to specify and check, taken from the time reserved for the evaluator's six fixes. c) Terminal plus a plain-text copy `out/trace.txt`: about 3 minutes. **Recommend a.** The reviewer's test is "run it and see"; the terminal already passes it.
2. **Show the human agent's original reply under each turn?** a) Yes, as a last row marked "not evidence", cut to two lines: no extra build time, the data is already loaded. b) No. **Recommend a.** The original replies are all "let me check"; beside them the agent's cited answer is the proof that the workflow closes what the human left open.
3. **Rewrite the handoff reply to the Confirmed / Not covered / Next form shown in turn 5?** a) Yes, about 5 minutes. b) Keep the current single sentence. **Recommend a.** The replies drawn below are target wording, not today's output.

## Answer turn, exactly as printed (turn 4, the $82.50 credit against the $75 question)
```
== TURN 4/6  14:09 =============================================== [ANSWER] ==
CUSTOMER  Okay, but isn't your refund limit only $75? I saw something like
          that in your terms once. So you can only give me $75 back for
          this, right?
DECISION  ANSWER - The verified outage meets Rule 3 eligibility and stays
          below Rule 4b approval thresholds.
RULE      > Rule 3   Service-Outage Credit Policy                   GOVERNS
          x Rule 2   rejected: The specific service-outage policy is
                     separate from the $75 goodwill ceiling; Rule 4a does
                     not apply.
ARTICLES  > KB-1004  Service-Outage Credits: Eligibility & Cre...  21.5  DROVE
            KB-1002  Refund Eligibility & Goodwill Credit Limits   13.8
            KB-1010  Mid-Cycle Plan Change Proration               12.3
EVIDENCE  Rule 3   "...is not counted against, and not capped by, the $75.00
                   General Refund/Goodwill Credit Limit."
          KB-1004  "...is not limited by, the standard $75.00 goodwill
                   credit ceiling described in KB-1002."
NUMBERS   credit $82.50 = $225.00 / 30 x 11 full days   ticket OUT-58823
AVOIDED   ! Did not cap an outage credit at the $75.00 goodwill limit.
REPLY     No. The $75.00 limit is for general billing-error credits and does
          not cap an outage credit. Your outage credit is $82.50 for 11 full
          days without service.
ORIGINAL  (human agent, not evidence) That's a fair thing to ask — I don't
          want to just quote you $75 without double-checking whether...
```
## Escalate turn, exactly as printed (turn 5, taxes and surcharges)
```
== TURN 5/6  14:11 ============================================= [ESCALATE] ==
CUSTOMER  Sure, no rush. While you're looking into that — does whatever
          credit I end up getting also reduce the taxes and regulatory
          surcharges I paid during those eleven days, or is it only applied
          against the plan charge itself?
DECISION  ESCALATE -> Tier 2 Billing Specialist (evidence gap) - The
          documents do not cover whether taxes or regulatory surcharges are
          adjusted.
RULE      > Rule 3   Service-Outage Credit Policy    GOVERNS confirmed part
ARTICLES  > KB-1004  Service-Outage Credits: Eligibility & Cre...  16.8  DROVE
            KB-1003  Understanding Your Nimbus Wireless Bill       15.5
            KB-1010  Mid-Cycle Plan Change Proration               14.1
EVIDENCE  KB-1004  "This credit applies to the recurring plan charge only..."
          GAP      no rule or retrieved article answers the escalated part
NUMBERS   credit $82.50 = $225.00 / 30 x 11 full days   ticket OUT-58823
AVOIDED   ! Did not guess whether taxes and surcharges are reduced.
REPLY     Confirmed: your $82.50 outage credit is calculated on and applied
          to the $225.00 recurring plan charge. Not covered: our policy and
          help articles do not say whether the taxes and regulatory
          surcharges for those 11 days are adjusted as well. Next: a Tier 2
          Billing Specialist decides that; I have passed the question on
          with outage ticket OUT-58823.
ORIGINAL  (human agent, not evidence) Good question, and I'd rather check
          than guess on that one too — I'll look into whether that's...
```
## Row order and why
Rows always print in this order; a row with nothing to show is omitted, except RULE and ARTICLES, which print `- none` so an absence is visible. Builder needs, beyond `docs/interface.md`: `guards` (already requested), a source id per evidence quote, rule short titles read from the policy headings, and `escalation_basis` (`policy` or `evidence_gap`).
1. **Header**: turn n/total, time, decision tag at the right edge. A reviewer scrolling sees the outcome before reading anything. Then **CUSTOMER**, verbatim. Everything below is judged against it.
2. **DECISION**: label, `-> escalate_to` if set, then `reason`. On an escalation add `(policy)` when a Rule 4 or Rule 5 condition forced it, `(evidence gap)` when the documents are silent.
3. **RULE**: `>` governing rule with its short title and `GOVERNS`; `x` each rejected rule with its `why`. The rejected line is where "the narrow exception" becomes visible.
4. **ARTICLES**: top three retrieved, best first, score to one decimal; the driving one marked `>` and `DROVE`. If no article supports a reply, none is marked.
5. **EVIDENCE**: at most two quotes, one from the governing rule and one from the driving article, each prefixed by its source id and trimmed with `...` to two lines (full text stays in `--json`). On an evidence-gap turn the last line is `GAP`.
6. **NUMBERS**: only figures the reply uses, with the working shown (`credit $82.50 = $225.00 / 30 x 11 full days`, `deadline 2026-10-21 = 2026-09-21 + 30 days`).
7. **AVOIDED**: one `!` line per entry in `guards`.
8. **REPLY**, then **ORIGINAL** (if decision 2 is yes): the conclusion comes last because it is only credible after its basis.

## Telling the four decisions apart
Words first, colour second. The tag is a bracketed upper-case word in the header and repeated as the first word of DECISION; the two that stop short of answering also change the DECISION row (`-> who`, or `out of scope -> team`).

| Decision | Tag | Colour on the tag only (ANSI) | Contrast, xterm palette |
|---|---|---|---|
| answer | `[ANSWER]` | black on green `30;42` | 9.7:1 |
| clarify | `[CLARIFY]` | black on cyan `30;46` | 10.6:1 |
| escalate | `[ESCALATE]` | black on yellow `30;43` | 12.3:1 |
| decline | `[DECLINE]` | bold white on red `1;97;41` | 5.8:1 |

Tags set both foreground and background, so the ratio holds on dark and light terminals (coloured text alone fails on white: green 2.2:1, yellow 1.7:1). Row labels are bold; ORIGINAL is dim (`2`). All other text uses the terminal default. No colour when stdout is not a terminal, `NO_COLOR` is set, or `TERM=dumb`; the output is then identical minus escape codes. Label column is 10 characters; wrap at 78 with `textwrap`, continuation lines indented to the text column; titles cut with `...`. Layout characters are ASCII (`= > x ! -`); quoted source text is printed as written.

## End-of-run summary
```
== SUMMARY  6 turns: 3 answer, 2 clarify, 1 escalate, 0 decline ==============
 #  TIME   DECISION   RULE    ARTICLE  MISTAKE AVOIDED
 1  14:02  CLARIFY    Rule 1  KB-1001  -
 2  14:04  CLARIFY    Rule 1  KB-1001  -
 3  14:06  ANSWER     Rule 3  KB-1004  $75.00 cap on an outage credit
 4  14:09  ANSWER     Rule 3  KB-1004  $75.00 cap on an outage credit
 5  14:11  ESCALATE   Rule 3  KB-1004  guess on taxes and surcharges
 6  14:13  ANSWER     Rule 3  KB-1004  60-day window used as the deadline
Handed to a human: turn 5 -> Tier 2 Billing Specialist (evidence gap)
```
DECISION cells take the tag colours. `-` for an empty cell. The "Handed to a human" line prints once per escalated or declined turn, or `Handed to a human: none`. MISTAKE AVOIDED is the first guard, cut to fit 78 columns.
## Reply wording when handing off
Three labelled sentences in this order: **Confirmed:** what the evidence supports, with the figure. **Not covered:** what the documents do not say, stated as a fact about the documents. **Next:** who decides (the `escalate_to` role) and what was passed on. Never apologise for the policy, never predict the specialist's answer, never promise a time, never use "should", "probably" or "usually". No internal rule numbers in any customer reply; they belong in the RULE row. A decline uses the same form with "Next:" naming the right team.

## Approved change (lead, 2026-10-11)

The human approved this spec with one change: "I want to keep the design as similar to the workflow as possible". Rows in each turn print in pipeline order from `docs/architecture.md`: CUSTOMER, ISSUE, ARTICLES, RULE, ESCALATION, EVIDENCE, NUMBERS, AVOIDED, REPLY, ORIGINAL. The decision tag stays in the turn header. Everything else above stands.
