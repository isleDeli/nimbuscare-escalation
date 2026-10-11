# architect STATUS

## Done

- 2026-10-11 read the brief, STATE.md, policy, knowledge base, transcript, interface contract, fixtures, all of `agent/`, evaluator status and `evals/results/summary.json`
- 2026-10-11 wrote `docs/architecture.md` (under 120 lines, no code)
- 2026-10-11 folded in lead-8: unseeded retrieval is now the first change, the no-ticket and Rule 5 points are recorded as settled, `guards` and rule-plus-figure escalation replies are in the change list

## Next

- lead: bring the three decisions to the human with the document
- builder: on approval, work the Change list in the order given under Risks (retrieval first)

## NEEDS HUMAN

- [ ] Decision 1: language model in the loop? a) offline rule-based only, b) model in the loop, c) rule-based plus optional model mode. recommend: a
- [ ] Decision 2: Dana's tax and surcharge question. a) quote KB-1004 "recurring plan charge only" and hand the tax-adjustment part to Tier 2, b) answer in full that taxes are not reduced, c) hand off the whole question. recommend: a
- [ ] Decision 3: outage with a ticket that fails Rule 3 (4 hours or less, or after 30 days). a) explain the Rule 2 ceiling and remaining allowance, promise no amount, escalate only if the ask exceeds the allowance, b) always escalate, c) offer the remaining Rule 2 allowance. recommend: a

## Log

- 2026-10-11 started on lead-6
- 2026-10-11 not read: individual case files in `evals/cases/` beyond one fixtures file, and the per-case result files; the failure list in `summary.json` was used instead
- 2026-10-11 lead-8 received and folded in
- 2026-10-11 document written; handed back to lead
