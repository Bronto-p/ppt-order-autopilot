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

`owner_direct` 不强制价格、客户截止时间或 sample_required；customer order 继续按业务字段判断。文件名不是需求证据。无法确认的字段标为 `missing` 或 `inferred`，冲突写入 `conflicts.md`，不得自行覆盖。
