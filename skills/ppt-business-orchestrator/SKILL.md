---
name: ppt-business-orchestrator
description: "PPT 接单系统总控。读取订单 state.json 和账本，决定下一步调用哪个 skill，维护状态、审批、幂等和失败恢复。不能直接操作企业微信、不能制作 PPT、不能发送业务消息。"
---

# PPT Business Orchestrator

## Purpose

作为接单系统的唯一总控。它根据 `00_state/state.json`、全局账本和订单产物决定下一步动作。

## Inputs

- `00_state/state.json`
- `00_state/events.jsonl`
- `00_state/approvals.jsonl`
- `ledgers/orders.jsonl`
- `ledgers/sent_messages.jsonl`
- `configs/*.json`

## Outputs

- 更新后的 `00_state/state.json`
- 追加写入的 `00_state/events.jsonl`
- 必要时生成 `pending_approval.md`
- 统一结果契约 JSON

## Allowed

- 读取订单状态。
- 校验状态迁移是否合法。
- 检查是否需要 owner approval。
- 检查消息幂等。
- 决定下一步调用哪个 skill。
- 标记 blocked 或 failed。

## Forbidden

- 不直接操作企业微信。
- 不直接发送消息。
- 不直接报价、接单、拒单或交付。
- 不直接制作 PPT。
- 不绕过 `chat_coverage_report.md`、`requirements.json`、`qa_report.md` 等硬门槛。

## Hard Rules

1. 所有业务消息默认禁止发送。
2. 只有固定询单消息可以在白名单联系人、白名单时间、每日次数限制内自动发送。
3. 所有订单必须进入 `WAITING_OWNER_CONFIRMATION`，不存在自动接单路径。
4. 中断恢复必须从 `state.json` 和账本恢复。
5. 每次更新 state 前必须读取 `configs/state_machine.json`，校验状态转移、required artifacts 和 approval 要求。

## Result Contract

```json
{
  "status": "success",
  "confidence": "high",
  "evidence_files": [
    "00_state/state.json"
  ],
  "next_action": "call_wecom_computer_use_operator",
  "requires_owner_approval": false
}
```
