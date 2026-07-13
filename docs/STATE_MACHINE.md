# State Machine

每一单必须有独立的 `00_state/state.json`。任何 agent 中断后，都必须从该文件恢复，而不是依赖聊天上下文。

## 1. 主状态

```text
IDLE
SCHEDULED_ASK
ASK_SENT
WAITING_REPLY_2M
WAITING_REPLY_5M
WAITING_REPLY_10M
WAITING_REPLY_30M
WAITING_REPLY_1H
WAITING_REPLY_2H
NO_REPLY_STOPPED
REPLY_DETECTED
OPENING_CHAT_RECORD
CAPTURING_CHAT_FROM_TOP
CAPTURE_GAP_DETECTED
SAVING_ATTACHMENTS
BUILDING_TRANSCRIPT
EXTRACTING_ORDER_BRIEF
NEEDS_MISSING_QUESTIONS
READY_FOR_OWNER_DECISION
WAITING_OWNER_CONFIRMATION
ASK_CUSTOMER_OR_ACCEPT_ORDER
SAMPLE_REQUIRED
DIRECT_PRODUCTION_ALLOWED
SAMPLE_PRODUCTION
SAMPLE_QA
WAITING_OWNER_SAMPLE_SEND_CONFIRMATION
SAMPLE_SENT
WAITING_CLIENT_SAMPLE_FEEDBACK
SAMPLE_FEEDBACK_AMBIGUOUS
SAMPLE_REVISION_REQUESTED
SAMPLE_APPROVED
FULL_PRODUCTION
FULL_QA
DELIVERY_READY
WAITING_OWNER_DELIVERY_CONFIRMATION
DELIVERY_SENT
WAITING_CLIENT_FEEDBACK
CLIENT_ACCEPTED
ORDER_CLOSED
REVISION_LOOP
FAILED_BLOCKED
```

机器可执行版本在 `configs/state_machine.json`。该文件不是单纯状态列表；每个 state 都必须定义：

```text
allowed_next
required_artifacts
requires_owner_approval
```

orchestrator 每次改状态前都要验证旧状态是否允许转到新状态，并确认所需产物和 approval 已存在。

## 2. 询单分支

```text
IDLE
  -> SCHEDULED_ASK
  -> ASK_SENT
  -> WAITING_REPLY_2M
  -> WAITING_REPLY_5M
  -> WAITING_REPLY_10M
  -> WAITING_REPLY_30M
  -> WAITING_REPLY_1H
  -> WAITING_REPLY_2H
  -> NO_REPLY_STOPPED
```

如果任一检查轮发现客服回复：

```text
WAITING_REPLY_*
  -> REPLY_DETECTED
```

## 3. 聊天采集分支

```text
REPLY_DETECTED
  -> OPENING_CHAT_RECORD
  -> CAPTURING_CHAT_FROM_TOP
  -> SAVING_ATTACHMENTS
  -> BUILDING_TRANSCRIPT
```

如果相邻屏幕重叠检查失败：

```text
CAPTURING_CHAT_FROM_TOP
  -> CAPTURE_GAP_DETECTED
```

`CAPTURE_GAP_DETECTED` 是硬停止状态。必须重新采集或人工确认覆盖范围，不能继续需求提取。

## 4. 需求和决策分支

```text
BUILDING_TRANSCRIPT
  -> EXTRACTING_ORDER_BRIEF
  -> NEEDS_MISSING_QUESTIONS
  -> WAITING_OWNER_CONFIRMATION
```

或者：

```text
BUILDING_TRANSCRIPT
  -> EXTRACTING_ORDER_BRIEF
  -> READY_FOR_OWNER_DECISION
  -> WAITING_OWNER_CONFIRMATION
```

## 5. 样稿分支

```text
WAITING_OWNER_CONFIRMATION
  -> SAMPLE_REQUIRED
  -> SAMPLE_PRODUCTION
  -> SAMPLE_QA
  -> WAITING_OWNER_SAMPLE_SEND_CONFIRMATION
  -> SAMPLE_SENT
  -> WAITING_CLIENT_SAMPLE_FEEDBACK
  -> SAMPLE_APPROVED
  -> FULL_PRODUCTION
```

样稿是否需要不能默认。必须满足至少一个条件：

- 聊天明确要求样稿。
- 客服明确要求样稿。
- 你明确确认先走样稿。

样稿 QA 通过后只是进入“待 owner 批准发送”，不能直接进正稿。发送后必须等客户明确通过；明确小修返回样稿生产，涉及价格、截止、页数或整体风格重置才再问 owner。

## 6. 正稿分支

```text
WAITING_OWNER_CONFIRMATION
  -> DIRECT_PRODUCTION_ALLOWED
  -> FULL_PRODUCTION
  -> FULL_QA
  -> DELIVERY_READY
  -> WAITING_OWNER_DELIVERY_CONFIRMATION
  -> DELIVERY_SENT
  -> WAITING_CLIENT_FEEDBACK
  -> CLIENT_ACCEPTED
  -> ORDER_CLOSED
```

`DELIVERY_READY` 只表示文件准备好了，不表示可以自动发送。

交付后如果客户反馈修改，进入 `REVISION_LOOP`。真正终态是 `ORDER_CLOSED`，不是发送文件本身。

## 7. state.json 契约

```json
{
  "order_id": "2026-07-05_001",
  "state": "WAITING_OWNER_CONFIRMATION",
  "previous_state": "READY_FOR_OWNER_DECISION",
  "fixed_contact": "客服A",
  "last_action": "generated_missing_questions",
  "next_action": "ask_owner_to_confirm_questions",
  "created_at": "2026-07-05T10:03:00+08:00",
  "updated_at": "2026-07-05T10:18:00+08:00",
  "can_send_message": false,
  "requires_owner_approval": true,
  "blocked_reason": null
}
```

`previous_state` 是必填的迁移证据；只有初始 `IDLE` 可以为 `null`。Validator 同时检查 `previous_state -> state` 是否存在于 `allowed_next`，不允许通过省略字段绕过转移规则。
