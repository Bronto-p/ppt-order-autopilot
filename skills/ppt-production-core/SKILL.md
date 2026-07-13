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
- `05_production/slide_jobs/slide_XX/attempts/*`
- `00_state/approvals.jsonl`

## Outputs

- `05_production/origin_image/`
- `05_production/production_blueprint.json`
- `05_production/slide_jobs/*/render_result.json`
- `05_production/slide_jobs/*/finalization.json`
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
7. 每页主体视觉必须由生图模型生成完整 slide canvas。固定导航、logo、页脚和页码可由 parent 在生图后使用已批准的透明 overlay 像素级合成。
8. 每页必须由独立 subagent 处理，parent agent 不直接生成页面。
9. 每个 slide job 必须 self-contained。
10. 禁止 HTML/CSS、SVG、Pillow、native python-pptx layout 作为页面主体生成路径。Pillow 仅可用于已批准 locked chrome 的确定性 alpha composite，不可增写页面内容。
11. required image 不在本页 `input_images/` 时必须 blocked，不能 text-only fallback。

## Dispatch And Repair Loop

1. 为每页读取 immutable base job，创建 attempt snapshot，再派发一个独立 subagent。
2. worker 只返回 immutable raw render result；parent agent 对 exact content、素材、文字、风格和页面结构做 QA。
3. 通过则记录 `accepted_attempt`。`locked_chrome.mode=post_generation_composite` 时，parent 运行 `tools/composite_locked_chrome.py`，校验 overlay hash、safe box 和像素一致性，生成 canonical `origin_image/slide_XX.png` 和 `finalization.json`。
4. 无 locked chrome 时，parent 仍然保留 raw output，复制到 canonical path 并写入 `finalization.json`。worker 永远不直接覆盖 canonical output。
5. 未通过则保存失败分类和证据，创建窄范围 repair job，再派一个单页 repair worker。
6. 缺真实素材或内容冲突立即 blocked；backend 暂时失败、文字错误、style drift 或 layout error 才能自动重试。
7. 不覆盖历史 attempt，不超过 base job 的 `max_attempts`，超过后进入 owner review。
