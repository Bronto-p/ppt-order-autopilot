---
name: ppt-order-decision
description: "PPT 接单建议层。根据 requirements、missing questions、conflicts 和附件状态生成接单建议与 pending approval 话术。不能自动接单、拒单、报价或发送消息。"
---

# PPT Order Decision

## Purpose

给出接单建议和下一步话术草稿，但不执行发送。

## Inputs

- `03_requirements/order_brief.md`
- `03_requirements/requirements.json`
- `03_requirements/missing_questions.md`
- `03_requirements/conflicts.md`
- `02_attachments_raw/attachment_index.jsonl`
- `02_attachments_raw/failed_downloads.md`

## Outputs

- `03_requirements/decision.md`
- `03_requirements/pending_approval.md`
- 统一结果契约 JSON

## Recommendation Values

- `suggest_accept`
- `ask_then_accept`
- `cautious`
- `suggest_reject`

## Hard Rules

1. 不自动接单。
2. 不自动拒单。
3. 不自动报价。
4. 不自动发送。
5. 缺页数、截止、价格、样稿要求时，默认进入追问。
6. 有未解决冲突时，默认进入追问。

## Result Contract

```json
{
  "status": "success",
  "confidence": "medium",
  "evidence_files": [
    "03_requirements/decision.md",
    "03_requirements/pending_approval.md"
  ],
  "next_action": "wait_for_owner_confirmation",
  "requires_owner_approval": true
}
```

