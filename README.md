# PPT Order Autopilot

这是一个 Agent-native 的 PPT 接单自动化系统。Codex/AI Agent 本身是 orchestrator；仓库提供可持久的上下文、状态、安全边界、每页任务契约和 validator，不是试图用传统代码代替 Agent 推理。

它能在一个活跃的 Codex 任务里自动跑到人工门禁、真实 blocker 或订单结束。它不是自带常驻进程的后台 daemon；任务结束后的定时唤醒需要 Codex Automation 或在同一任务中手动 resume。

运行时按订单场景选择最短生产路径，并把每页交给独立 slide worker。审查结论与目标流程见：

- [深度审查](docs/DEEP_REVIEW.md)
- [PPT 生产工作流 V2](docs/WORKFLOW_V2.md)

核心原则：

> Computer Use 只做眼睛和手，不能做脑子。

企业微信 UI 操作、截图、下载附件可以进入受限自动化层；接不接、问什么、发什么、样稿怎么走、成品什么时候交付，必须由业务 skill、状态机和人工确认控制。

## 当前交付物

```text
ppt-order-autopilot/
├── AGENTS.md               # Agent 唯一启动入口
├── .codex-plugin/          # 薄插件元数据，skills 按需加载
├── configs/                 # 白名单、排程、消息策略示例
├── docs/                    # 系统设计和硬边界文档
├── inbox/                   # 订单识别前的询单与下载暂存
├── ledgers/                 # 全局账本占位
├── orders/                  # 真实订单目录
├── skills/                  # 每个业务层的 skill 契约骨架
├── templates/order/         # 单个订单的标准文件结构模板
└── tools/                   # 最小初始化和校验工具
```

## 系统边界

- `wecom-computer-use-operator` 只负责打开企业微信、定位白名单客服、截图、下载附件、发送已批准消息。
- `wecom-chat-recorder` 只负责完整采集聊天记录，生成覆盖报告、转写文本、消息索引和附件索引。
- `ppt-order-briefing` 只负责结构化需求、缺失项和冲突项，每个字段必须带证据。
- `ppt-order-decision` 只负责生成接单建议和待确认话术，不能发送。
- `ppt-production-contract-builder` 只负责把已确认需求和审批记录转换成 `production_contract.json`。
- `ppt-style-master-builder` 只负责把已批准样稿、客户模板、源 PPT 或已批准风格 brief 转换成 style kit 图像锚点和机器规则。
- `ppt-slide-job-packager` 只负责把 contract 拆成每页一个真实材料包。
- `ppt-production-core` 只吃 slide job bundles，不回头翻企业微信或 raw 附件目录。
- `ppt-visual-consistency-qa` 只负责检查 style drift、asset fidelity、navigation consistency 和 worker blockers。
- `ppt-qa-delivery` 只在 QA 通过后生成交付包和交付话术，仍然不能自动发送。

## 快速开始

### Agent 运行

将仓库作为 Codex plugin 安装/附加，或直接作为 workspace 打开。在完成一次性 live config 后，直接要求 Agent “运行 PPT Order Autopilot”。Agent 必须按照根目录 `AGENTS.md` 从企业微信或 Codex 附件开始，而不是要求你先创建订单文件夹。

运行入口和恢复规则见 [Agent Run Loop](docs/AGENT_RUN_LOOP.md)。

也可以直接在 Codex 任务里附上客户文件，或明确指向 workspace 中的文件。Agent 会自动选择 `owner_direct`（在 Codex 中制作并返回给你）或 `customer_order`（带客户承诺与外部发送 gate），自己暂存、建单并继续。具体启动口令、确认节点和定时唤醒说明见 [Codex Usage](docs/CODEX_USAGE.md)。

每个订单步骤由 `tools/autopilot.py next/commit` 校验；owner-direct 成品只有在 `finish --target owner` 生成 verification receipt 后才能宣告完成。AI 负责理解、设计和逐页生产，控制器只守状态、hash 和交付边界。

### 手动诊断

初始化一个新订单目录：

```bash
python3 tools/init_order.py --title "大学生创新创业项目路演PPT"
```

复制订单模板和 schema 到新订单目录：

```bash
python3 tools/init_order.py --title "大学生创新创业项目路演PPT" --contact "客服A" --with-templates
```

校验订单硬门槛：

```bash
python3 tools/validate_order.py orders/2026-07-05_001_大学生创新创业项目路演PPT --gate chat_capture
python3 tools/validate_order.py orders/2026-07-05_001_大学生创新创业项目路演PPT --gate decision
```

`orders/`、运行时 `ledgers/*.jsonl`、PPT/PDF 等客户数据默认被 `.gitignore` 忽略，不要把真实订单数据提交到公开仓库。

## 关键文档

- [System Design](docs/SYSTEM_DESIGN.md)
- [Codex Usage](docs/CODEX_USAGE.md)
- [State Machine](docs/STATE_MACHINE.md)
- [UI Operation Policy](docs/UI_OPERATION_POLICY.md)
- [Order Folder Contract](docs/ORDER_FOLDER_CONTRACT.md)
- [PPT Generation Accuracy](docs/PPT_GENERATION_ACCURACY.md)
- [Image Reference Routing](docs/IMAGE_REFERENCE_ROUTING.md)
- [Style Kit And Sample Policy](docs/STYLE_MASTER_AND_SAMPLE_POLICY.md)
- [Subagent Handoff Policy](docs/SUBAGENT_HANDOFF_POLICY.md)
- [Visual Consistency QA](docs/VISUAL_CONSISTENCY_QA.md)
