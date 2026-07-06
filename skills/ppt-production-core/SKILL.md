---
name: ppt-production-core
description: "PPT 生产核心层。只读取 production_contract.json，生成页面设计、全页图、PPTX 和 PDF。不能直接读取企业微信或自行补需求。"
---

# PPT Production Core

## Purpose

从 slide job bundles 生产 PPT。production core 不直接浏览 raw 附件，也不由 parent agent 直接做页面；它只负责读取每页 job bundle、调度 one-slide workers、收集 render result、QA 和 assembly。

## Inputs

- `03_requirements/production_contract.json`
- `05_production/slide_jobs/slide_jobs.json`
- `05_production/slide_jobs/slide_XX/job.json`
- `05_production/slide_jobs/slide_XX/prompt.md`
- `05_production/slide_jobs/slide_XX/input_images/*`
- `00_state/approvals.jsonl`

## Outputs

- `05_production/origin_image/`
- `05_production/production_blueprint.json`
- `05_production/slide_jobs/*/render_result.json`
- `05_production/slide_run_state.json`
- `05_production/visual_qa_result.json`
- `05_production/deck_spec.json`
- `05_production/outline.md`
- `05_production/speech.md`
- `05_production/*.pptx`
- `05_production/*.pdf`
- 统一结果契约 JSON

## Hard Rules

1. 不读取企业微信。
2. 不自行解释原始聊天。
3. 不自行补缺失需求。
4. 不使用未在 contract 中批准的客户素材。
5. 生产前必须存在人工批准记录。
6. 只能读取 `slide_jobs/` 内的 job bundle 和本页 `input_images/`。
7. 每页必须由生图模型生成完整 slide image。
8. 每页必须由独立 subagent 处理，parent agent 不直接生成页面。
9. 每个 slide job 必须 self-contained。
10. 禁止 HTML/CSS、SVG、Pillow、native python-pptx layout 作为页面生成路径。
11. required image 不在本页 `input_images/` 时必须 blocked，不能 text-only fallback。

## Integration Note

现有目录 `../full ppt making workflow/skills/ppt-complete-workflow` 可以作为生产后端。接入时建议做一层 adapter：

```text
production_contract.json
        |
        v
ppt-complete-workflow compatible order folder
        |
        v
ppt_plan.md / production deck
```
