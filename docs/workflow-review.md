# Workflow review

Reviewed October 11, 2026. Scope: local Python workflow, policy, knowledge base, handoff generation, and evaluation suite. No application code changed.

The workflow does **not** reliably escalate whenever it is unsure. It handles several documented policy thresholds well, but uncertainty, unfamiliar wording, incomplete account data, and multiple requests can bypass escalation. It is an offline prototype: no actual customer transfer occurs.

## Validation

`python3 evals/score.py`: 179/182 checks, 16/17 cases pass; exit status 1. Case 17 routes a tablet protection request to Billing instead of Device Protection. The source restrictions pass all four checks. Additional direct calls to `respond()` used the default account, conversation date 2026-10-05, and fresh state per scenario. The examples below describe observed output unless identified as a code inspection finding.

## Findings, ordered by priority

### 1. Critical: escalation is a note, not a delivered handoff

`agent/__main__.py` constructs and prints `handoff_notes`; `agent/handoff.py` formats them. There is no queue submission, case ID, delivery acknowledgment, retry, ownership, or human acceptance. Replies nevertheless say the specialist reviews the request and the question is passed on.

Required change: add a real handoff adapter with confirmed submission, case ID, destination, and status. Report submission failures honestly, retain the unresolved request, and provide an available contact route. Until connected, describe the output as a prepared handoff rather than a completed transfer.

### 2. High: customer-reported fraud does not trigger specialist review

Location: `agent/state.py:137`–144; `agent/respond.py` general-credit branch.

Input: “My card ends 4471. I dispute an unauthorized $20 charge on invoice dated October 1, 2026 for a SIM not registered on my account.”

Observed: `answer`, “This amount qualifies within the $75.00 limit, so no further approval is needed.” Review is based on fixture fraud flags and resolved disputes, and ignores the fraud indicator in the customer message. This conflicts with Rules 4d and 5.

Required change: distinguish suspected fraud from confirmed billing errors. Route suspected fraud for human review before credit eligibility statements; preserve the customer's report as an allegation for investigation.

### 3. High: customer allegations are treated as confirmed billing errors; missing history becomes zero

Locations: `agent/state.py:81`–103,132–133; `agent/policy.py:62`; `agent/respond.py` general-credit branch.

Input: “My card ends 4471. I was charged twice on invoice dated October 1, 2026, a duplicate $20 charge.”

Observed: the agent says the amount qualifies and no further approval is needed. No invoice ledger or error-verification result exists in the workflow, although Rule 2 requires an error confirmed by the agent. Removing `goodwill_credits_last_12_months` from the fixture yields the same approval because the code defaults to zero. Missing dispute and fraud fields likewise read as no recorded risk.

Required change: require authoritative error verification and complete, valid account history before personalized eligibility decisions. Unknown values must remain unknown and trigger specialist review if they cannot be obtained. General policy explanations can still be answered as such.

### 4. High: short problem statements are mistaken for acknowledgments

Location: `agent/respond.py:20`–25, acknowledgment branch.

After verification, “Payment missing”, “My payment disappeared.” and “SIM stolen” each produce `answer` and “You're welcome.” The broad five-word heuristic runs before issue handling.

Required change: restrict acknowledgments to a small set of explicit conversational phrases. Treat other short statements as potential problems; clarify once when useful, or route to a human when the problem is unclear or requires investigation.

### 5. High: explicit human requests and stalled clarification do not escalate

Locations: `agent/respond.py:20`–60 and missing-details branch. No clarification retry counter or human-request intent exists.

Input after verification: “Please transfer me to a human specialist.”

Observed: asks for a disputed charge instead. Subsequent “I do not have those details” and “I still cannot provide that information” keep producing requests for the same billing details.

Required change: honor explicit human requests immediately, including before verification using a restricted handoff without account disclosure. Escalate when the customer cannot provide required information or clarification stops making progress. Use a configurable retry limit, such as two unsuccessful attempts, rather than an unlimited loop.

### 6. High: mixed requests can silently drop the unsupported portion

Location: `agent/respond.py:question_types` and `respond`.

Input: “My card ends 4471. I was charged twice on invoice dated October 1, 2026, a duplicate $20 charge. Can you refund it and arrange a payment extension?”

Observed: answers the credit question only, with no acknowledgment or escalation of the payment-extension request. The splitter recognizes only a limited set of question labels; it does not verify that the entire request is covered.

Required change: track each customer request independently. Every request needs an answer, clarification, or human route. An unsupported component must trigger handoff even when another component is answerable. Preserve every unresolved component and destination in the handoff rather than only one overall decision.

### 7. High: partial ticket overlap is accepted as complete outage confirmation

Location: `agent/state.py:109`–118.

Input: “My card ends 4471. Service outage September 20 to September 30, 2026. I dispute the $225 charge.”

Observed: calculates $82.50 for the existing September 10–21 ticket and says no specialist approval is needed. The ticket overlaps the reported period but does not cover it. The lookup selects the first overlap; it does not resolve conflicting dates, multiple tickets, affected lines, or service address coverage.

Required change: validate the incident, address, affected lines, and requested interval against authoritative outage records. Ask about discrepancies and escalate unresolved conflicts or ambiguous ticket matches before quoting a definitive credit.

### 8. Medium: deadline intent bypasses missing-ticket escalation

Location: `agent/respond.py` outage deadline branch, `elif state.start`.

Input: “My card ends 4471. Service outage September 25 to September 27, 2026, $225 charge. What is the deadline?”

Observed: `answer`, stating no ticket could be verified and no specific deadline can be confirmed; no handoff is created. The equivalent credit request escalates. General deadline information is supported, but the unresolved customer outage lacks a consistent route to review.

Required change: separate supported general information from unresolved eligibility. Retain the general explanation and escalate the account-specific missing-ticket issue consistently across question types.

### 9. Medium: stale incident state can cross account and issue boundaries

Location: `agent/state.py:55`–58, `agent/handoff.py:build_notes`.

Code inspection: an account switch clears verification and the account record but retains amount, statement, incident dates, error/dispute flags, monthly charge fallback, and `credit_answered`. Handoff notes combine final state with the full chat and favor the header account number. The README explicitly limits the prototype to one account per chat, but this boundary is not enforced.

Required change: reject or hand off account switching, or create completely separate account-scoped state and notes. On a new incident, reset prior incident data and preserve provenance. Test that no previous account's facts, eligibility, or identity status appear in another account's summary.

### 10. Medium: operational failures exit without a customer recovery path

Location: `agent/__main__.py` exception handling; fixture and policy parsing.

Code inspection: missing files, invalid JSON, and some malformed fields terminate through `parser.error`; other type errors can escape. There is no specialist fallback. Policy effective dates are not validated, and source quotes prove that text exists but do not prove every customer-specific claim is justified.

Required change: validate source versions and account/ticket schemas at startup. In a connected workflow, lookup failures, unavailable policy, malformed evidence, and conflicting facts must stop automated eligibility decisions and produce an actionable human route. Check support for each claim after combining reply parts.

## Acceptance criteria for reliable escalation

- Explicit requests for a human always create an appropriate handoff.
- Unknown intent, unsupported requests, conflicting facts, suspected fraud, missing authoritative data, and stalled clarification cannot produce an unconditional credit eligibility statement.
- Every component of a mixed request remains tracked until resolved or accepted by the relevant human team.
- A handoff is only described as sent after the receiving system acknowledges delivery; failures remain visible and recoverable.
- Specialists receive the customer question, verified facts and their sources, unknowns, escalation reason, prior attempts, and commitments already made, scoped to the correct account and incident.
- Add regression coverage for every finding above, alongside account-switch isolation, failed verification retries, lookup timeouts, multiple tickets, missing or malformed history, non-English input, and contradictory customer corrections. Include unfamiliar wording written independently of the implementation.

Fix the fraud/verification gates and acknowledgment heuristic first, then add consistent uncertainty escalation and request tracking. Connecting and verifying delivery is necessary before this prototype can ensure that a human actually receives unresolved customer problems.
