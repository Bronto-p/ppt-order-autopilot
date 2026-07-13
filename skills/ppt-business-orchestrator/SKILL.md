---
name: ppt-business-orchestrator
description: "PPT 接单系统总控。用于启动、继续、恢复或定时检查 PPT Order Autopilot；读取持久化状态和账本，选择下一阶段 skill，维护审批、幂等和中断恢复。"
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
- 更新后的 `ledgers/automation_state.json`
- 询单/promotion 账本记录（通过对应 intake skill）
- 追加写入的 `00_state/events.jsonl`
- 必要时生成 `pending_approval.md`
- 统一结果契约 JSON

## Entry Rule

当用户要求运行、继续、恢复或监控系统时，从 `docs/AGENT_RUN_LOOP.md` 开始。没有订单时，根据用户给定的入口选择企业微信询单/回复检查，或者 Codex 附件建单。不能要求用户手工整理订单文件夹。

询单前使用 `inbox/{inquiry_id}/` 和全局 automation state。打开回复并获得足够的订单身份后，初始化订单目录、迁移 inquiry artifacts、记录 promotion event，再切换到订单 state machine。

## Run Loop

1. 读取 live config、automation state 和 side-effect ledgers。
2. 对未确认的外部动作先做 reconciliation，禁止盲目重试。
3. 无 active order 时执行询单、检查回复或 inquiry promotion。
4. 有 active order 时读取订单 state、最新事件、approval 和机器状态定义。
5. 验证当前 required artifacts，选择并调用一个 skill。
6. 校验该 skill 的输出 gate，追加 event，原子更新 state。
7. 自动继续，直到 owner approval、hard blocker、no-reply stop 或 closeout。

## Context Budget

- 常驻上下文只包含：automation state、active order state、最新事件、有效审批、当前状态定义和下一阶段的输入摘要。
- 每次只加载一个阶段 skill 及其直接 schema/template。不预读全部 skills/docs。
- raw 聊天、客户附件和历史 worker 输出按路径引用；只在当前 skill 明确需要时打开。
- 单页 worker 只能获得该页 bundle。总控保留 deck-level state、跨页 QA 和 assembly 责任。

## State Routing

| State / entry | Load exactly this owner |
| --- | --- |
| Codex attachments before order | `codex-attachment-intake` |
| scheduled ask / reply / WeCom capture | `wecom-computer-use-operator`, then `wecom-chat-recorder` |
| transcript ready through missing/conflict analysis | `ppt-order-briefing` |
| owner decision and customer commitment draft | `ppt-order-decision` |
| accepted scope to production contract | `ppt-production-contract-builder` |
| sample branch | `ppt-sample-manager` |
| approved visual source to style kit | `ppt-style-master-builder` |
| contract/style kit to page bundles | `ppt-slide-job-packager` |
| page dispatch/finalization/assembly | `ppt-production-core` |
| cross-slide visual checks | `ppt-visual-consistency-qa` |
| final QA, manifest, delivery, closeout | `ppt-qa-delivery` |

## Codex Automation Binding

用户要求自动唤醒查单时，创建或更新一个 workspace-level Codex Automation，不为每个订单新建 automation。

1. 先读取 live `ask_schedule.json` 和 automation state。缺真实联系人或排程时只询问一次。
2. 查找 Codex automation list/update capability，用它对账并创建/更新 automation；不用文档中的原始指令代替工具调用。当前宿主没有该 capability 时，记录明确 blocker，不声称已建立无人值守监控。
3. 每次只调度最早的下一个 due time（daily ask 或 reply check）；唤醒后再用同一 automation ID 更新到后续 due time。
4. Automation prompt 固定为版本化文本：resume autopilot，reconcile side effects first，无到期动作则安静结束，否则跑到 owner gate/blocker/closeout。
5. Fingerprint 输入是 `{"workspace": absolute_path, "schedule": live_schedule_object, "task_prompt_version": 1}`，使用 UTF-8、sorted keys、compact JSON 后 SHA-256。Deterministic name 是 `ppt-order-autopilot-{sha256(absolute_workspace)[:12]}`。
6. 在外部创建前，先原子写入 `automation_binding` intent：`status=pending`、deterministic name、fingerprint、next-due schedule、prompt，`automation_id=null`。
7. 先 list/reconcile deterministic name：已存在就 adopt ID 并 update，不存在才 create。Create 成功后将同一 binding 更新为 `status=active` 和真实 ID。如在 create 后中断，resume 依靠 pending intent + deterministic name 找回已创建对象。
8. 已绑定且 fingerprint 一致时只更新 next due，不创建新 ID。修改或删除 automation 后同步更新绑定。

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
