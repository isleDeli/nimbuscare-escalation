# NimbusCare: Policy-Grounded Customer Support Agent

An offline Python prototype that evaluates customer billing disputes against documented policies, shows the evidence behind each decision, and prepares specialist handoffs when a request needs human review.

The workflow handles service-outage credits, general billing disputes, credit limits, request deadlines, and separate-team routing. Its trace records the governing policy, retrieved knowledge-base article, calculations, and escalation reason so reviewers can inspect how each reply was produced.

Built with Python's standard library, deterministic rules, and keyword retrieval. Runs locally without an API key or network access.

Validation on October 11, 2026: all 23 evaluation scenarios passed, covering 217 checks, alongside four source-restriction checks. This is a prototype with fixture-backed accounts; specialist handoffs are prepared notes and are not delivered to a live queue.

Suggested project tags: Python, Customer Support, Policy Retrieval, Human Escalation, Agent Evaluation.

Links to add after publication: GitHub repository and downloadable source archive.
