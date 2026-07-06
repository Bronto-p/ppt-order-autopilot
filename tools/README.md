# Tools

这里放最小本地工具。当前只提供骨架级工具，不做企业微信 UI 自动化。

## init_order.py

创建标准订单目录：

```bash
python3 tools/init_order.py --title "大学生创新创业项目路演PPT"
```

可选指定客服：

```bash
python3 tools/init_order.py --title "商业计划书" --contact "客服A"
```

复制订单模板和 schema：

```bash
python3 tools/init_order.py --title "商业计划书" --contact "客服A" --with-templates
```

`init_order.py` 会初始化本地运行时 ledger 文件：

```text
ledgers/orders.jsonl
ledgers/sent_messages.jsonl
ledgers/ui_actions.jsonl
ledgers/approvals.jsonl
```

这些 JSONL 文件被 `.gitignore` 忽略，不能提交到公开仓库。

## validate_order.py

按 gate 校验订单硬门槛：

```bash
python3 tools/validate_order.py orders/2026-07-05_001_商业计划书 --gate chat_capture
python3 tools/validate_order.py orders/2026-07-05_001_商业计划书 --gate decision
```

支持的 gate：

- `base`
- `chat_capture`
- `briefing`
- `decision`
- `production`
- `contract_accuracy`
- `sample_accuracy`
- `slide_jobs`
- `visual_qa`
- `qa`
- `delivery`

## Minimal Runbook

1. `init_order.py --with-templates` 创建订单。
2. 写入真实 `coverage_result.json`、`message_index.jsonl`、`attachment_index.jsonl` 后跑 `--gate chat_capture`。
3. 写入 `requirements.json` 后跑 `--gate briefing`。
4. 写入 `pending_approval.json` 和 `decision.md` 后跑 `--gate decision`。
5. 写入 approved approval record 和 `production_contract.json` 后跑 `--gate production`。
6. 跑 `--gate contract_accuracy` 确认 contract 足够精确。
7. 样稿通过并生成 `style_master/` 后跑 `--gate sample_accuracy`。
8. 生成 `slide_jobs.json` 和 `prompts/slide_XX.json` 后跑 `--gate slide_jobs`。
9. 所有 slide worker 完成并生成 `visual_qa_result.json` 后跑 `--gate visual_qa`。
10. 写入交付物、`qa_result.json` 和 `qa_report.md` 后跑 `--gate qa`。
