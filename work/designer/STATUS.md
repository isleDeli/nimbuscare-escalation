# designer STATUS

## Done

- 2026-10-11 designer: trace layout spec -> `docs/design/trace.md` (answer turn, escalate turn, summary, colour and wording rules)

## Next

- nothing; waiting on the human's approval of the spec via the lead

## NEEDS HUMAN

- [ ] 2026-10-11 designer: output format. options: a) terminal only, b) terminal plus out/trace.html (about 25 to 30 min of builder time), c) terminal plus out/trace.txt (about 3 min) recommend: a
- [ ] 2026-10-11 designer: show the human agent's original reply under each turn. options: a) yes, last row, marked not evidence, b) no recommend: a
- [ ] 2026-10-11 designer: rewrite the handoff reply to Confirmed / Not covered / Next. options: a) yes (about 5 min), b) keep current sentence recommend: a

## Log

- 2026-10-11 designer: read brief, interface, policy, knowledge base, transcript; ran ./run.sh and ./run.sh --json (both ran; `guards` not yet in output)
- 2026-10-11 designer: computed tag contrast on the xterm palette; wrote docs/design/trace.md
