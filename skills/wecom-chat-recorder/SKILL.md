---
name: wecom-chat-recorder
description: "企业微信聊天采集层。负责从聊天记录顶部到底部截图、OCR、重叠校验、生成 transcript、coverage report、message index 和 attachment index。发现断层必须停止。"
---

# WeCom Chat Recorder

## Purpose

把客服发来的聊天记录采集成可审计、可追溯、可恢复的订单输入。

## Inputs

- `01_chat/screenshots/*.png`
- `01_chat/ocr/*.txt`
- `02_attachments_raw/from_chat/*`

## Outputs

- `01_chat/chat_transcript.md`
- `01_chat/chat_coverage_report.md`
- `01_chat/coverage_result.json`
- `01_chat/message_index.jsonl`
- `01_chat/screenshots/screen_001.meta.json`
- `02_attachments_raw/attachment_index.jsonl`
- `02_attachments_raw/failed_downloads.md`
- 统一结果契约 JSON

## Capture Protocol

1. 打开聊天记录后先回到顶部。
2. 顶部稳定确认至少两次。
3. 记录 `top_anchor`。
4. 每屏截图、OCR、写 meta。
5. 每屏保存 `screen_001.png`、`screen_001.ocr.txt`、`screen_001.meta.json`。
6. 每次下滑保留 20%-30% 重叠。
7. 相邻屏幕必须能对上。
8. 记录 `bottom_anchor`。
9. 生成 Markdown 覆盖报告和机器可读 `coverage_result.json`。

## Hard Rules

- 没有 `chat_coverage_report.md` 和 `coverage_result.json`，不能进入需求提取。
- 相邻屏幕重叠失败，状态变为 `CAPTURE_GAP_DETECTED`。
- 关键附件下载失败时必须写入 `failed_downloads.md`。
- 不允许自行判断订单是否能接。

## Result Contract

```json
{
  "status": "success",
  "confidence": "high",
  "evidence_files": [
    "01_chat/chat_coverage_report.md",
    "01_chat/message_index.jsonl",
    "02_attachments_raw/attachment_index.jsonl"
  ],
  "next_action": "call_ppt_order_briefing",
  "requires_owner_approval": false
}
```
