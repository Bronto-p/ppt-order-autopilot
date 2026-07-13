---
name: ppt-business-orchestrator
description: "PPT 接单系统总控。读取订单 state.json 和账本，决定下一步调用哪个 skill，维护状态、审批、幂等和失败恢复。不能直接操作企业微信、不能制作 PPT、不能发送业务消息。"
---

# PPT Business Orchestrator

## Purpose

作为接单系统的唯一总控。它同时管理订单出现前的全局 automation/inquiry state，以及订单创建后的 `00_state/state.json`。它根据持久化状态、账本和订单产物决定下一步动作。

## Inputs

- `ledgers/automation_state.json`
- `ledgers/inquiries.jsonl`
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

## Entry Rule

当用户要求运行、继续或恢复系统时，从 `docs/AGENT_RUN_LOOP.md` 开始。没有订单时不能等待用户整理文件；必须从企业微信询单或回复检查分支开始。

询单前使用 `inbox/{inquiry_id}/` 和全局 automation state。打开回复并获得足够的订单身份后，初始化订单目录、迁移 inquiry artifacts、记录 promotion event，再切换到订单 state machine。

## Run Loop

1. 读取 live config、automation state 和 side-effect ledgers。
2. 对未确认的外部动作先做 reconciliation，禁止盲目重试。
3. 无 active order 时执行询单、检查回复或 inquiry promotion。
4. 有 active order 时读取订单 state、最新事件、approval 和机器状态定义。
5. 验证当前 required artifacts，选择并调用一个 skill。
6. 校验该 skill 的输出 gate，追加 event，原子更新 state。
7. 自动继续，直到 owner approval、hard blocker、no-reply stop 或 closeout。

## Recovery Rule

- 不依赖对话记忆决定是否已发送、下载、派发或交付。
- 先检查 ledger、文件 hash、worker result 和当前 UI，再决定重试。
- 活跃 lock 不允许抢占；过期 lock 只有在对账后才可回收。
- 如果上次运行在外部操作中断，优先确认副作用是否已经发生，而不是重新执行。

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
