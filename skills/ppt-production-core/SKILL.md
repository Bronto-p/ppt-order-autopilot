---
name: ppt-production-core
description: "PPT 生产核心层。只读取 production_contract.json，生成页面设计、全页图、PPTX 和 PDF。不能直接读取企业微信或自行补需求。"
---

# PPT Production Core

## Purpose

从干净的 `production_contract.json` 生产 PPT。它可以对接现有的 `ppt-complete-workflow`，但不能跳过订单系统的需求和审批层。

## Inputs

- `03_requirements/production_contract.json`
- `02_attachments_raw/from_chat/*`
- `02_attachments_raw/from_customer/*`
- `00_state/approvals.jsonl`

## Outputs

- `05_production/origin_image/`
- `05_production/prompts/`
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

