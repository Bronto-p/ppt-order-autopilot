# PPT Order Autopilot Agent Entry

This repository is an agent-operated system, not a request for the user to prepare an order folder manually.

When the user says to run, continue, resume, check, or operate the PPT order autopilot:

1. Read `docs/AGENT_RUN_LOOP.md` completely.
2. Read `skills/ppt-business-orchestrator/SKILL.md` and `configs/state_machine.json`.
3. Inspect live configs, global runtime state, inquiry staging folders, order state, and ledgers.
4. Resume the earliest unfinished side effect or artifact. Do not restart from chat memory.
5. Load only the skill and schemas required for the current action.
6. Continue automatically until an owner-approval gate, a hard blocker, or order closeout.

Operational rules:

- Intake may start from WeCom through Computer Use or from files the user attaches directly in Codex. Never ask the user to build or populate an order folder.
- For Codex attachments, stage the files under `inbox/{inquiry_id}/downloads/`, record their hashes and source, then promote them into an order. Do not invent chat evidence.
- Example configs are documentation, not live authorization. Missing live contact or send configuration blocks only the first WeCom side effect; internal work from Codex attachments may continue before that gate.
- Before an order exists, use `inbox/{inquiry_id}/` and `ledgers/automation_state.json`.
- Once the chat reveals enough identity for an order, initialize `orders/{order_id}_{topic}/`, promote the inquiry artifacts, and continue from order state.
- Use one subagent per slide. The parent agent owns orchestration, state, packaging, QA, repair decisions, assembly, and reporting.
- Every external side effect must be reconciled against ledgers before retrying.
- At an owner gate, return one decision card containing the order, recommendation, exact message/files affected, consequence, and a short reply instruction. Do not ask vague questions.
- Never merge pull requests or change `main` without the owner.
