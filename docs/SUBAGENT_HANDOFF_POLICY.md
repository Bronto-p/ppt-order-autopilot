# Subagent Handoff Policy

Each slide worker receives one self-contained material bundle. Workers must not rely on parent chat context, raw attachment folders, or memory from another page.

```text
05_production/slide_jobs/slide_07/
├── job.json
├── prompt.md
├── input_images/
│   ├── style_anchor.png
│   ├── template_master.png
│   ├── navigation_bar.png
│   ├── locked_chrome.png
│   ├── page_family_ref.png
│   └── client_required_image_001.png
└── attempts/
    ├── attempt_01/
    │   ├── job_snapshot.json
    │   ├── render_result.json
    │   └── output.png
    └── attempt_02/
        ├── repair_job.json
        ├── render_result.json
        └── output.png
```

## Required Job Contents

- `job_id`
- `attempt`
- `max_attempts`
- `slide_no`
- `title`
- `page_type`
- `output_mode`
- `deck_context`
- `local_context`
- `exact_content`
- `input_images`
- each `input_images[].bundle_path`
- `visual_constraints`
- `backend`
- `worker_policy`
- `qa_requirements`

## Worker Policy

- `reasoning_level` defaults to `high`.
- `low` is forbidden for customer production.
- `medium` is only allowed for simple decorative or section pages with no customer assets.
- pages with customer images, logos, charts, screenshots, certificates, data, tables, old PPT references, navigation bars, covers, or strict consistency requirements must use `high`.

## Worker Result

Workers should return a result that records:

```json
{
  "job_id": "2026-07-05_001:slide_07",
  "attempt": 1,
  "slide_no": 7,
  "output_mode": "hybrid",
  "status": "success",
  "output_image": "05_production/slide_jobs/slide_07/attempts/attempt_01/output.png",
  "input_images_seen": [
    "style_anchor.png",
    "navigation_bar.png",
    "chart_001.png"
  ],
  "asset_fidelity": [
    {
      "asset": "chart_001.png",
      "status": "pass",
      "notes": "appears as supplied; labels preserved"
    }
  ],
  "style_match": "pass",
  "text_readability": "pass",
  "editable_artifacts": [
    {
      "path": "05_production/slide_jobs/slide_07/attempts/attempt_01/editable-layer.json",
      "sha256": "sha256:...",
      "role": "editable_layer_spec"
    }
  ],
  "blockers": []
}
```

## Attempt And Repair Rules

- `job.json` is the immutable base job and uses `attempt: 1`.
- Every dispatch snapshots the exact job and prompt under `attempts/attempt_XX/` before calling a worker.
- Parent QA accepts or rejects an attempt; workers never accept their own output.
- Workers write an attempt-local rendered preview and any mode-required editable artifacts. They never write `origin_image/slide_XX.png`.
- When `locked_chrome.mode=post_generation_composite`, the worker treats the overlay as a placement/safe-zone reference but does not redraw it. The parent applies the exact overlay after accepting the raw attempt and writes `finalization.json`.
- A rejected attempt creates `repair_job.json` with failure class, evidence files, narrow repair instructions, and must-preserve constraints.
- Repair workers receive the base job, the rejected output, QA evidence, and the repair job. They must not reinterpret the customer request.
- Never overwrite a prior attempt. Finalize only the accepted output into `origin_image/slide_XX.png`, record `accepted_attempt`, and preserve the raw image separately.
- Automatic generation stops after `max_attempts` (maximum 3). Missing source truth or required assets blocks immediately instead of consuming retries.

If a required input image is unavailable or not visible to the backend, the worker must return a blocker and must not use a text-only fallback.

## Human Confirmation Boundary

Ask the owner for anything that changes customer commitments: sending messages, accepting/rejecting orders, price, deadline, scope, sample delivery, final delivery, major revision, extra pages, style reset, payment, or repeated QA failures.

Do not ask for internal actions: order folder setup, transcript/OCR, attachment indexing, draft requirements, draft production contract, slide job packaging, permitted automatic repairs, PDF export, QA report generation, or delivery message drafting.
