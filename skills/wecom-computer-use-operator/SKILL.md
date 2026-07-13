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
- 样稿/交付发送时：`file_send_manifest.json`

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
10. 在 file-send manifest 与对应 approval 均有效时，附加并发送样稿、成品或改稿文件。

## Forbidden Actions

1. 不允许自由选择联系人。
2. 不允许主动点陌生群。
3. 不允许自行决定接单。
4. 不允许自行报价。
5. 不允许承诺截止时间。
6. 不允许发送没有 `send_sample`、`send_final_delivery` 或 `send_revision_response` approval 的文件。
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

## File Send Gate

文件发送使用同样的 two-phase protocol：

1. 读取 manifest，校验 order、contact、purpose 与 approval action 一致。
2. 重新计算本地消息和每个文件的 sha256；任一不匹配立即 blocked。
3. `prepare_file_send` 只打开正确联系人、输入消息并附加 manifest 中的文件，不发送；保存 pre-send screenshot。
4. `commit_file_send` 再次核对联系人、消息、附件文件名、approval 与重复发送 ledger，然后发送。
5. 保存 post-send screenshot，写入 sent-message ledger；final/revision delivery 还要生成 `delivery_receipt.json`。

不得用 UI 中“看起来是同名文件”替代本地 hash 校验，也不得在 approval 后临时替换附件。

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
