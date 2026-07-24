# PPT 生产工作流 V2

## 设计目标

这个流程不假设客户一定有模板或完整内容，也不假设所有页面都适合用同一种方式生成。设计型任务先用一张完整内容页验证视觉方向；客户样稿发送和 owner 在 Codex 内审阅是两个不同 gate。

系统必须先判断订单属于什么问题，再选择最短且安全的生产路径。图片生成是默认视觉能力，不是强迫所有文字、数据和可编辑元素都烘焙进一张图片的理由。

## 1. 先确定六个决策轴

每个订单在开始生产前必须得到以下分类：

| 决策轴 | 允许值 | 影响 |
| --- | --- | --- |
| job mode | new deck / template fill / full redesign / selected slides / repair / editable reconstruction | 决定是否保留原页数、原结构和原 slide id |
| content readiness | complete / partial / brief only / missing | 决定是直接规划、补内容还是阻塞追问 |
| design source | customer template / source deck / brand guide / reference images / system proposed | 决定 style kit 从哪里建立 |
| transformation | beautify / layout cleanup / visual redesign / content restructure / new content | 决定允许 worker 改多少 |
| output mode | image_first / hybrid / template_native / editable_reconstruction | 决定页面如何生成和装配；设计型任务默认 image_first |
| sample policy | owner review / customer review | 决定完整单页样稿由谁确认及是否需要外发 |

这六个轴必须显式记录。不能用“做一个 PPT”或“美化一下”直接跳到生图。

## 2. 常见订单路由

| 客户输入 | 默认路径 | 必须阻塞或确认的情况 |
| --- | --- | --- |
| 有完整内容，无模板 | 内容结构化 → 系统提出设计方向 → 风险样稿 → 生产 | 页数、受众、用途或品牌偏好缺失 |
| 只有主题或一句 brief | 研究/内容生成 → 客户确认大纲 → 设计 → 生产 | 无法判断事实来源、用途或交付深度 |
| 有模板和完整内容 | 模板解析 → 页型映射 → template_native 或 hybrid | 模板字体/母版缺失，内容超出页型容量 |
| 有模板但内容不全 | 缺口分析 → 追问或内容补全 → 页型映射 | 客户是否允许补写内容不明确 |
| 有旧 PPT，要美化 | 提取文本/媒体/结构 → 保真边界 → 逐页优化 | 页数变化、删减、改写未获允许 |
| 只改指定页 | 读取全稿上下文 → 只打包指定页 → 原 slide id 回填 | 指定范围不明确或会破坏全稿导航 |
| 数据/图表密集 | 数据校验 → native chart/table + image visual layer | 原始数据不可用或数字相互冲突 |
| 需要完全可编辑 | template_native 或 editable_reconstruction | 客户只提供低清截图且要求像素级可编辑 |
| 高视觉路演/发布会 | image_first 页面 + native text safety layer | 品牌素材缺失、人物/产品不可伪造 |
| 多语言版本 | 锁定源语言内容 → 翻译 → 文本扩张检查 → 同版式适配 | 专有名词表和目标语言未确认 |
| 打印册/竖版/4:3 | 单独画布策略 → 安全边距 → 打印导出 QA | 不允许默认沿用 16:9 |

## 3. 精简后的订单生命周期

主状态只描述业务阶段，不描述每一次 UI 点击或等待时间。

```text
INTAKE
  -> CLARIFY
  -> PLAN
  -> DESIGN
  -> PRODUCE
  -> QA
  -> DELIVER
  -> REVISE -> PRODUCE
  -> CLOSED
```

每个阶段统一使用 `pending / running / blocked / completed / failed`。轮询时间、截图序号、附件下载和单页 attempt 都是 task/event，不再变成新的订单主状态。

需要人工确认的只有高影响决策：

- 接单、价格、截止时间和范围。
- 系统需要替客户补写或重构内容。
- 高风险订单的视觉方向。
- 最终发送和超范围改稿。

`owner_direct` 是同一生产核心的短路径：直接文件 intake → brief/contract → 完整单页样稿 → owner 在 Codex 审阅 → style kit → per-slide production → QA → verified Codex return。它不经过客户报价、样稿发送或外部交付 gate；最终由 `autopilot.py finish --target owner` 生成 receipt。

## 4. 生产前的 deck contract

进入逐页生产前，父流程必须冻结：

- deck goal、audience、language、aspect ratio、deliverables。
- slide count policy：固定、允许调整或只修改指定页。
- 每页 exact content、页面意图和在故事中的作用。
- 每页必须使用的客户素材及 fidelity rule。
- design system 来源和已锁定元素。
- output mode 与可编辑性要求。
- 不允许修改的内容、数据、结构或品牌元素。

任何页面仍为“介绍产品”“展示数据”这种主题描述时，都不能派发 worker。

## 5. 一页一个 subagent

父流程负责全局判断，slide worker 只负责一页。每个 job 必须自包含：

```json
{
  "job_id": "order_001:slide_07:v2",
  "slide_no": 7,
  "page_role": "evidence",
  "deck_story": "问题 -> 方案 -> 证据 -> 商业模式",
  "previous_slide": "方案如何工作",
  "next_slide": "客户案例",
  "exact_content": {},
  "content_checks": [],
  "assets": [],
  "design_system": {},
  "transformation_boundary": {},
  "output_mode": "image_first",
  "worker_policy": {
    "must_generate_complete_slide": true,
    "must_render_all_visible_content": true,
    "forbid_background_only": true
  },
  "attempt": 1,
  "max_attempts": 3
}
```

worker 必须实际收到图片附件，不能只收到本地路径文字。worker 不读取聊天、全量 raw 附件或其他订单文件，也不能自行补事实。

worker 输出：完整页面图（或仅在明确高置信可编辑需求下输出契约允许的原生结构）、实际使用素材、内容核对结果、阻塞项和可重试原因。任何模式都不能把“只有背景”报告为完成页面。

## 6. 图片生成策略

每页都可以使用图片模型，但装配策略按页面风险选择：

### image_first

设计型任务的默认模式。图片模型一次生成全部可见文字、图形和完整构图；父 Agent 不再重新设计或补齐主体内容，只能合成已批准的确定性 locked chrome。

### hybrid

只用于用户明确要求主要文字/表格/图表可编辑，且证据置信度高的页面。图片模型可生成局部视觉资产，标题、正文、数字、表格和图表使用可校验的原生元素；不能仅凭“文字最好可编辑”之类推测自动切换。

### template_native

适合严格企业模板、批量周报、标准汇报和必须完全可编辑的订单。图片模型只生成插图或局部视觉资产，文本与图表填入原模板占位符。

### editable_reconstruction

适合截图/PDF/图片版 PPT 重建。先分析页面层次，再重建背景视觉、原生文字和可编辑对象；不能把全页截图冒充可编辑文件。

禁止把客户 Logo、产品、人物、证书、截图或数据交给模型“画一个类似的”。必须使用真实素材或明确阻塞。

## 7. 并发与一致性

1. 第一张代表性完整内容页必须先完成、通过父流程 QA，并取得 owner/customer 对当前 preview hash 的批准。
2. 内容页、数据页和图片页各选一个代表页，验证 design system 的可扩展性。
3. 风格确认后才能并行。每个 worker 仍只处理一页。
4. 有跨页依赖的页面按小批次执行：目录/章节导航、连续时间线、逐步流程、成组数据页不能完全独立乱序生成。
5. 每批完成后执行 deck-level QA，发现系统性偏差时修 design system，不逐页重复打补丁。
6. 修复任务使用原 job id 的新 attempt，保留所有结果，不覆盖历史。

## 8. QA 分为四层

### 内容 QA

- exact content 是否完整出现。
- 数字、单位、日期、专有名词和引用是否正确。
- 是否出现模型编造内容。
- 多语言版本是否漏译或溢出。

### 页面 QA

- 文字是否可读、遮挡、截断或越界。
- 客户素材是否真实使用且未被重画。
- 图表是否与源数据一致。
- 页面是否符合 transformation boundary。

### 全稿 QA

- 章节顺序、叙事推进和结论是否连贯。
- 术语、颜色、字体、导航、页码和 Logo 是否一致。
- 是否有重复页面、遗漏需求或同一事实前后矛盾。
- 页面密度是否有异常跳变。

### 导出 QA

- PPTX 能打开，PDF 页数一致。
- 指定页面尺寸、字体嵌入、链接、动画和备注符合交付要求。
- 导出后重新渲染检查，不能只验证文件存在。

## 9. 失败与恢复

- 所有 task 使用确定性 id；重复运行不能重复发送、重复扣费或覆盖已批准结果。
- 每页记录 `queued / running / blocked / repair / accepted` 和 attempt。
- 失败分类至少区分：缺素材、内容不确定、模型失败、文字错误、视觉偏差、导出失败。
- 自动重试只用于暂时性模型/导出错误；缺素材、冲突内容和范围变化必须阻塞。
- 每页默认最多三次生成尝试。超过预算后进入人工处理，不能无限循环。
- 恢复时从事件和 run state 计算下一任务，不依赖对话记忆。

## 10. 最小事实源

长期建议把订单运行时收敛到以下核心文件，而不是让每个 skill 创建一套重复文档：

```text
order.json          # 商务范围、需求、证据、审批引用
assets.json         # 素材、来源、hash、用途、fidelity
deck_spec.json      # 结构、逐页 exact content、design system、策略
run_state.json      # task、attempt、worker、结果、blocker
delivery.json       # QA、文件 manifest、发送审批与回执
artifacts/          # 原始素材、样稿、页面结果、导出文件
```

Markdown 只做人类阅读视图，从 JSON 生成；schema 是唯一机器规则来源，validator 不再手写另一套字段定义。
