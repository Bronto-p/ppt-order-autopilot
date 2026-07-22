---
name: ppt-production-core
description: "PPT 逐页生产核心。只读取已验证的 slide bundles，按一页一个 subagent 生成页面、修复、组装 PPTX/PDF，并保留每次 attempt；禁止绕回聊天或通用模板捷径。"
---

# PPT Production Core

开始前必须通过 `slide_jobs` gate。父 Agent 不直接设计页面；每个 subagent 只接收一个 immutable slide bundle，并返回 raw preview、实际使用素材、内容核对、blockers，以及非 image-first 模式所需的 editable artifacts。

## Output Modes

- `image_first`：生图生成完整主体画布；已批准 locked chrome 由父 Agent 确定性合成。
- `hybrid`：subagent 返回生图视觉层、可编辑层描述和 preview；关键文字、数字、表格与图表保持可校验。
- `template_native`：继承模板页型和占位符，图片模型只生产所需插图/视觉资产。
- `editable_reconstruction`：重建背景、原生文字和可编辑对象；不得把截图冒充可编辑页。

父 Agent 检查 exact content、素材 fidelity、风格、可读性和 output-mode 契约。失败 attempt 不覆盖；只对暂时性后端错误、文字错误、style drift 或 layout error 自动修复。缺素材或事实冲突 blocker。所有页面 accepted 后才能 assembly 和 FULL_QA。

显式插件调用要求 one-slide-per-subagent；能力不可用时在任何页面生产前停止，不得改用通用 Presentations 直接做完整 deck。
