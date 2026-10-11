# Architecture: NimbusCare billing-support agent (prototype)

Written by architect, 2026-10-11. Needs human approval before the builder continues.

## Decisions for the human

**1. Is a language model in the loop?**
- a) Offline, rule-based only. Runs from the zip with no setup; same output every run. **(recommended)**
- b) Language model writes or checks replies. More natural wording, but the reviewer needs an API key or logged-in CLI, output varies between runs, and there is no build time left to guard it.
- c) Rule-based core plus an optional model mode. Two paths to test in 40 minutes.

Why (a): the requirement is judged on which rule and article drove each reply, and on refusing when evidence is missing. Both are decisions, not wording, and rules make them checkable.

**2. Dana's tax and surcharge question (turn 5). The only source sentence is KB-1004: "This credit applies to the recurring plan charge only".**
- a) Quote that sentence, say the documents do not say whether taxes and surcharges are adjusted, hand that part to Tier 2. **(recommended, current behaviour)**
- b) Answer in full: "plan charge only, taxes are not reduced". Reads cleaner but the second half is an inference no document states.
- c) Hand off the whole question without quoting anything.

**3. An outage with a ticket that still fails Rule 3 (4 hours or less, or requested after 30 days).** The policy sends these to Rule 2 but gives no formula for the amount.
- a) Say Rule 3 does not apply and why, state the $75.00 Rule 2 ceiling and the account's remaining allowance, promise no amount; escalate under Rule 4a only if the amount asked for exceeds the allowance. **(recommended)**
- b) Always escalate these to Tier 2.
- c) Offer the remaining Rule 2 allowance as a credit. Not supported: an unqualified outage is not a "confirmed billing error".

Already settled by the lead, listed so you can overrule: an outage claim with no NOC ticket escalates under Rule 4b; on a repeat-dispute or fraud-flagged account (Rule 5) the agent keeps gathering details and hands the credit decision to Tier 2.

## Goal

A command-line agent that replays a billing chat and, for each customer turn, shows the retrieved articles, the governing rule, the rule it rejected, the quoted evidence, and a reply or a handoff. For the hackathon reviewer, who runs `./run.sh` and reads the trace. The policy and knowledge-base files in `data/` are the only source of truth.

## Stack

- Python 3 standard library: already built, no installs on the reviewer's machine.
- Retrieval: the existing keyword ranking (BM25-style) over the 9 articles. Enough for 9 documents; no embeddings.
- Data: the two markdown files and one JSON fixtures file, read at start. No database.
- Hosting: none. Runs locally from the zip.

## Pipeline per customer turn

1. **Load** (once): split the policy into rules and the knowledge base into articles with their category line.
2. **Update state** from the turn: identity check, issue track (outage, general billing error, or none yet), dates, line item, amount, invoice date. Look up the NOC ticket from whatever dates are known, even a single date; the ticket supplies the duration.
3. **Classify the question** in two parts: the issue track comes from state, the question type comes from this turn's words (amount, limit, deadline, tax on the credit, how the bill works, other team, not covered). State wins when the words are ambiguous.
4. **Retrieve**: the query is built only from the customer's words and the conversation state (issue track terms). Nothing chosen later in the pipeline may enter the query. Keep the top 3.
5. **Choose the governing rule**: test Rule 3's three conditions. All pass: Rule 3 governs and Rule 2 is recorded as rejected with the reason. Any fails: Rule 2 governs and Rule 3 is recorded as rejected with the failed condition. One rule does the calculation; never both.
6. **Check escalation** only after step 5, and only the conditions for the governing rule: Rule 4a for Rule 2, Rule 4b for Rule 3 (including no verifiable ticket), Rule 1 outside 60 days, Rule 5 for repeat dispute or fraud on any credit decision.
7. **Pick the driving article and check evidence**: the driving article is chosen from the top 3 of step 4, the best-ranked one whose category is allowed for this issue track and which contains the sentences this reply type needs. Every claim in the reply must rest on a quoted sentence; numbers and dates must come from a quoted sentence or from `computed`. If nothing retrieved supports the reply, `driving_article` is null and the turn is handed off.
8. **Reply or hand off**: all claims supported gives `answer`; missing customer information gives `clarify` naming only the missing items; a failed step 6 or 7 gives `escalate` with the supported part, the rule and the figure that triggered it; another team's topic gives `decline`.

## Mistake guards

| Wrong answer | Blocked at | How |
|---|---|---|
| $75.00 ceiling applied to an outage credit | 5, 6 | Rule 3 governs, Rule 2 rejected; Rule 4a never tested against a Rule 3 credit |
| 60-day window quoted for an outage credit | 3, 5 | Deadline question on the outage track uses Rule 3's 30 days from resolution; Rule 1 recorded as rejected |
| Answer with no supporting evidence | 4, 7 | No retrieved article holds the needed sentence: the claim is removed and the question handed off |
| Front-line credit where Tier 2 must decide | 6 | Rule 4 and Rule 5 run before any amount is offered; the reply never says a credit is issued |
| Retention, device or proration article used for a dispute | 7 | Articles whose category is not a billing-dispute credit cannot drive a dispute or outage reply |

Each turn's trace lists the guards that fired (the `guards` field).

## Stand-ins for real systems

`data/fixtures.json` stands in for two systems: the account system (identity check, monthly charge, goodwill credits in the last 12 months, resolved disputes, fraud flags) and the NOC ticket lookup. A real deployment replaces these with the billing and NOC services, and adds what the prototype only describes: logging the case number, queueing the Tier 2 handoff, and applying the credit. The prototype never issues anything; it states what the policy allows.

## Data

- Rule and article: id, title, category, text, sentences.
- Conversation state: verified, account, issue track, outage dates, ticket, line item, amount, invoice date, review flag.
- Turn result: the fields in `docs/interface.md`, unchanged. Proposed additions: `guards` (list of guard name and what it blocked) and `issue` (the track from state).

## Keep / change / drop for the existing code

**Keep**
- `run.sh`, the command-line options, the document loader, the fixtures format, all output field names.
- The Rule 3 test and credit arithmetic in the policy module, and its ordering: governing rule first, escalation second.
- Identity check against fixtures; the keyword ranker itself.

**Change**
- Retrieval (most important): today the query has the already-chosen article's title and key terms appended, so the article only appears to be retrieved. Build the query from the turn and state alone, pick the driving article from the top 3, and hand off when none supports the reply.
- Classification: use the issue track from state before any keyword. "Prorated" on an outage track is an outage credit, not a plan change (case 05).
- Tax questions: split "does the credit reduce my taxes" (decision 2) from "how are taxes calculated", which KB-1003 answers in full (case 10).
- Ticket lookup: search by account and any one known date; stop asking the customer for an end time (case 02).
- Rule 2 reply: state the amount asked for, credits already used, the total, and whether it is within $75.00 (case 07).
- Clarify: ask only for what is missing on the current track; never mention an outage the customer did not raise (cases 06, 09, 10).
- Escalation replies: state the rule and the figure (for example the credit against $300.00, or the 12-month total against $75.00), plus any supported part. A dispute past 60 days is driven by KB-1001, not KB-1006 (case 07 turn 3).
- Rule 5 accounts: keep asking for missing details, then escalate the credit decision.
- Evidence: attach required source sentences to each reply type in place of hand-picked search words.
- Add the per-turn `guards` field and show it in the readable trace as "Mistake avoided".

**Drop**
- The two lines that seed the retrieval query with the chosen article.
- The single first-match keyword list as the only classifier.
- The one fixed clarify sentence and the one fixed escalation sentence.
- Replies that are an article sentence pasted whole with no check that it fits the question.

## Risks and open questions

- **Honest retrieval may miss, and may cost points on the provided conversation.** It scores 26/26 today with the seeded query. Once the query stops naming the answer, the right article may fall outside the top 3 and cause a handoff. Mitigation: issue-track terms in the query. If it still misses, the handoff stands and is reported; do not re-seed to recover the score.
- **Regression.** The builder re-runs the scorer after each change and reports any case 01 check that changes.
- **Keyword classification stays brittle** for phrasings outside the 10 test chats. Accepted for today; unknown questions hand off.
- **Time.** About 40 minutes of build. Order: retrieval, classification and clarify, replies, evidence, `guards`.

## Out of scope for today

- Language model, embeddings, any network call or install.
- Issuing credits, opening cases, or contacting Tier 2 for real.
- Fraud detection beyond reading the fixture flag; more than one account per chat.
- Free-form reply wording, other languages, a web interface.
- Policy versions other than BIL-POL-014 v6.2.
