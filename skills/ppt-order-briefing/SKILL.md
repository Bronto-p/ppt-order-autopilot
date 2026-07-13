---
name: ppt-order-briefing
description: "PPT 订单需求提取层。从聊天 transcript、message index 和附件索引中提取结构化需求、缺失项和冲突项。每个需求字段必须有 evidence。"
---

# PPT Order Briefing

## Purpose

把聊天记录和附件整理成可决策的订单 brief。

## Inputs

- `01_chat/chat_coverage_report.md`
- `01_chat/chat_transcript.md`
- `01_chat/message_index.jsonl`
- `02_attachments_raw/attachment_index.jsonl`
- `02_attachments_raw/failed_downloads.md`

## Outputs

- `03_requirements/order_brief.md`
- `03_requirements/requirements.json`
- `03_requirements/missing_questions.md`
- `03_requirements/conflicts.md`
- 统一结果契约 JSON

## Required Fields

字段以 `templates/order/03_requirements/requirements.template.json` 为初始模板。机器约束应逐步迁移到一个真正的 JSON Schema，不要在 skill 里另写一套字段口径。

## Evidence Rule

每个字段必须包含：

- `value`
- `evidence`
- `confidence`
- `required`

没有证据的字段必须标记为 `missing` 或 `inferred`。

## Conflict Rule

任何冲突都不允许自行按最后一句覆盖。必须写入 `conflicts.md`，并生成待审批追问话术。

## Result Contract

```json
{
  "status": "blocked",
  "confidence": "high",
  "evidence_files": [
    "03_requirements/requirements.json",
    "03_requirements/missing_questions.md"
  ],
  "next_action": "call_ppt_order_decision",
  "requires_owner_approval": true,
  "blocked_reason": "missing_required_fields"
}
```
