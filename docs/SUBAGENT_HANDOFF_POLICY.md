# Subagent Handoff Policy

Each slide worker receives one self-contained JSON job. Workers must not rely on parent chat context, raw attachment folders, or memory from another page.

## Required Job Contents

- `slide_id`
- `slide_no`
- `title`
- `page_type`
- `deck_context`
- `local_context`
- `exact_content`
- `input_images`
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
    "navigation_bar_reference.png",
    "chart_001.png"
  ],
  "asset_fidelity_check": "chart_001 appears as supplied; labels preserved",
  "style_check": "matches style_anchor palette and title hierarchy",
  "text_check": "Chinese title and bullets readable",
  "blockers": []
}
```

If a required input image is unavailable or not visible to the backend, the worker must return a blocker and must not use a text-only fallback.

