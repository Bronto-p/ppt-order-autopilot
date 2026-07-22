# Agent Run Loop

## Purpose

This is the operational entrypoint for a capable AI agent. The agent is expected to use reasoning, Computer Use, subagents, image generation, filesystem tools, and presentation/PDF tools. Local Python utilities exist for deterministic initialization and validation; they are not the orchestrator.

The user does not prepare an order folder. The agent begins from WeCom, Codex attachments, or an explicitly named workspace file, creates runtime artifacts, and proceeds until a human commitment gate, verified owner return, closeout, or a real blocker.

## 1. Bootstrap

Before the first unattended WeCom side effect, require live versions of:

```text
configs/allowed_contacts.json
configs/ask_schedule.json
configs/message_policy.json
```

Files ending in `.example.json` are never authorization. If live files are missing or still contain replacement values, ask once for the exact WeCom contact identity and intended send permissions. Do not repeatedly ask for values already present in live config. A Codex-attachment order may continue through internal analysis before this setup, but it must stop before any WeCom read or send.

Run `python3 tools/bootstrap_runtime.py`. It initializes these runtime files when absent and never overwrites existing state:

```text
ledgers/automation_state.json
ledgers/inquiries.jsonl
ledgers/orders.jsonl
ledgers/ui_actions.jsonl
ledgers/sent_messages.jsonl
ledgers/approvals.jsonl
```

`ledgers/automation_state.json` begins from `templates/inquiry/automation_state.template.json`.

## 2. Two State Scopes

### Automation state

Automation state exists before an order is known. It owns scheduled asks, reply checks, the active contact, inquiry staging, and the active order pointer.

### Order state

`orders/{order_id}_{topic}/00_state/state.json` begins only after the agent has opened a reply and identified enough information to create an order. It owns requirements, approval, production, QA, delivery, revisions, and closeout.

Do not invent a placeholder customer order merely to send the daily inquiry.

## 3. Inquiry Staging

Choose one intake source from the user's request:

- `wecom`: discover the order in the allowed WeCom chat.
- `codex_attachment`: ingest files attached to the Codex task. The agent copies them into staging and builds the attachment index; the user never prepares a repository folder.
- `workspace_file`: ingest a readable workspace file explicitly identified by the user. Record its original relative path and hash; do not call it an attachment.

Choose one execution profile:

- `owner_direct`: the owner asks Codex to make/edit a deck and return it in Codex. No customer commitment or external-send gate is implied.
- `customer_order`: the workflow reads or commits to a customer and retains all business/send approvals.

For each outbound ask, create:

```text
inbox/{inquiry_id}/
├── inquiry_state.json
├── screenshots/
├── ocr/
└── downloads/
```

An inquiry ID must be deterministic from contact plus the outbound message ledger record. Re-running the same scheduled action must reuse the inquiry instead of sending again.

Store pre-order screenshots and downloads here. After a reply reveals the customer topic or a stable fallback title, call `tools/init_order.py --with-templates`, move the staged artifacts into the matching order folders, write a promotion event to both ledgers, and set `active_order_id`.

For `codex_attachment` or `workspace_file`, load `codex-attachment-intake`. Derive a deterministic inquiry ID from the exact prompt, source type, and sorted file names/hashes; workspace sources also include their relative source paths. Copy files into `downloads/`, record the exact source type and paths, and promote once the prompt/files reveal a stable topic. Do not fabricate WeCom screenshots, OCR, senders, coverage, or attachment provenance. If later delivery must go through WeCom, collect live contact configuration only at that external-action gate.

If one reply contains multiple distinct customer orders, create one order per distinct scope and preserve the shared inquiry evidence in each order index. Set the first runnable order as `active_order_id` and append the rest to `pending_order_ids`. When the active order reaches an owner gate, move its ID to `waiting_order_ids` before rotating to the next pending order. An owner reply names/binds its order ID, removes it from waiting, and makes it active when safe. Closed orders leave all queues. Never process two orders concurrently under one lock.

## 4. Orchestration Algorithm

At every wake or resume:

1. For an existing order, run `python3 tools/autopilot.py next <order_dir>`; do not infer the current step from chat.
2. Read live config and `ledgers/automation_state.json`.
3. Reconcile pending external side effects against `ui_actions.jsonl` and `sent_messages.jsonl`.
4. If there is no active order, resume the scheduled inquiry or reply-check branch.
5. If there is an active order, read its `state.json`, latest events, approvals, and current state definition in `configs/state_machine.json`.
6. Verify required artifacts for the current state.
7. Select exactly one next skill/action.
8. Load that skill and only its input schemas/templates.
9. Execute, then run `python3 tools/autopilot.py commit <order_dir> --to <STATE>` to validate, append an event, and transition atomically.
10. Continue without asking the owner unless the next state requires approval or the skill returned a hard blocker.

Never rely on the parent chat as the source of truth. Chat is for owner decisions; state and artifacts are for execution.

### Runtime context tiers

1. **Always resident:** automation state, active order state, current state-machine entry, latest relevant events, valid approvals, and compact artifact summaries.
2. **Stage resident:** exactly one selected skill plus its direct schemas, templates, and input artifacts.
3. **Worker resident:** one immutable slide bundle only. The slide worker never receives the full repository, raw chat, all customer attachments, or other slide attempts.

The parent retains the production contract, deck story, style kit index, slide run state, and cross-slide QA. It passes the worker only the deck/local summaries and real files already copied into that slide bundle. Paths are pointers, not permission to recursively read unrelated folders.

## 5. Tool Routing

| Action | Required capability |
| --- | --- |
| Open WeCom, locate contact, type, scroll, download, attach, send | Computer Use using `wecom-computer-use-operator` |
| Stage files attached to the Codex task and promote them into an order | `codex-attachment-intake` |
| Stage an explicitly named workspace file | `codex-attachment-intake` with `source_type=workspace_file` |
| Interpret chat and customer files | Current agent using `wecom-chat-recorder` and `ppt-order-briefing` |
| Decide next business step | Current agent using `ppt-order-decision` and owner gates |
| Generate sample/final slides | One subagent per slide with the contract-selected backend and output mode |
| Inspect images and cross-slide consistency | Parent agent using visual inspection and QA contracts |
| Assemble PPTX/PDF and verify exports | Presentation/PDF tooling selected by production core |

If a required capability is unavailable, record a blocker. Do not silently substitute a method forbidden by the active contract.

Explicit plugin invocation plus a request to produce slides is explicit authorization for the plugin's declared one-slide-per-subagent capability. It does not authorize any customer-facing side effect.

## 6. Recovery and Idempotency

Before repeating an action with external effects:

- Message send: match contact, message hash, approval ID, inquiry/order ID, and duplicate window.
- Attachment download: match source message and file hash; reuse a verified existing file.
- Slide dispatch: match slide job ID and attempt; do not dispatch an already recorded or accepted attempt.
- Image generation: retain every attempt and selected result; never overwrite evidence.
- Delivery: match the approved file manifest hashes and delivery-message hash.

Use `locked_by` and `lock_expires_at` for order work. A live lock owned by another run blocks. An expired lock may be reclaimed only after checking the latest event and side-effect ledgers.

On ambiguous external state, inspect the UI or artifact first. Never assume an action failed merely because the previous agent turn ended.

## 7. Human Gates

Stop and request owner confirmation only for customer commitments or explicit hard stops:

- accept/reject, price, deadline, scope, or missing-question message;
- sample delivery; ambiguous customer sample feedback;
- final delivery;
- major revision, extra pages, style reset, payment decision;
- repeated QA failure beyond the permitted automatic repair attempt;
- identity, chat coverage, source truth, or required-asset ambiguity.

Folder creation, OCR, indexing, requirement drafting, contract drafting, slide packaging, first repair, export, QA, and delivery-message drafting are internal actions and should continue automatically.

Clear customer sample feedback is not another owner gate. Record it in `customer_sample_decision.json`: explicit approval proceeds to style-kit/full production, and explicit requested changes return to sample production. Ask the owner only when the feedback is ambiguous or changes price, deadline, page count, or style scope.

### Owner decision card

Every owner gate must be one compact Codex message:

```text
[Needs confirmation] {order_id} - {action}
Recommendation: {approve / reject / revise, with one reason}
Customer-facing effect: {exact message and file names, or exact commitment}
If approved: {next automatic steps}
Reply with: "approve" or the change you want
```

The agent must bind the reply to the pending approval ID and current message/file hashes before resuming. It should not ask the owner to inspect internal folders or reconstruct missing context.

## 8. Completion

The automation run is complete only when:

- it is waiting at a clearly recorded owner gate;
- it is blocked with a specific required action and evidence;
- the no-reply schedule has ended; or
- the order is closed with delivery receipt and closeout artifacts.
- an `owner_direct` order has passed `autopilot.py finish --target owner` and reached `OWNER_RETURNED`.

Every final report must name the active inquiry/order, current state, completed artifacts, next action, and whether owner approval is required. An owner-direct completion must include the generated `receipt_id`; without it, report the actual blocker instead of claiming success.

## 9. Codex Lifecycle

An active Codex task may continue through all internal steps until it reaches a gate. Repository schedules describe *when* to check WeCom but do not wake Codex by themselves. For reply checks after the active task has ended, use one workspace-level Codex Automation or explicitly tell the same task to `resume PPT Order Autopilot`. On resume, state and ledgers are authoritative; do not restart the order.

When the user asks for unattended monitoring, create/update that one Automation from the live schedule and persist its ID and schedule fingerprint under `automation_binding`. The wake prompt must reconcile external actions, exit quietly when nothing is due, and otherwise continue to an owner gate, blocker, or closeout. Never create one Automation per order.
