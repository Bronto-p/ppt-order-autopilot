---
name: ppt-order-briefing
description: "PPT 需求提取层。从企业微信或直接文件证据中生成结构化需求、转换边界、输出模式、缺失项与冲突；每个字段必须有 evidence。"
---

# PPT Order Briefing

读取 coverage、message index、attachment index 和实际源文件。输出 `order_brief.md`、`requirements.json`、`missing_questions.md`、`conflicts.md`。

除基础需求外，必须明确：

- `job_mode`：new deck / template fill / full redesign / selected slides / repair / editable reconstruction。
- `transformation`：beautify / layout cleanup / visual redesign / content restructure / new content。
- `output_mode`：image_first / hybrid / template_native / editable_reconstruction。
- `content_change_policy`：哪些文字、数据、页数、结构和素材不得修改。
- `delivery_target`：owner_codex 或 customer_wecom。

`owner_direct` 不强制价格或客户截止时间，但设计/美化/重制默认 `sample_required=true`，样稿范围是一张带真实内容的完整代表页。“最后返回成品”不能推断为跳过样稿。

`image_first` 是美化、visual redesign 和新设计的默认 output mode。只有 owner/customer 明确要求可编辑结构、严格模板继承或 native 图表/表格时，才能以 high-confidence evidence 选 `hybrid` / `template_native` / `editable_reconstruction`；不得因为“文字可编辑更好”自行推断 hybrid。

文件名不是需求证据。无法确认的字段标为 `missing` 或 `inferred`，冲突写入 `conflicts.md`，不得自行覆盖。
