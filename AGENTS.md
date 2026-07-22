# PPT Order Autopilot Agent Entry

This repository is an agent-operated system, not a request for the user to prepare an order folder manually.

When the user says to run, continue, resume, check, or operate the PPT order autopilot:

1. Read `docs/AGENT_RUN_LOOP.md` and `skills/ppt-business-orchestrator/SKILL.md`.
2. For an existing order, run `python3 tools/autopilot.py next <order_dir>` before doing work. Its output is authoritative.
3. Inspect raw chats, attachments, or full ledgers only when the selected stage skill requires them.
4. Resume the earliest unfinished side effect or artifact. Do not restart from chat memory.
5. Load only the skill and schemas required for the current action.
6. Commit every completed state with `tools/autopilot.py commit`; never hand-edit state to skip a gate.
7. Continue automatically until an owner-approval gate, a hard blocker, or order closeout.

Operational rules:

- Intake may start from WeCom through Computer Use or from files the user attaches directly in Codex. Never ask the user to build or populate an order folder.
- A direct request to make/edit a PPT and return it in Codex uses `execution_mode=owner_direct`; a customer communication/order uses `customer_order`.
- A file already in the workspace and explicitly identified by the user uses `source_type=workspace_file`, not a fabricated Codex attachment.
- For Codex attachments, stage the files under `inbox/{inquiry_id}/downloads/`, record their hashes and source, then promote them into an order. Do not invent chat evidence.
- Example configs are documentation, not live authorization. Missing live contact or send configuration blocks only the first WeCom side effect; internal work from Codex attachments may continue before that gate.
- Before an order exists, use `inbox/{inquiry_id}/` and `ledgers/automation_state.json`.
- Once the chat reveals enough identity for an order, initialize `orders/{order_id}_{topic}/`, promote the inquiry artifacts, and continue from order state.
- Use one subagent per slide. The parent agent owns orchestration, state, packaging, QA, repair decisions, assembly, and reporting.
- For owner-direct design work, first generate one representative complete slide with real content, show it in Codex, and stop at `OWNER_SAMPLE_REVIEW`. Do not treat a background, moodboard, blank template, or style anchor as the sample.
- Design/beautify/redesign defaults to `image_first`. Each worker must generate the whole page with all visible content; inferred `hybrid` and background-only visual layers are forbidden unless an explicit high-confidence editability requirement selects another mode.
- Explicitly invoking this plugin and asking it to produce slides is an explicit request for its declared one-slide-per-subagent capability. If unavailable, stop before production instead of substituting a generic deck builder.
- Do not preload all skills, docs, schemas, raw chats, or customer files. Load one stage skill and its direct inputs at a time. A slide worker receives only its immutable slide bundle.
- If continuous monitoring is requested, maintain one workspace-level Codex Automation and persist its identity in `ledgers/automation_state.json`; never create one automation per order.
- Every external side effect must be reconciled against ledgers before retrying.
- At an owner gate, return one decision card containing the order, recommendation, exact message/files affected, consequence, and a short reply instruction. Do not ask vague questions.
- Owner-direct completion requires `tools/autopilot.py finish <order_dir> --target owner`; do not claim completion without its `receipt_id`.
- Never merge pull requests or change `main` without the owner.
