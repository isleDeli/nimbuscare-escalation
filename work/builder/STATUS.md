# builder STATUS

## Done
- 2026-10-11 13:11 ./run.sh and ./run.sh --json work end to end on the provided conversation (Codex run 1)
- 2026-10-11 13:40 rebuilt to docs/architecture.md and docs/design/trace.md (Codex runs 3 and 4): honest retrieval (query = customer words + state topic words only; driving article picked from the retrieved top 3), state-first classification, Rule 3 / Rule 2 choice before any figure, escalation checks, verbatim evidence with source ids, `guards`, pipeline-order trace with summary
- 2026-10-11 13:44 polish and generalisation (Codex runs 5 and 6) plus four small hand fixes in agent/respond.py
- 2026-10-11 13:47 `python3 evals/score.py` -> 109/109 on cases 01-11, sources PASS
- 2026-10-11 13:59 FINAL after lead-13 (held-out cases 12-15): checks passed: 154/154 (100.0%), 15/15 cases, sources check: PASS (4/4 parts). Facts-first outage and billing-error recognition, Rule 3 lock on limit and deadline questions, multi-question turns, evidence restricted to retrieved articles and governing rules. Deterministic, no trace line over 78 columns, agent/__pycache__ deleted.

## State of the code
- Runnable and finished for this round. Files: run.sh, agent/ (8 modules), data/fixtures.json, README.md (about 22 lines, for the writer to expand).
- Provided conversation: clarify, clarify, answer (Rule 3, $82.50, KB-1005), answer (Rule 3, KB-1004), escalate (Rule 3 confirmed part, KB-1004, evidence gap), answer (Rule 3, 2026-10-21, KB-1004).

## Known limits
- Question type is still keyword based; unknown questions hand off to Tier 2.
- Team names for declines are matched from the article text by two known names.
- Replies are templates filled from state; customer replies carry no rule numbers (design), the rule is in `reason` and the ESCALATION row.

## Next
- nothing in progress; waiting for lead

## NEEDS HUMAN
(none from builder; open points are in the report to lead)

## Log
- 2026-10-11 13:06 builder: started
- 2026-10-11 13:10 builder: Codex run 1 finished, created run.sh, agent/, data/fixtures.json, README.md
- 2026-10-11 13:11 builder: ./run.sh runs; reviewing code; found retrieval query is seeded with the already-chosen article
- 2026-10-11 13:12 builder: lead-3 received (guards); Codex run 2 started with retrieval fix, guards, intent and trace fixes
- 2026-10-11 13:19 builder: lead-4 and lead-5 received; stopped Codex run 2 (no output, no file changes); confirmed ./run.sh and ./run.sh --json still work
- 2026-10-11 13:20 builder: paused by lead, waiting on human approval of architecture and design
- 2026-10-11 13:36 builder: lead-10 resume received (architecture and design approved by human). Started Codex run 3 (decision logic: honest retrieval, state-first classification, replies, evidence, guards; files state/policy/respond/retrieval/loaders/__main__) and Codex run 4 (agent/render.py trace layout in pipeline order) in parallel. run.sh may be briefly unstable while these run. Cutoff 14:25.
- 2026-10-11 13:40 builder: Codex runs 3 and 4 finished; scorer 109/109, sources PASS
- 2026-10-11 13:44 builder: Codex run 5 (replies, intents, trace columns and row order) and run 6 (outage wording, acknowledgements, Rule 2 limit answer, README) finished
- 2026-10-11 13:46 builder: hand fixes: one handoff per reply under Rule 5, no rule id in customer reply, deadline answer when Rule 3 fails or no ticket, blending guard only when a ticket-based calculation ran
- 2026-10-11 13:47 builder: final score 109/109, sources PASS; done, reported to lead
- 2026-10-11 13:52 builder: lead-13 received (held-out cases 12-15: 24/45, one unsafe reply). Codex run 7 started: facts-first issue recognition, Rule 3 lock on limit/deadline questions, multi-question turns. Cutoff 14:30.
- 2026-10-11 13:55 builder: Codex run 7 finished (facts-first recognition, Rule 3 lock, multi-question replies); 154/154
- 2026-10-11 13:58 builder: own unseen conversations found more gaps; Codex run 8 fixed them (evidence only from retrieved articles and governing rules, Rule 1 rejected again on deadline turns, problem-described first turn, acknowledgement by shape, add-on and limit wording by meaning)
- 2026-10-11 13:59 builder: three small hand fixes in agent/respond.py ("time limit" is not a credit-limit question; unrelated question on a complete claim is an evidence gap; scope article chosen by category). Final 154/154, sources PASS. Done, reported to lead.
- 2026-10-11 14:12 builder: lead-16 received (speaker names, handoff note, --handoff, handoff_notes and participants in JSON; output only). Backup of agent/ taken in scratch; baseline 179/182, 16/17, sources 4/4. Codex run 9 started. Cutoff 14:30.
- 2026-10-11 14:15 builder: lead-16 done. Codex run 9 added agent/handoff.py, speaker names, HANDOFF NOTE block, --handoff, top-level participants and handoff_notes; hand-tidied note wording and layout. Score unchanged: 179/182, 16/17 cases, sources 4/4. Existing JSON fields byte-identical to the pre-change output on the provided conversation and cases 04, 08, 09, 17. respond/state/policy/loaders/retrieval untouched. agent/__pycache__ deleted.
- 2026-10-11 14:17 builder: lead-17 done. Rewrote the note builder in agent/handoff.py by hand (no time for a Codex round trip before 14:27): full customer question, Decide / Known lines, one-sentence reason, plain-sentence recap per turn, "- " bullets. One line changed in agent/render.py (no cut on recap lines). Score unchanged 179/182, 16/17, sources 4/4; existing JSON fields identical; all 17 cases run, no line over 80 columns. Provided-conversation note is 35 lines (target 25). agent/__pycache__ deleted.
- 2026-10-11 14:33 builder: lead-19 done, written directly (not Codex), in agent/respond.py only. (1) After a claim has its credit answer, a turn asking for something other than the amount, limit, deadline or scope is an evidence-gap handoff with the credit as the confirmed part; (2) deadline questions recognised from time words (last day, until when, by when ...) alone or near a filing word, so limit+deadline turns get both answers. Score unchanged 179/182, 16/17 (case 17 turn 3 only), sources 4/4. Provided-conversation JSON byte-identical to before. No line over 80 columns, deterministic. Backup of the previous agent/ kept in scratch. agent/__pycache__ deleted.
- 2026-10-11 15:02 builder: lead-20 received (docs/workflow-review.md findings). Backup of agent/ and baseline JSON saved in scratch. Codex run 10 started for A (customer-reported fraud), B (human request, stalled clarification), G (acknowledgements), F (deadline with no ticket), H (handoff wording). C, D, E only if time allows. Cutoff 15:14.
- 2026-10-11 15:07 builder: lead-20 done before the 15:14 cutoff. Codex run 10: A (customer-reported fraud -> Rule 4d / Rule 5 escalation), B (human request; third consecutive clarify hands off), G (acknowledgement only for explicit closers), F (deadline with no ticket states the 30-day rule and escalates under Rule 4b), H (handoff wording: prepared, not sent). By hand: D wording only (no "qualifies"; "once the error is confirmed on the invoice"), E (ticket confirms only its own period; dates beyond it escalate under Rule 4b), C (a question clause that no known topic covers is named as not covered and handed off). NOT done: D missing account history read as zero; findings 9 and 10. Score 214/217, 22/23 cases, only case 17 turn 3 failing; sources 4/4. Provided conversation: decision, governing_policy, driving_article, computed identical on all six turns; reply changed on turn 5 only. Backups in scratch. agent/__pycache__ deleted.
- 2026-10-11 15:16 builder: lead-23 (device-protection routing, case 17 turn 3) NOT done. The task reached the builder at 15:15:50, ten seconds before its 15:16 cutoff; no code was changed. agent/ is identical to the state reported for lead-20 (214/217, 22/23, sources 4/4). agent/__pycache__ deleted.
- 2026-10-11 15:17 builder: lead-24 done by hand (agent/state.py, agent/respond.py). A device-protection request (the customer's own device with a damage, loss or replacement word, or a protection/insurance plan mention) now wins over an open outage claim unless the turn itself describes a service interruption or fraud was reported; that turn's query uses device-track words instead of outage words. Case 17 passes. Score 217/217, 23/23, sources 4/4. Provided conversation and case 09 JSON byte-identical to before. No line over 80 columns. agent/__pycache__ deleted.
