---
name: codex-attachment-intake
description: "PPT 直接文件入口。用户在 Codex 附上文件，或明确要求处理 workspace 中的 PPT/PDF/Word/图片/文案时使用；负责确定性暂存、hash、证据索引、建单和 promotion，不伪造企业微信记录。"
---

# Direct File Intake

## Choose Source

- `codex_attachment`：文件由当前 Codex 消息附加。
- `workspace_file`：用户明确指向当前 workspace 中的可读文件。

不要把 workspace 文件伪装成 Codex attachment，也不要因为目录名包含“试稿”而启动客户样稿流程。

## Procedure

1. 运行 `tools/bootstrap_runtime.py`。
2. 先调用：

```bash
python3 tools/init_order.py --order-id <id> --title <title> \
  --execution-mode owner_direct --intake-source <source> \
  --allow-existing --with-templates
```

3. 将 exact owner prompt 写入一个 UTF-8 scratch 文件，然后用确定性工具一次性完成 hash、复制、索引、promotion、owner instruction approval 和 active-order 绑定：

```bash
python3 tools/register_direct_intake.py <order_dir> \
  --source-type <codex_attachment|workspace_file> \
  --prompt-file <exact_prompt.txt> --file <path> [--file <path> ...]
```

4. 工具会 promote 到 `02_attachments_raw/from_codex/` 或 `from_workspace/`，并生成真实 `message_index.jsonl`、`attachment_index.jsonl`、`coverage_result.json` 和 coverage report。直接文件来源不需要假截图或上下滚动锚点。
5. 只有工具返回 `runnable=true` 时才运行 `autopilot.py commit ... --to DIRECT_INTAKE_STAGED`。若已有其他 active order，新订单会进入 `pending_order_ids`；不覆盖当前订单，也不继续生产。不要重新手写这些 runtime 文件。

读不到文件或 hash 不一致时 blocker。此 skill 不解释最终需求、不生产 PPT。
