# UI Operation Policy

`wecom-computer-use-operator` 是受限操作层。它只能执行白名单动作，不能自行做业务判断。

## 1. 允许动作

1. 打开企业微信。
2. 定位白名单客服。
3. 校验当前窗口联系人名称。
4. 发送白名单固定询单话术。
5. 发送已经人工批准的话术。
6. 检查客服是否在询单后回复。
7. 打开客服发来的聊天记录。
8. 从聊天记录顶部开始截图、OCR 和滑动。
9. 下载聊天中的附件。
10. 保存截图、OCR 文本、附件路径和 UI 操作日志。

## 2. 禁止动作

1. 不允许自由选择联系人。
2. 不允许主动点击陌生群或陌生客户。
3. 不允许自行决定接单。
4. 不允许自行报价。
5. 不允许承诺截止时间。
6. 不允许发送样稿或成品。
7. 不允许删除、撤回、转发聊天。
8. 不允许修改企业微信设置。
9. 不允许在没有人工批准的情况下发送业务消息。

## 3. Two-phase Send

业务消息发送必须拆成两步：

```text
prepare_message
  - 定位联系人。
  - 输入消息到聊天输入框。
  - 不发送。
  - 保存 pre_send_screenshot。
  - 写入 ui_action: draft_prepared。

commit_send
  - 再次确认联系人。
  - 再次确认输入框文本 hash 等于 pending_approval.json draft_sha256。
  - 再次确认 approval_id 存在且 approved。
  - 发送。
  - 保存 post_send_screenshot。
  - 写入 sent_messages.jsonl。
```

## 4. 发送前校验

发送任何消息前必须通过四项检查：

```text
1. 当前应用是企业微信。
2. 当前聊天窗口联系人名称完全匹配 allowed_contacts。
3. 消息内容匹配可自动发送规则，或存在人工批准记录。
4. sent_messages.jsonl 中没有同联系人、同内容、短时间内的重复发送记录。
```

## 5. UI 操作日志

每次 UI 动作都写入 `ledgers/ui_actions.jsonl`：

```json
{
  "event": "ui_action",
  "action": "send_message",
  "contact": "客服A",
  "order_id": "2026-07-05_001",
  "message_hash": "sha256:...",
  "approval_id": "appr_001",
  "timestamp": "2026-07-05T10:30:00+08:00",
  "status": "success"
}
```

## 6. 失败策略

遇到以下情况必须停止：

- 当前联系人无法确认。
- 企业微信窗口焦点不稳定。
- 聊天记录打不开。
- 滚动到顶部失败。
- 相邻截图重叠检查失败。
- 关键附件下载失败。
- 即将发送的消息没有匹配到自动发送规则或人工批准记录。
