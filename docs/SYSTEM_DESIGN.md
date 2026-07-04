# System Design

## 1. 目标

这个系统服务于 PPT 接单流程，但它的第一目标不是自动生产 PPT，而是把最容易翻车的地方做成硬机制：

- 企业微信 UI 操作不能点错人。
- 聊天记录不能漏读。
- 附件不能漏存。
- 需求不能靠猜。
- 业务消息不能误发。
- 中断后不能重复接单或丢状态。

## 2. 总体架构

```text
Automation / manual trigger
        |
        v
ppt-business-orchestrator
        |
        v
wecom-computer-use-operator
        |
        v
wecom-chat-recorder
        |
        v
ppt-order-briefing
        |
        v
ppt-order-decision
        |
        v
owner approval
        |
        v
ppt-sample-manager / ppt-production-core
        |
        v
ppt-qa-delivery
        |
        v
owner delivery approval
```

## 3. 分层职责

### Orchestrator

`ppt-business-orchestrator` 是总控。它只读写订单状态和账本，决定下一步应该调用哪个 skill。

它不直接操作企业微信，不直接做 PPT，也不直接发送业务消息。

### UI Adapter

`wecom-computer-use-operator` 是受限 UI 操作层。它可以打开企业微信、定位白名单客服、截图、下载附件、发送已经批准的话术。

它不能判断业务，不能报价，不能接单，不能交付。

### Chat Recorder

`wecom-chat-recorder` 是聊天采集层。它负责从聊天记录顶部到底部截图、OCR、建立消息索引、下载附件、生成覆盖报告。

没有 `chat_coverage_report.md`，后续 skill 不允许开始需求提取。

### Briefing

`ppt-order-briefing` 是需求结构化层。它从聊天记录、附件和消息索引里提取需求字段。

每个字段必须有：

- `value`
- `evidence`
- `confidence`
- `required`

没有证据的字段不能当成确定需求。

### Decision

`ppt-order-decision` 是接单建议层。它输出：

- 建议接。
- 建议追问后接。
- 建议谨慎。
- 建议不接。

它只能生成 `pending_approval.md`，不能发送消息。

### Production

`ppt-production-core` 是 PPT 生产层。它只接受 `production_contract.json`，不直接读取企业微信，不自行解释聊天，不自行补需求。

现有的 `full ppt making workflow/skills/ppt-complete-workflow` 可以作为后续生产后端，但接入前必须先由本系统生成干净的生产契约。

### QA and Delivery

`ppt-qa-delivery` 是质检和交付层。它检查 PPT、PDF、需求覆盖、附件使用、页数、错别字、导出结果和交付文件名。

即使 QA 通过，也只生成交付话术，不能自动发送。

## 4. 核心账本

全局账本放在 `ledgers/`：

```text
ledgers/
├── orders.jsonl
├── sent_messages.jsonl
├── ui_actions.jsonl
└── approvals.jsonl
```

订单内账本放在 `orders/{order_id}/00_state/`：

```text
00_state/
├── state.json
├── events.jsonl
└── approvals.jsonl
```

## 5. 不可绕过的硬门槛

1. 发送消息前必须校验白名单联系人。
2. 业务消息必须先进入人工确认队列。
3. 聊天读取必须有顶部锚点、底部锚点和相邻屏重叠检查。
4. 附件必须进入 `attachment_index.jsonl`。
5. 需求字段必须带证据。
6. 冲突必须进入 `conflicts.md`。
7. 接单、报价、样稿、交付必须等人工确认。
8. 中断恢复只能依赖 `state.json` 和账本，不能依赖对话记忆。

