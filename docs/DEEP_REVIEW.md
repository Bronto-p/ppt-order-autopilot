# PPT Order Autopilot 深度审查

## 结论

当前仓库是一个有价值的规则原型，但还不是可自动运行的系统。真正可执行的部分只有订单目录初始化和门槛校验；企业微信采集、需求归纳、流程调度、单页生产、修复重试和交付都仍由 skill 文档描述，没有统一运行器。

主要问题不是规则不够多，而是同一事实被分散在 skill、Markdown、schema、模板和 validator 中。它们已经出现不同步，继续增加规则会放大维护成本。

## 已确认的问题

### P0：会造成错误授权或错误放行

1. **审批可以跨订单复用。** 原 validator 只检查 `approval_id` 是否存在于任意本地或全局账本，没有绑定当前 `order_id`。
2. **审批草稿 hash 没有验证正文。** 只检查 `sha256:` 格式，不检查它是否真的是 `draft_message` 的摘要。
3. **交付审批没有动作类型。** 任意 approved 记录都可满足交付 gate，包括接单审批。
4. **运行时路径可以逃出订单目录。** 附件、slide job、render result 和交付 manifest 中的相对路径可包含 `../`，validator 会读取订单目录之外的文件。
5. **空集合被当成有效需求。** `[]` 和 `{}` 不被视为空值，因此“必填素材列表为空”可能通过完整性检查。

本 PR 修复这些 validator 问题，并增加针对性回归用例。

### P1：流程自身不闭合

1. **仓库没有真正的 orchestrator。** `ppt-business-orchestrator` 目前是说明书，没有负责状态迁移、锁、重试或 skill 调用的程序。
2. **状态机混合了三种不同层级。** `WAITING_REPLY_2M` 属于调度器，`CAPTURING_CHAT_FROM_TOP` 属于 UI 采集任务，`FULL_PRODUCTION` 属于订单生命周期；全部放进一个 39 状态主状态机后，分支和恢复逻辑会持续膨胀。
3. **样稿和生产存在循环依赖。** sample manager 曾声明依赖 `production_contract.json`，而 production contract 又固定引用样稿产出的 style kit。
4. **“不需要样稿”路径不完整。** slide packager 无条件要求 style kit，但 style kit 的定义又默认来自已批准样稿。
5. **审查时存在两套目录命名。** `style_master/` 与 `style_kit/` 同时存在，部分 skill、文档和 schema 指向不同目录；本 PR 已统一为 `style_kit/`。
6. **schema 不是 validator 的真相来源。** JSON Schema 文件很多，但 `validate_order.py` 重新手写了一套不完整规则，两套定义会继续漂移。原本误命名为 `requirements.schema.json` 的实例模板已在本 PR 更名，但统一 schema 仍需后续迁移。
7. **恢复能力只是字段，没有实现。** `locked_by`、`lock_expires_at`、幂等、重试次数和事件回放都未被运行器执行。

本 PR 先消除明确的目录冲突和 sample/contract 循环声明。状态机与 schema 的收敛应作为独立后续 PR，避免把迁移和 bug 修复混在一次不可审查的重写中。

### P1：PPT 生产策略覆盖不全

1. **强制全页图片不适合所有订单。** 数据表、密集中文、需要编辑的企业模板、论文答辩和精确图表对文字与数据准确性要求高，纯生图容易出现乱码、错数和不可编辑问题。
2. **每页一个 subagent 的方向正确，但 job context 不完整。** 当前 schema 缺少 deck story、相邻页关系、页面意图、允许改动范围、输出模式和可验证内容清单。
3. **只有视觉一致性，没有叙事一致性。** 当前 QA 偏重样式、导航和素材，没有检查章节推进、重复内容、跨页术语、结论是否由前文支持。
4. **没有页面级重试预算。** 缺少确定性 job id、attempt、失败分类、最大重试次数和只修问题区域的策略，容易无限重生整页。
5. **样稿规则过于二元。** 样稿不应只有“客户明确要求才做”和“完全不做”；高风险订单需要基于模板严格度、金额、页数、品牌要求和内容不确定性决定。

独立的目标流程见 [WORKFLOW_V2.md](WORKFLOW_V2.md)。

## 建议保留的部分

- 每个需求字段带 evidence 的思路。
- 客户素材的真实性和 fidelity 约束。
- 一页一个 worker、父流程只负责编排与 QA。
- 订单级可恢复状态和 append-only 事件。
- 发送消息和最终交付保留人工确认。

## 建议删除或降级的部分

- 将 2/5/10/30/60/120 分钟等待编码为订单主状态。
- 为每个小职责建立一个只含 Markdown 的 skill。
- 把样稿设为所有生产路径的固定前置条件。
- 把“全页图片”设成所有客户场景唯一合法输出。
- 在订单目录中复制大量 schema 和 README。
- 同时维护 Markdown 规则、schema 和手写 validator 三套事实源。

## 推荐的后续 PR

1. **生命周期收敛：** 将主状态缩减为 intake、clarify、plan、design、produce、qa、deliver、revise/closed；轮询与 UI 步骤迁移到任务事件。
2. **统一订单清单：** 用一个 canonical order manifest 承载需求、证据、场景策略和审批引用，schema 成为唯一验证来源。
3. **生产运行器：** 实现可恢复的 slide dispatcher、确定性 job id、并发上限、attempt 和 repair queue。
4. **多渲染策略：** 支持 image-first、hybrid、template-native 和 editable reconstruction，并由订单需求自动选择。
5. **端到端 QA：** 增加 OCR/内容核对、数据核对、跨页叙事、一致性、导出回读和交付文件检查。
