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
- navigation geometry matches `navigation_bar_reference.png`.
- active section highlight is correct.
- title hierarchy is consistent.
- locked logo/footer/page-number zones are stable.
- Chinese text is readable and not garbled.
- every accepted slide has a worker result with no blockers.

