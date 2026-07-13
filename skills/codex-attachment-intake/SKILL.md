---
name: codex-attachment-intake
description: "Codex 附件订单入口。当用户在 Codex 附上 PPT/PDF/Word/图片/文案并要求建单时，负责确定性暂存、hash、证据索引和 promotion；不伪造企业微信记录。"
---

# Codex Attachment Intake

## Inputs

- 当前 Codex 用户消息原文。
- 本消息中真实可读的附件。
- `templates/inquiry/*`、`ledgers/automation_state.json` 和 `ledgers/inquiries.jsonl`。

## Deterministic Evidence IDs

1. 对附件按稳定文件名排序，计算每个 SHA-256。
2. 用 compact JSON `{"prompt": <exact user text>, "attachments": [{"name": ..., "sha256": ...}]}`（UTF-8、keys 排序、无多余空格）计算 source digest。
3. `message_id = codex_prompt_{digest前12位}`，`inquiry_id = codex_{digest前16位}`。这是 Codex 来源 ID，不是伪造的聊天 ID。
4. `attachment_id = codex_att_{file_sha256前12位}`。同 hash 重跑复用现有文件和索引。

## Procedure

1. 运行 `tools/bootstrap_runtime.py`。
2. 建立/复用 `inbox/{inquiry_id}/downloads/`，原子复制附件并校验 hash。
3. 将 exact Codex prompt 原文原子写入 `inbox/{inquiry_id}/source_prompt.txt`，记录 path/hash；然后写入 inquiry state 和 inquiry ledger。将它记录为一条 source message，`screen_ids=[]`。
4. 为每个附件写入 `source_message_id` 和 `download_status=success`。不生成假截图、OCR 或 WeCom sender。
5. 获得稳定 topic 后，先在 `inquiry_state.json` 写入 `promotion_intent={order_id,title,status:pending}` 并追加 ledger event。Order ID 一旦保存就不重新分配。
6. Resume 时先按 intent order ID + title 查找已有目录和 orders ledger。存在则复用；不存在才调用 `tools/init_order.py --order-id {intent.order_id} --title {intent.title} --allow-existing --with-templates`。创建后立即将 intent 改为 `order_created`。
7. Promote 到 `02_attachments_raw/from_codex/`，生成 `message_index.jsonl`、`attachment_index.jsonl` 和 `coverage_result.json`。
8. 在 inquiry ledger 追加 promotion，并在 orders ledger 追加 `event=inquiry_promoted`；然后将 intent 改为 `recorded`。设置 `active_order_id`；其他同次拆分订单进入 `pending_order_ids`。每步重跑前均按 inquiry/order ID 对账，已存在记录不重复追加。

## Hard Rules

- 用户不需要手工创建或填充仓库文件夹。
- 读不到的附件是 blocker；不得仅根据文件名继续。
- 附件和 prompt 的 hash/ID 一旦记录不得改写。
- 这一 skill 只负责 intake 与 promotion，不推断最终需求、不报价、不生产 PPT。
