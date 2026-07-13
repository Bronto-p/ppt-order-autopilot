# Agent Run Loop

## Purpose

This is the operational entrypoint for a capable AI agent. The agent is expected to use reasoning, Computer Use, subagents, image generation, filesystem tools, and presentation/PDF tools. Local Python utilities exist for deterministic initialization and validation; they are not the orchestrator.

The user does not prepare an order folder. The agent begins from WeCom or Codex attachments, discovers the order, creates its runtime artifacts, and proceeds until a human commitment gate or a real blocker.

## 1. Bootstrap

Before the first unattended WeCom side effect, require live versions of:

```text
configs/allowed_contacts.json
configs/ask_schedule.json
configs/message_policy.json
```

Files ending in `.example.json` are never authorization. If live files are missing or still contain replacement values, ask once for the exact WeCom contact identity and intended send permissions. Do not repeatedly ask for values already present in live config. A Codex-attachment order may continue through internal analysis before this setup, but it must stop before any WeCom read or send.

Initialize these runtime files when absent:

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

For `codex_attachment`, use a deterministic inquiry ID derived from the attachment hashes. Copy attachments into `downloads/`, set `source_type=codex_attachment`, record `source_attachment_paths`, and promote once the files or the user's prompt reveal a stable topic. Record the Codex prompt as source evidence; do not fabricate WeCom screenshots, message IDs, or chat coverage. If later delivery must go through WeCom, collect the live contact configuration only at that external-action gate.

If one reply contains multiple distinct customer orders, create one order per distinct scope and preserve the shared inquiry evidence in each order index.

## 4. Orchestration Algorithm

At every wake or resume:

1. Read live config and `ledgers/automation_state.json`.
2. Reconcile pending external side effects against `ui_actions.jsonl` and `sent_messages.jsonl`.
3. If there is no active order, resume the scheduled inquiry or reply-check branch.
4. If there is an active order, read its `state.json`, latest events, approvals, and current state definition in `configs/state_machine.json`.
5. Verify required artifacts for the current state.
6. Select exactly one next skill/action.
7. Load that skill and only its input schemas/templates.
8. Execute, validate the resulting gate, append an event, and transition atomically.
9. Continue without asking the owner unless the next state requires approval or the skill returned a hard blocker.

Never rely on the parent chat as the source of truth. Chat is for owner decisions; state and artifacts are for execution.

## 5. Tool Routing

| Action | Required capability |
| --- | --- |
| Open WeCom, locate contact, type, scroll, download, attach, send | Computer Use using `wecom-computer-use-operator` |
| Interpret chat and customer files | Current agent using `wecom-chat-recorder` and `ppt-order-briefing` |
| Decide next business step | Current agent using `ppt-order-decision` and owner gates |
| Generate sample/final slides | One subagent per slide with the selected image-generation backend |
| Inspect images and cross-slide consistency | Parent agent using visual inspection and QA contracts |
| Assemble PPTX/PDF and verify exports | Presentation/PDF tooling selected by production core |

If a required capability is unavailable, record a blocker. Do not silently substitute a method forbidden by the active contract.

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

Every final report must name the active inquiry/order, current state, completed artifacts, next action, and whether owner approval is required.

## 9. Codex Lifecycle

An active Codex task may continue through all internal steps until it reaches a gate. Repository schedules describe *when* to check WeCom but do not wake Codex by themselves. For reply checks after the active task has ended, use a Codex Automation or explicitly tell the same task to `resume PPT Order Autopilot`. On resume, state and ledgers are authoritative; do not restart the order.
