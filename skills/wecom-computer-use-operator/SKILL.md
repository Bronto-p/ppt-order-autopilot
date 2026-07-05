---
name: wecom-computer-use-operator
description: "企业微信受限 UI 操作层。只能做打开企业微信、定位白名单客服、校验窗口、发送已允许消息、检查回复、打开聊天记录、截图和下载附件。不能做业务判断。"
---

# WeCom Computer Use Operator

## Purpose

使用 Computer Use 操作企业微信，但只作为 UI adapter。它只能执行白名单动作，不能理解订单或做业务判断。

## Inputs

- `configs/allowed_contacts*.json`
- `configs/message_policy*.json`
- `ledgers/sent_messages.jsonl`
- `00_state/state.json`
- 已批准的话术文件或 approval record

## Outputs

- `ledgers/ui_actions.jsonl`
- `ledgers/sent_messages.jsonl`
- `01_chat/screenshots/*.png`
- `01_chat/ocr/*.txt`
- `02_attachments_raw/from_chat/*`
- 统一结果契约 JSON

## Allowed Actions

1. 打开企业微信。
2. 定位固定白名单客服。
3. 校验当前聊天窗口联系人。
4. 发送固定询单话术。
5. 使用 two-phase send 发送已经人工批准的话术。
6. 检查客服是否在询单后回复。
7. 打开客服发来的聊天记录。
8. 截图、OCR、滑动。
9. 下载附件。

## Forbidden Actions

1. 不允许自由选择联系人。
2. 不允许主动点陌生群。
3. 不允许自行决定接单。
4. 不允许自行报价。
5. 不允许承诺截止时间。
6. 不允许发送样稿或成品。
7. 不允许删除、撤回、转发聊天。
8. 不允许修改企业微信设置。

## Send Gate

业务消息必须先 `prepare_message`，再 `commit_send`：

- `prepare_message` 只输入消息，不发送，并保存 `pre_send_screenshot`。
- `commit_send` 再次校验联系人、输入框文本 hash、approval id，然后发送并保存 `post_send_screenshot`。

发送前必须确认：

- 当前应用是企业微信。
- 当前联系人完全匹配 allowed contacts。
- 消息属于自动询单白名单，或存在人工批准记录。
- 没有在幂等窗口内重复发送。

## Stop Conditions

- 当前联系人无法确认。
- 企业微信窗口焦点不稳定。
- 消息无审批记录。
- 聊天记录打不开。
- 下载关键附件失败。

## Result Contract

```json
{
  "status": "blocked",
  "confidence": "high",
  "evidence_files": [
    "ledgers/ui_actions.jsonl"
  ],
  "next_action": "request_owner_review",
  "requires_owner_approval": true,
  "blocked_reason": "contact_not_confirmed"
}
```
