# Skill Contracts

每个 skill 的输出必须包含统一结果契约：

```json
{
  "status": "success",
  "confidence": "high",
  "evidence_files": [],
  "next_action": "next_step_name",
  "requires_owner_approval": false
}
```

允许的 `status`：

- `success`
- `blocked`
- `failed`

允许的 `confidence`：

- `high`
- `medium`
- `low`

## 1. ppt-business-orchestrator

职责：

- 读取 `state.json`。
- 决定下一步调用哪个 skill。
- 检查是否需要人工确认。
- 防止重复发送。
- 写入 `events.jsonl`。

禁止：

- 直接操作企业微信。
- 直接制作 PPT。
- 直接发送业务消息。

## 2. wecom-computer-use-operator

职责：

- 打开企业微信。
- 定位白名单客服。
- 发送固定询单。
- 检查回复。
- 打开聊天记录。
- 保存截图。
- 下载附件。

禁止：

- 业务判断。
- 自由聊天。
- 报价。
- 接单。
- 交付。
- 操作非白名单联系人。

## 3. wecom-chat-recorder

职责：

- 从顶部到底部采集聊天。
- 生成 `chat_transcript.md`。
- 生成 `chat_coverage_report.md`。
- 生成 `message_index.jsonl`。
- 生成 `attachment_index.jsonl`。
- 发现断层就停止。

## 4. ppt-order-briefing

职责：

- 提取主题、用途、页数、截止时间、价格、样稿要求、素材、风格、交付格式。
- 标记缺失信息。
- 标记冲突。
- 生成 `order_brief.md`、`requirements.json`、`missing_questions.md`、`conflicts.md`。

硬规则：

- 每个需求字段必须有 evidence。
- 必填字段缺失时必须停止到追问流程。

## 5. ppt-order-decision

职责：

- 判断建议接、追问后接、谨慎、不接。
- 生成 `decision.md`。
- 生成 `pending_approval.md`。
- 生成客服话术草稿。

禁止：

- 自动接单。
- 自动拒单。
- 自动报价。
- 自动发送。

## 6. ppt-production-contract-builder

职责：

- 读取 `requirements.json`、`decision.md`、`approvals.jsonl` 和 `attachment_index.jsonl`。
- 把已确认需求转成 `production_contract.json`。
- 生成 `asset_allowlist`、`forbidden_assets` 和 `coverage_matrix`。

禁止：

- 不直接操作企业微信。
- 不自行补缺失需求。
- 不使用未批准附件。

硬规则：

- 没有 approved approval record，不生成生产契约。
- contract 中所有素材必须来自附件索引或人工确认的本地路径。

## 7. ppt-sample-manager

职责：

- 判断是否需要样稿。
- 生成样稿 brief。
- 制作样稿 PPT/PDF。
- 样稿 QA。
- 生成样稿交付话术。

硬规则：

- 样稿是否需要不能默认。
- 样稿交付必须人工确认。

## 8. ppt-style-master-builder

职责：

- 读取样稿产物和 approval。
- 生成 `approved_sample_reference.json`。
- 生成 `04_sample/style_master/*` 图像锚点和 JSON 规则。

硬规则：

- 没有 approved sample，不生成 style master。
- style master 必须包含图像参考和 locked element 规则。

## 9. ppt-slide-job-builder

职责：

- 读取 `production_contract.json`、approved samples 和 style master。
- 生成 `slide_jobs.json` 和每页 `prompts/slide_XX.json`。
- 确保每个单页 job self-contained。

硬规则：

- required client asset 必须进入对应页 `input_images`。
- worker reasoning level 不能是 low。
- 缺 required image 必须 blocker，不能 text-only fallback。

## 10. ppt-production-core

职责：

- 读取 `production_contract.json`。
- 生成页面设计。
- 生成全页图。
- 装配 PPTX。
- 导出 PDF。

硬规则：

- 不读取企业微信。
- 不自行解释聊天。
- 不自行补缺失需求。
- 只能读取 contract 中 allowlist 明确列出的素材。
- parent agent 不直接生成页面。
- 每页必须由生图模型生成完整 slide image。

## 11. ppt-visual-consistency-qa

职责：

- 检查 required assets 是否可见且未被重画。
- 检查 style drift。
- 检查 navigation consistency。
- 检查 locked elements。
- 检查 worker blockers。
- 生成 `visual_qa_result.json` 和四个视觉 QA 报告。

硬规则：

- strict asset fidelity 失败阻塞 assembly。
- visual QA 不 pass，final QA 不允许 pass。

## 12. ppt-qa-delivery

职责：

- 检查页数。
- 检查标题和主题覆盖。
- 检查文字溢出。
- 检查附件使用。
- 检查错别字。
- 检查 PPTX/PDF 是否可打开。
- 生成 `qa_report.md`。
- 生成 `delivery_message.md`。

硬规则：

- 没有 QA 通过，不进入交付确认。
- 交付消息不能自动发送。
