# Visual Consistency QA

Standard PPT QA checks that files open and text is readable. Image-based PPT production also needs visual consistency checks.

## Required Reports

```text
06_qa/visual_consistency_report.json
06_qa/asset_fidelity_report.json
06_qa/style_drift_report.json
06_qa/navigation_consistency_report.json
```

`05_production/visual_qa_result.json` can summarize those reports for the validator.

## Checks

- required assets are visible and not redrawn as lookalikes.
- style drift from `style_anchor.png` is within tolerance.
- navigation geometry is an exact pixel match to the selected locked overlay; `medium` does not pass.
- every registered overlay matches one invariant skeleton outside declared dynamic regions, so consistency is checked before per-slide bundling as well as after finalization.
- active section highlight is correct.
- title hierarchy is consistent.
- locked logo/footer/page-number zones are stable.
- Chinese text is readable and not garbled.
- every accepted slide has a worker result with no blockers.
- every accepted slide identifies an accepted attempt preserved in `slide_run_state.json`.
- every final slide has a parent-owned `finalization.json` that links the raw attempt to the canonical image and verifies overlay hash, safe zone, and opaque pixels.

Navigation/chrome failure is a packaging/finalization defect when the raw page body is otherwise correct. Reapply the approved overlay first; do not consume an image-generation repair attempt for a deterministic compositing error.
