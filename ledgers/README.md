# Ledgers

全局账本放在这里。真实运行时建议使用 append-only JSONL。

```text
automation_state.json
inquiries.jsonl
orders.jsonl
sent_messages.jsonl
ui_actions.jsonl
approvals.jsonl
schemas/
```

规则：

- 不覆盖历史记录。
- `automation_state.json` 只保存当前全局指针、pending/waiting 订单队列和 Codex Automation 绑定；历史询单动作追加到 `inquiries.jsonl`。
- 不删除已发送消息记录。
- 所有人工确认都必须有 `approval_id`。
- 所有 UI 发送动作都必须能追溯到消息内容 hash 和审批记录。

`schemas/` 里的 JSON Schema 是可提交的契约文件；运行时 JSONL 文件默认被 `.gitignore` 忽略。
