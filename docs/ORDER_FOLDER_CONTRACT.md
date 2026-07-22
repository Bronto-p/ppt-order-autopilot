# Order Folder Contract

每个订单都必须使用标准目录结构。任何 skill 只能读取和写入自己负责的区域，跨区域写入必须通过 orchestrator。

## 1. 标准目录

```text
orders/{order_id}_{topic}/
├── 00_state/
│   ├── state.json
│   ├── events.jsonl
│   └── approvals.jsonl
├── 01_chat/
│   ├── screenshots/
│   ├── ocr/
│   ├── chat_transcript.md
│   ├── chat_coverage_report.md
│   ├── coverage_result.json
│   └── message_index.jsonl
├── 02_attachments_raw/
│   ├── from_chat/
│   ├── from_customer/
│   ├── from_codex/
│   ├── from_workspace/
│   ├── attachment_index.jsonl
│   └── failed_downloads.md
├── 03_requirements/
│   ├── order_brief.md
│   ├── requirements.json
│   ├── missing_questions.md
│   ├── conflicts.md
│   ├── decision.md
│   ├── pending_approval.json
│   └── production_contract.json
├── 04_sample/
│   ├── sample_contract.json
│   ├── sample_send_manifest.json
│   ├── sample_send_receipt.json
│   ├── customer_sample_decision.json
│   ├── approved_sample_reference.json
│   └── style_kit/
│       ├── style_kit.json
│       ├── style_anchor.png
│       ├── template_master.png
│       ├── navigation_bar.png
│       └── locked_elements.json
├── 05_production/
│   ├── production_blueprint.json
│   ├── slide_jobs/
│   ├── slide_run_state.json
│   ├── origin_image/
│   └── visual_qa_result.json
├── 06_qa/
│   ├── qa_report.md
│   └── qa_result.json
├── 07_delivery/
│   ├── delivery_message.md
│   ├── final_send_manifest.json
│   ├── revision_request.json
│   ├── revision_decision.md
│   └── revision_quote_or_scope.md
└── 08_closeout/
    ├── order_summary.md
    ├── final_files_manifest.json
    ├── delivery_receipt.json
    ├── revision_history.md
    ├── payment_status.json
    └── closeout_checklist.md
```

## 2. 聊天覆盖报告

`chat_coverage_report.md` 必须包含：

- 截图总数。
- 顶部锚点。
- 底部锚点。
- 相邻屏幕重叠检查结果。
- 附件发现数量。
- 附件下载成功数量。
- 附件下载失败数量。
- 疑似冲突数量。

没有覆盖报告，不允许需求提取。

同时必须生成机器可读的 `coverage_result.json`。validator 以 JSON 为准，Markdown 只给人审阅。

## 3. 附件索引

每个附件必须写入 `attachment_index.jsonl`：

```json
{
  "attachment_id": "att_003",
  "original_filename": "参考风格.png",
  "saved_path": "02_attachments_raw/from_chat/att_003_参考风格.png",
  "source_message_time": "2026-07-05T10:38:00+08:00",
  "source_sender": "客户",
  "file_type": "reference_style",
  "sha256": "sha256:...",
  "download_status": "success"
}
```

## 4. 需求字段

`requirements.json` 中每个字段必须有：

```json
{
  "value": "大学生创新创业项目路演PPT",
  "evidence": "客户 10:12: 我要做一个大创项目路演PPT",
  "confidence": "high",
  "required": true
}
```

如果没有证据，必须标记为 `missing` 或 `inferred`，不能当成确定需求。

## 5. 生产契约

`production_contract.json` 是 PPT 生产层唯一入口。它必须由 briefing 和 decision 后生成，并经过人工确认。

`owner_direct` 不伪造 customer decision。用户的 exact prompt 可以形成 order-scoped `owner_direct_instruction` approval；production contract 必须同时记录 execution mode、delivery target 和每页 output mode。

生产层不能直接读取企业微信、聊天截图或未经整理的客服消息。

## 6. 审批和 QA 结果

`pending_approval.json` 必须包含待发送话术的 `draft_sha256`。Computer Use 发送前必须用这个 hash 做二次校验。

`qa_result.json` 必须是机器可读 QA 结果。只有 `status: "pass"` 才允许进入交付 gate。

Codex 内返回给 owner 使用 `07_delivery/owner_return_manifest.json` 和由 `tools/autopilot.py finish` 生成的 `owner_return_receipt.json`。这两个文件不包含 contact、customer message 或 send approval，也不能替代客户外发 manifest。
