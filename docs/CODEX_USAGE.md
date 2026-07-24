# Using PPT Order Autopilot In Codex

## What Codex Is Doing

Codex is the orchestrator. The repository supplies durable context, state, safety rules, templates, and validators; it is not trying to replace the Agent with a traditional background service.

Install or attach this repository as the `ppt-order-autopilot` Codex plugin, or open it directly as the workspace. The plugin is intentionally thin: it exposes the entrypoint and skills, while progressive disclosure keeps most docs, schemas, raw chat, and customer files out of the active context until needed.

## One-Time Setup

For WeCom intake or delivery, provide the exact allowed contact and send policy once. A screenshot of the correct WeCom contact is useful when the displayed identity is hard to describe, but a precise name/account is enough. Codex turns that into live config; `.example.json` files never authorize a send.

You do not need WeCom config to begin an attachment-only order. Codex may analyze attached customer files first and ask for the live contact only before the first WeCom read or send.

## Start Modes

### Make or edit a deck for me

Attach a file or point to an existing workspace file, then say what result to return. Codex uses `execution_mode=owner_direct`; it does not ask for customer price, WeCom contact, customer deadline, customer sample-send permission, or final-send permission unless the request actually involves a customer side effect. For design work it does pause once to show you a complete-slide visual sample before producing the rest of the deck.

```text
Use PPT Order Autopilot to beautify this deck and return the finished PPTX to me.
Use the plugin's one-slide-per-subagent workflow.
```

An explicitly named workspace file is recorded as `workspace_file`. A file attached to the message is `codex_attachment`. The file name or folder name does not decide whether the customer sample branch is required.

### Start from WeCom

```text
Run PPT Order Autopilot from WeCom. Continue automatically until an owner gate,
a hard blocker, or order closeout. Do not stop at internal steps.
```

Codex locates the allowed contact, checks for an order, captures the chat and files, creates the order, and continues.

### Start from Codex attachments

Attach the customer's PPT/PDF/Word/images or brief to the task, then say:

```text
Treat these attachments and my message as one PPT order. Run PPT Order Autopilot.
Continue automatically until an owner gate, a hard blocker, or order closeout.
```

Codex stages and indexes the files itself. It must label the source as `codex_attachment`; it must not fabricate a WeCom chat history.

The attachment-intake skill derives stable Codex evidence IDs from the exact prompt and attachment hashes, so rerunning the same task reuses the inquiry instead of duplicating it.

### Resume

```text
Resume PPT Order Autopilot from its saved state. Reconcile external actions first.
```

Codex reads state, events, approvals, file hashes, and side-effect ledgers. It does not restart from conversation memory or resend an action merely because an earlier turn ended.

## When Codex Asks You

Codex should ask only for high-impact decisions or evidence it cannot safely infer:

1. Approval or revision of the complete single-slide sample shown in Codex for `owner_direct` design work.
2. One-time WeCom identity and send permissions.
3. Accept/reject, price, deadline, scope, or the exact missing-question message.
4. Permission to send a customer sample or final files.
5. Major revision, extra pages, style reset, or payment decision.
6. Ambiguous customer feedback, source truth, required asset, contact identity, or exhausted automatic repair attempts.

Clear customer sample approval does not need a second owner confirmation. Clear minor sample changes return to sample production automatically. A change that affects scope, price, deadline, or the overall visual direction does ask you.

Every request should arrive as one decision card with the Agent's recommendation, the exact customer-facing message/files, the consequence of approval, and a short response such as `approve` or the change you want.

## What Runs Without Asking

Chat capture, attachment download, OCR, indexing, requirements extraction, conflict detection, sample planning/generation/QA, production planning, style-kit construction, per-slide dispatch, image generation, internal QA, bounded repair, assembly, export, file hashing, and delivery-message drafting are automatic. Owner-direct design work stops after displaying the first complete-slide sample; the remaining pages start only after approval bound to that preview hash.

Each slide is a separate subagent job. In `image_first`, that job asks the image model for the entire page with all visible content—not a background layer for the parent to finish. The parent Agent supplies deck-level and local context, keeps all attempts, accepts or rejects the result, runs cross-slide QA, applies only approved locked chrome, and assembles the final deck.

Explicitly attaching the plugin and asking it to produce slides authorizes this declared subagent workflow. If that capability is unavailable, Codex must stop before production instead of silently replacing it with a generic presentation builder.

For owner-direct work, every stage is committed through `tools/autopilot.py`. The final response is valid only after `finish --target owner` returns a receipt ID; returning a file in Codex does not authorize sending it to a customer.

If navigation, logo, footer, or page numbers must stay fixed, slide workers generate the page body while leaving the locked regions clear. The parent then applies the approved transparent overlay and verifies its hash and pixels before cross-slide QA. This prevents independently generated pages from moving the navigation bar.

## Waiting And Notifications

Within an active Codex task, the Agent keeps going until a gate or blocker. A schedule stored in this repository does not wake Codex after the task has ended.

For unattended WeCom reply checks, ask Codex once to create monitoring from the live schedule. The orchestrator maintains one workspace-level Codex Automation and stores its binding, so reruns update it instead of creating duplicates. If the automation environment cannot control the local WeCom app, keep UI operations in a foreground Codex task and use the automation only to remind or resume you.

Owner questions appear in the same Codex task. Operating-system notifications depend on your Codex notification settings.
