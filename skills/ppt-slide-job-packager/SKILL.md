---
name: ppt-slide-job-packager
description: "PPT 单页材料包层。把 production contract 拆成一页一个 self-contained bundle，支持 Codex/workspace/企业微信素材、真实 style references、locked chrome 和多种 output mode。"
---

# PPT Slide Job Packager

读取 production contract、style kit 和已索引的 `from_chat/`、`from_customer/`、`from_codex/`、`from_workspace/` 素材。每页生成独立 `job.json`、`prompt.md`、`input_images/` 和总 `slide_jobs.json`。

每个 job 必须包含 deck/local context、exact content、前后页摘要、真实输入图片、style anchor、template master、page-family reference、客户素材 fidelity、locked chrome、`output_mode`、backend、QA 和 worker policy。

- 所有 worker `one_slide_only=true`。
- image_first：完整视觉画布，`uses_image_generation=true`、`image_generation_only=true`。
- hybrid：生图视觉层加可编辑文字/数据层，`uses_image_generation=true`、`image_generation_only=false`。
- template_native / editable_reconstruction：保留可编辑结构，`image_generation_only=false`，按需生成局部视觉素材。
- 必需素材必须实际复制进本页 bundle；路径文字不能代替附件。
- subagent 不读取聊天、raw 目录、完整 contract 或其他页面。
- 每个 job 必须设 `forbid_background_only=true`。`image_first` 还必须设 `must_generate_complete_slide=true` 和 `must_render_all_visible_content=true`；prompt 要求图片模型直接返回整张可交付幻灯片，不能写“背景底图”“visual layer”或“后续叠加主文字”。
