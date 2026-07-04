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

## 6. ppt-sample-manager

职责：

- 判断是否需要样稿。
- 生成样稿 brief。
- 制作样稿 PPT/PDF。
- 样稿 QA。
- 生成样稿交付话术。

硬规则：

- 样稿是否需要不能默认。
- 样稿交付必须人工确认。

## 7. ppt-production-core

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

## 8. ppt-qa-delivery

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

