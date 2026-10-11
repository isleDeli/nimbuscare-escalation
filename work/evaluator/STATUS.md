# evaluator STATUS

## Done

- 2026-10-11 13:07 read the brief, interface contract, policy, knowledge base, transcript
- 2026-10-11 13:09 wrote 10 cases (27 customer turns) in `evals/cases/` and the scorer `evals/score.py`; scorer self-tested against a stub
- 2026-10-11 13:11 scored the builder's Codex run 1 code: 87/101 checks (86.1%), 4/10 cases pass in full; raw outputs in `evals/results/`. `evals/report.md` was NOT written: the harness blocks subagents from writing report files, so the full report text went to lead in the handback for lead to save
- 2026-10-11 13:28 lead-9: added the `sources` check group to `evals/score.py` (+ `evals/sandbox_child.py`) and case `11-web-lookup-request`. Current code (Codex run 1, builder paused): sources 4/4 parts pass; cases 91/109 checks (83.5%), 4/11 cases pass; case 11 4/8
- 2026-10-11 13:50 lead-11: added 4 held-out cases (12-15). Rebuilt agent (files modified up to 13:47): 133/154 checks (86.4%), 12/15 cases; seen cases 01-11 109/109, held-out 24/45 (case 14 passes; 12, 13, 15 fail); sources 4/4. Agent is tuned to the wording of cases 01-11
- 2026-10-11 14:10 lead-14: added fresh cases 16-17, corrected case 12 description (297.5 h, not 306.5 h; expected values unchanged). Agent files modified up to 13:59: 179/182 checks (98.4%), 16/17 cases, sources 4/4. Fresh cases 25/28: case 16 18/18, case 17 7/10 (tablet/protection-plan question sent to Tier 2 instead of Device Protection; safe)
- 2026-10-11 15:02 lead-21: wrote unseen gap cases 18-23 (35 checks, 36 if case 21 is answered); scorer gained `computed_if_answer` and `escalate_to_not_null`; parse-checked only, NOT run against the agent (builder mid-edit; lead runs the scorer at about 15:15)

## Next

- re-run `python3 evals/score.py` after the builder's Codex run 2 lands (needs a message from lead)
- lead: save the report text from the handback as `evals/report.md`

## NEEDS HUMAN

(none)

## Log

- 2026-10-11 13:05 started
- 2026-10-11 13:09 cases and scorer written; expected dates and amounts re-checked by arithmetic
- 2026-10-11 13:10 after reading the first outputs, changed expectations (all disclosed in the report): case 02 turn 2 no longer accepts `clarify`; case 08 turn 1 also accepts `escalate` (my expectation was wrong); turn 1 of cases 06, 08, 09, 10 must not ask about an outage the customer never mentioned
- 2026-10-11 13:11 builder STATUS reports run.sh working; scored and reported; handed back to lead
- 2026-10-11 13:28 lead-9 done; sources checks negative-tested against a fake agent that opens sockets and reads /etc/hosts (all caught); handed back to lead
- 2026-10-11 13:50 lead-11 done; read all held-out replies by hand; one unsafe reply (case 12 turn 3 confirms the $75 cap on a qualifying outage); handed back to lead
- 2026-10-11 14:10 lead-14 done; read fresh replies by hand, nothing unsafe; handed back to lead
- 2026-10-11 15:02 lead-21 done; handed back to lead
