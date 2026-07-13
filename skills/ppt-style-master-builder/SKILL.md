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

1. `sample_required=true` 时只能使用 `approved_sample`，没有样稿 approval 不生成 approved sample reference。
2. 直接生产时 `source_type` 必须是 `customer_template`、`source_deck` 或 `approved_style_brief`，且必须引用真实 source paths 和 approval。
3. 无样稿不等于无视觉基准；直接生产也必须生成完整 style kit。
4. `style_anchor.png` 和 `template_master.png` 是正稿必要输入。
5. 有导航条时必须生成 `navigation_bar.png` 和 locked navigation rule。
6. style kit 是图像参考 + JSON 坐标规则，不是纯文字描述。
7. 正稿每页必须引用 style kit。
