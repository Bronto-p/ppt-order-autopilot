# Using PPT Order Autopilot In Codex

## What Codex Is Doing

Codex is the orchestrator. The repository supplies durable context, state, safety rules, templates, and validators; it is not trying to replace the Agent with a traditional background service.

Open this repository as the Codex workspace. The root `AGENTS.md` tells Codex how to start and resume without requiring you to prepare folders.

## One-Time Setup

For WeCom intake or delivery, provide the exact allowed contact and send policy once. A screenshot of the correct WeCom contact is useful when the displayed identity is hard to describe, but a precise name/account is enough. Codex turns that into live config; `.example.json` files never authorize a send.

You do not need WeCom config to begin an attachment-only order. Codex may analyze attached customer files first and ask for the live contact only before the first WeCom read or send.

## Start Modes

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

### Resume

```text
Resume PPT Order Autopilot from its saved state. Reconcile external actions first.
```

Codex reads state, events, approvals, file hashes, and side-effect ledgers. It does not restart from conversation memory or resend an action merely because an earlier turn ended.

## When Codex Asks You

Codex should ask only for decisions that affect the customer or for evidence it cannot safely infer:

1. One-time WeCom identity and send permissions.
2. Accept/reject, price, deadline, scope, or the exact missing-question message.
3. Permission to send a sample.
4. Permission to send final files.
5. Major revision, extra pages, style reset, or payment decision.
6. Ambiguous customer feedback, source truth, required asset, contact identity, or exhausted automatic repair attempts.

Clear customer sample approval does not need a second owner confirmation. Clear minor sample changes return to sample production automatically. A change that affects scope, price, deadline, or the overall visual direction does ask you.

Every request should arrive as one decision card with the Agent's recommendation, the exact customer-facing message/files, the consequence of approval, and a short response such as `approve` or the change you want.

## What Runs Without Asking

Chat capture, attachment download, OCR, indexing, requirements extraction, conflict detection, production planning, style-kit construction, per-slide dispatch, image generation, internal QA, bounded repair, assembly, export, file hashing, and delivery-message drafting are automatic.

Each slide is a separate subagent job. The parent Agent supplies deck-level and local context, keeps all attempts, accepts or rejects the result, runs cross-slide QA, and assembles the final deck.

## Waiting And Notifications

Within an active Codex task, the Agent keeps going until a gate or blocker. A schedule stored in this repository does not wake Codex after the task has ended.

For unattended WeCom reply checks, create a Codex Automation that resumes this workspace at the desired interval. If the automation environment cannot control the local WeCom app, keep UI operations in a foreground Codex task and use the automation only to remind or resume you.

Owner questions appear in the same Codex task. Operating-system notifications depend on your Codex notification settings.
