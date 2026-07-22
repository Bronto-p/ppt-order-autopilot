# Tools

这里放最小本地工具。当前只提供骨架级工具，不做企业微信 UI 自动化。

## bootstrap_runtime.py

幂等初始化全局 automation state 和所有 JSONL ledgers，不覆盖已有运行数据：

```bash
python3 tools/bootstrap_runtime.py
```

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

Codex 中直接制作并返回给 owner：

```bash
python3 tools/init_order.py --title "美化现有PPT" --with-templates \
  --execution-mode owner_direct --intake-source workspace_file
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
- `owner_return_ready`
- `owner_returned`
- `delivery`
- `closeout`

## Minimal Runbook

1. `init_order.py --with-templates` 创建订单。
2. 写入真实 `coverage_result.json`、`message_index.jsonl`、`attachment_index.jsonl` 后跑 `--gate chat_capture`。
3. 写入 `requirements.json` 后跑 `--gate briefing`。
4. 写入 `pending_approval.json` 和 `decision.md` 后跑 `--gate decision`。
5. 写入 approved approval record 和 `production_contract.json` 后跑 `--gate production`。
6. 跑 `--gate contract_accuracy` 确认 contract 足够精确。
7. 样稿通过并生成 `style_kit/` 后跑 `--gate sample_accuracy`。
8. 生成 `slide_jobs/slide_jobs.json` 和每页 `slide_jobs/slide_XX/job.json` 材料包后跑 `--gate slide_jobs`。
9. 所有 slide worker 完成并生成 `visual_qa_result.json` 后跑 `--gate visual_qa`。
10. 写入交付物、`qa_result.json` 和 `qa_report.md` 后跑 `--gate qa`。
11. 发送交付后写入 `08_closeout/`，再跑 `--gate closeout`。

## autopilot.py

Agent 每次先读取并验证当前步骤：

```bash
python3 tools/autopilot.py next orders/<order>
```

完成阶段后，校验产物并原子提交状态：

```bash
python3 tools/autopilot.py commit orders/<order> --to FULL_PRODUCTION
```

owner-direct 成品通过 QA 并写好 owner return manifest 后：

```bash
python3 tools/autopilot.py finish orders/<order> --target owner
```

`finish` 生成的 receipt ID 是 Agent 可以声称完成的必要证据。客户发送仍走独立 send manifest/approval/receipt。

## register_direct_intake.py

对 Codex 附件或用户明确指向的 workspace 文件执行一次性、幂等的 owner-direct intake：复制并复核 hash、生成 evidence indexes、记录 owner instruction approval、完成 promotion 并绑定 active order。它不理解内容，也不生产 PPT。
如果已有其他 active order，新订单会进入 `pending_order_ids` 并返回 `runnable=false`，不会覆盖全局当前订单。

```bash
python3 tools/register_direct_intake.py orders/<order> \
  --source-type workspace_file --prompt-file /tmp/exact-prompt.txt \
  --file /absolute/path/to/source.pptx
```

## composite_locked_chrome.py

将已批准的透明导航/logo/页脚/页码 overlay 精确合成到 accepted raw slide，校验 overlay hash、画布、content safe box 和 opaque pixels，原子写入最终 PNG 与 `finalization.json`。该工具不设计页面内容，只应用已批准的固定 chrome。

```bash
python3 tools/composite_locked_chrome.py \
  --order-dir orders/example \
  --job-id example:slide_01 --slide-no 1 --accepted-attempt 1 \
  --variant-id section_overview --active-navigation-section "概览" \
  --raw-image 05_production/slide_jobs/slide_01/attempt_01_raw.png \
  --overlay-image 05_production/slide_jobs/slide_01/input_images/locked_chrome.png \
  --expected-overlay-sha256 sha256:... \
  --output-mode image_first \
  --output-image 05_production/origin_image/slide_01.png \
  --receipt 05_production/slide_jobs/slide_01/finalization.json \
  --safe-box 120 140 1680 820
```

`hybrid`、`template_native` 或 `editable_reconstruction` 模式还必须传入 `--editable-artifacts-json <order-relative-path>`；该 JSON 是非空数组，每项只含 `path` 和 `role`，工具会自行校验路径并写入实际 hash。
