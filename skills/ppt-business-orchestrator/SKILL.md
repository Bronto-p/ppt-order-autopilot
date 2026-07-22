---
name: ppt-business-orchestrator
description: "PPT Order Autopilot 总入口。用户附加插件，或要求运行、继续、恢复、查询、制作、美化、修改或交付 PPT 订单时使用；自动区分 owner-direct、Codex 附件、workspace 文件和企业微信客户订单。"
---

# PPT Business Orchestrator

## Start

1. 定位插件运行仓库；运行 `python3 tools/bootstrap_runtime.py`。
2. 有订单时，先运行 `python3 tools/autopilot.py next <order_dir>`。它是当前步骤的事实源。
3. 没有订单时，按用户请求选择：
   - `owner_direct`：用户在 Codex 里直接要求制作/美化/修改并返回给自己。
   - `customer_order`：需要读取客户聊天、报价、发送样稿或外部交付。
4. 文件来自本条 Codex 消息时用 `codex_attachment`；来自当前 workspace 且用户明确指向时用 `workspace_file`；来自企业微信时用 `wecom`。
5. 只加载下一步骤所需 skill 和直接输入。

## Mandatory Protocol

- 每个阶段完成后运行 `python3 tools/autopilot.py commit <order_dir> --to <STATE>`。校验失败时修复或记录 blocker；不得手改状态绕过。
- `owner_direct` 成品返回前必须进入 `OWNER_RETURN_READY`，再运行 `python3 tools/autopilot.py finish <order_dir> --target owner`。
- 最终回复必须包含 `finish` 返回的 `receipt_id`。没有 receipt 时禁止说“已按插件完成”。
- 客户发送继续使用不可变 send manifest、owner approval 和发送 receipt；owner Codex return 不是客户发送，不需要 WeCom approval。
- 不得直接调用通用 PPT 工具绕开 production contract、slide bundles、one-slide workers 或 QA。Presentation/PDF 工具只能由 production/QA 阶段按契约使用。

## Owner-Direct Route

```text
IDLE -> DIRECT_INTAKE_STAGED -> BUILDING_TRANSCRIPT
-> EXTRACTING_ORDER_BRIEF -> DIRECT_PRODUCTION_ALLOWED
-> FULL_PRODUCTION -> FULL_QA -> OWNER_RETURN_READY -> OWNER_RETURNED
```

- 用户的明确指令可记录为 `owner_direct_instruction` approval，只授权内部生产范围和返回 owner。
- 不要求价格、客服联系人、客户截止时间或样稿发送确认，除非用户请求涉及这些事项。
- “试稿文件”“sample 文件夹”等文件名不等于客户样稿分支；依据用户意图判断。

## Production Delegation

显式附加本插件并要求按插件制作，视为明确要求插件声明的 one-slide-per-subagent 工作方式。父 Agent 负责 contract、style kit、派发、跨页 QA、修复和 assembly；每个 worker 只处理一页。若 subagent 或所需后端不可用，在生产前记录 blocker，不得静默换成通用模板。

## Owner Gates

只在客户承诺或真实高影响不确定性时询问 owner：接单、价格、截止、范围、客户消息、样稿发送、最终外发、重大改稿、关键素材或事实冲突。内部分析、style anchor、逐页生产、第一轮修复、QA 和 owner Codex return 自动继续。

详细恢复、外部副作用和上下文分层见 `docs/AGENT_RUN_LOOP.md`；状态与 gate 定义见 `configs/state_machine.json`。
