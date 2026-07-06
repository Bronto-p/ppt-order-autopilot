---
name: ppt-slide-job-builder
description: "PPT 单页 job 构建层。把 production_contract.json 拆成每页一个 self-contained slide_XX.json，明确 exact content、input images、style refs、template refs、fidelity rules、backend、worker policy 和 QA requirements。"
---

# PPT Slide Job Builder

## Purpose

把生产契约拆成一页一个完整 job。每个 subagent 只看自己的 job，也能准确生产该页。

## Inputs

- `03_requirements/production_contract.json`
- `04_sample/approved_sample_reference.json`
- `04_sample/style_master/*`
- `00_state/approvals.jsonl`

## Outputs

- `05_production/production_blueprint.json`
- `05_production/slide_jobs.json`
- `05_production/prompts/slide_01.json`
- `05_production/prompts/slide_02.json`
- `05_production/slide_run_state.json`
- 统一结果契约 JSON

## Job Requirements

Each slide job must include:

- exact slide-ready content.
- style anchor input image.
- template master input image.
- navigation reference when needed.
- page family reference.
- strict client assets assigned to that slide.
- asset fidelity rules.
- backend and image input requirements.
- worker reasoning level.
- QA requirements.

## Hard Rules

1. No low reasoning level for customer production.
2. A required client asset must appear in `input_images`.
3. A required client asset must have a fidelity rule.
4. Missing required image means blocker, not text fallback.
5. Parent agent must not generate slide images directly.

