---
name: ppt-order-decision
description: "PPT 客户订单决策层。根据 requirements、缺失项、冲突和附件状态生成接单建议与待确认话术；仅用于 customer_order，不用于 owner-direct 内部制作。"
---

# PPT Order Decision

只处理 `execution_mode=customer_order`。生成 `decision.md`、`pending_approval.md/json`，但不接单、拒单、报价或发送。

缺客户订单必需字段、存在冲突或需要客户承诺时进入 owner gate。`owner_direct` 应由 orchestrator 记录用户原始指令为 `owner_direct_instruction`，直接进入 production contract builder；不得伪造 customer decision 或 send approval。
