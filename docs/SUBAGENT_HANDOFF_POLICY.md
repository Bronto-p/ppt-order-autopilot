# Subagent Handoff Policy

Each slide worker receives one self-contained material bundle. Workers must not rely on parent chat context, raw attachment folders, or memory from another page.

```text
05_production/slide_jobs/slide_07/
├── job.json
├── prompt.md
└── input_images/
    ├── style_anchor.png
    ├── template_master.png
    ├── navigation_bar.png
    ├── page_family_ref.png
    └── client_required_image_001.png
```

## Required Job Contents

- `slide_id`
- `slide_no`
- `title`
- `page_type`
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
  "status": "success",
  "selected_source": "05_production/origin_image/slide_07.png",
  "backend_used": "same_as_sample",
  "input_images_seen": [
    "style_anchor.png",
    "navigation_bar.png",
    "chart_001.png"
  ],
  "asset_fidelity_check": "chart_001 appears as supplied; labels preserved",
  "style_check": "matches style_anchor palette and title hierarchy",
  "text_check": "Chinese title and bullets readable",
  "blockers": []
}
```

If a required input image is unavailable or not visible to the backend, the worker must return a blocker and must not use a text-only fallback.

## Human Confirmation Boundary

Ask the owner for anything that changes customer commitments: sending messages, accepting/rejecting orders, price, deadline, scope, sample delivery, final delivery, major revision, extra pages, style reset, payment, or repeated QA failures.

Do not ask for internal actions: order folder setup, transcript/OCR, attachment indexing, draft requirements, draft production contract, slide job packaging, first automatic regeneration, PDF export, QA report generation, or delivery message drafting.
