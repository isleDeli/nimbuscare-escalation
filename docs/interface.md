# Interface contract (written by lead, 2026-10-11)

Builder implements this; evaluator and writer rely on it. Builder may add fields, never remove or rename them.

## Run

```
./run.sh                                   # provided conversation, readable per-turn trace
./run.sh --json                            # same, machine-readable
./run.sh --conversation <file.txt> --fixtures <file.json> [--json]
```

Defaults: `data/transcript-dana-whitfield-2026-10-05.txt`, `data/fixtures.json`,
`data/policy-bil-pol-014.md`, `data/kb-billing-credits.md`.
Python 3 standard library only. No network, no API key, no installs.

## Conversation file

Same format as the provided transcript: header lines (`Date:`, `Account Number:`, `Plan: ... — $X/month recurring charge`),
then `[HH:MM] Customer (Name): text` and optional `[HH:MM] Agent (Name): text` lines.
The agent replies to every Customer line. Existing Agent lines are the human agent's original replies: shown for comparison, never used as evidence.

## Fixtures file (stands in for the account system and the NOC ticket lookup)

```json
{
  "accounts": {
    "NMB-7745213": {
      "card_last4": "4471", "pin": "0000",
      "monthly_recurring_charge": 225.00,
      "goodwill_credits_last_12_months": 0.00,
      "resolved_disputes": [],            // list of "YYYY-MM-DD" resolution dates
      "fraud_flags": []
    }
  },
  "noc_tickets": [
    {"id": "OUT-58823", "account": "NMB-7745213",
     "start": "2026-09-10T06:00", "end": "2026-09-21T06:00"}
  ]
}
```

## `--json` output

```json
{
  "conversation": "<path>",
  "turns": [
    {
      "turn": 1,
      "time": "14:02",
      "customer": "<customer text>",
      "intent": "<short label>",
      "decision": "answer | clarify | escalate | decline",
      "governing_policy": ["Rule 3"],            // rule ids from the policy; [] if none applies
      "rejected_policy": [{"id": "Rule 2", "why": "..."}],
      "retrieved": [{"id": "KB-1004", "title": "...", "score": 0.0}],   // top results, best first
      "driving_article": "KB-1004",              // null when no article supports a reply
      "evidence": ["<quoted sentence(s) the reply rests on>"],
      "computed": {"credit": 82.50},             // any numbers or dates worked out; {} if none
      "escalate_to": null,                       // e.g. "Tier 2 Billing Specialist"
      "reason": "<one sentence: why this decision>",
      "reply": "<text sent to the customer>"
    }
  ]
}
```

Decisions:
- `answer`: the reply is fully supported by quoted evidence.
- `clarify`: the agent needs information from the customer first (identity, dates, line item).
- `escalate`: policy requires a human (Rule 4 / Rule 5), or the documents do not support an answer to an in-scope question. The reply says so plainly and makes no unsupported claim.
- `decline`: out of scope for billing (for example device protection or retention credits); the reply points to the right team.

A turn may answer the supported part and escalate the rest; then `decision` is `escalate` and the reply contains only the supported part plus the handoff.
