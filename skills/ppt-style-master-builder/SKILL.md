---
name: ppt-style-master-builder
description: "PPT 视觉基准构建层。从已批准样稿、客户模板、源 PPT 或已批准风格 brief 生成统一 style_kit，供正稿每页引用。"
---

# PPT Style Kit Builder

## Purpose

为所有生产路径生成真实视觉锚点。样稿不是 style kit 的唯一来源；直接生产也必须先从客户模板、源 PPT 或 owner 批准的风格 brief 建立 style kit。不能只留下“按某某风格做”的文字说明。

## Inputs

- `03_requirements/production_contract.json`
- `02_attachments_raw/attachment_index.jsonl`
- 可选：`04_sample/sample_contract.json`
- 可选：`04_sample/sample_preview_images/*`
- 可选：`04_sample/sample_qa.md`
- 样稿分支：`04_sample/customer_sample_decision.json`
- `00_state/approvals.jsonl`

## Outputs

- `04_sample/approved_sample_reference.json`
- `04_sample/style_kit/style_kit.json`
- `04_sample/style_kit/style_anchor.png`
- `04_sample/style_kit/template_master.png`
- `04_sample/style_kit/navigation_bar.png`
- `04_sample/style_kit/cover_ref.png`
- `04_sample/style_kit/content_ref.png`
- `04_sample/style_kit/data_ref.png`
- `04_sample/style_kit/image_heavy_ref.png`
- `04_sample/style_kit/locked_elements.json`
- 统一结果契约 JSON

## Hard Rules

1. `sample_required=true` 时只能使用 `approved_sample`；没有带消息证据的客户明确通过记录，不生成 approved sample reference。
2. 直接生产时 `source_type` 必须是 `customer_template`、`source_deck` 或 `approved_style_brief`，且必须引用真实 source paths 和 approval；owner-direct 可使用同订单的 `owner_direct_instruction` approval。
3. 无样稿不等于无视觉基准；直接生产也必须生成完整 style kit。
4. `style_anchor.png` 和 `template_master.png` 是正稿必要输入。
5. 有导航条时必须生成 `navigation_bar.png` 和 locked navigation rule。
6. style kit 是图像参考 + JSON 坐标规则，不是纯文字描述。
7. 正稿每页必须引用 style kit。
8. 导航、logo、页脚或页码要求跨页像素稳定时，`locked_elements.json` 必须使用 `post_generation_composite`，声明 `content_safe_box` 和所有 transparent overlay variants 的 path/hash。
9. 先生成一张 `invariant_skeleton`，再为每页建立一个完整 variant，注册 `slide_no`、`page_number_text` 和 active section。所有 variant 在 `dynamic_regions` 之外必须与 skeleton 像素完全一致；只允许声明的栏目高亮和页码区域变化。
10. 页码必须声明 `page_number_policy`（plain、zero-padded、current/total 或逐页 custom map），variant 文本必须与政策计算结果一致。
11. Overlay alpha 只能是 0 或 255。抗锯齿、阴影和半透明效果必须先在固定背景上扁平化成不透明像素，避免与每页 raw canvas 混合后漂移。
12. 样稿必须是已经 owner/customer 审阅的完整页面，不是背景图或 style anchor。批准后才能从该页提取 `style_anchor.png`、`template_master.png` 和 page-family references。
