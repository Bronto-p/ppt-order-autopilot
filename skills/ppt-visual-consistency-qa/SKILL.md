---
name: ppt-visual-consistency-qa
description: "PPT 视觉一致性质检层。检查 style drift、asset fidelity、navigation consistency、locked elements、text readability 和 slide worker blockers，生成 visual_qa_result.json。"
---

# PPT Visual Consistency QA

## Purpose

在 assembly 前检查所有 output mode 的页面是否符合样稿/源稿锚点、模板母版、导航条、可编辑性和客户资产 fidelity 要求。

## Inputs

- `03_requirements/production_contract.json`
- `04_sample/approved_sample_reference.json`
- `04_sample/style_kit/*`
- `05_production/slide_jobs/slide_jobs.json`
- `05_production/slide_run_state.json`
- `05_production/slide_jobs/slide_XX/finalization.json`
- `05_production/origin_image/*.png`

## Outputs

- `05_production/visual_qa_result.json`
- `06_qa/visual_consistency_report.json`
- `06_qa/asset_fidelity_report.json`
- `06_qa/style_drift_report.json`
- `06_qa/navigation_consistency_report.json`
- 统一结果契约 JSON

## Checks

- Required client assets are visible.
- Strict assets were not redrawn as lookalikes.
- Style matches `style_anchor.png`.
- Template and title hierarchy match `template_master.png`.
- Navigation geometry is an exact pixel match to the locked overlay; `medium` is not a passing result.
- Active section highlight is correct.
- Locked logo/footer/page-number regions stay stable.
- Chinese text is readable.
- Worker result has no blockers.
- Source text/data changes stay inside `content_change_policy`.
- Hybrid/native modes include their required editable artifacts and rendered preview.
- Composition is presentation-quality: reject generic UI-card grids, unexplained empty space, missing subject visuals, weak hierarchy, and invented decorative copy.

## Hard Rules

1. Any failed strict asset fidelity check blocks assembly.
2. Any worker blocker blocks assembly.
3. Navigation mismatch blocks pages that require navigation.
4. `visual_qa_result.json` must be `pass` before final QA can pass.
5. 有 locked chrome 的页必须先验证 `finalization.json`：overlay hash 正确、safe zone 无不透明像素、opaque pixels 在最终图中精确保留。
6. 导航不一致属于 finalization/packaging 错误，优先重新合成，不消耗生图重试次数。
