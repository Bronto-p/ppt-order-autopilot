---
name: ppt-style-master-builder
description: "PPT 样稿风格母版层。把已通过样稿转换成 style_master 图像锚点、approved_sample_reference.json、style_spec.json 和 locked_elements.json，供正稿每页引用。"
---

# PPT Style Master Builder

## Purpose

样稿通过后，生成正稿生产必须使用的真实视觉锚点。不能只留下“按样稿风格做”的文字说明。

## Inputs

- `04_sample/sample_contract.json`
- `04_sample/sample_preview_images/*`
- `04_sample/sample_qa.md`
- `00_state/approvals.jsonl`

## Outputs

- `04_sample/approved_sample_reference.json`
- `04_sample/style_master/style_anchor.png`
- `04_sample/style_master/template_master.png`
- `04_sample/style_master/navigation_bar_reference.png`
- `04_sample/style_master/cover_reference.png`
- `04_sample/style_master/section_reference.png`
- `04_sample/style_master/content_reference.png`
- `04_sample/style_master/data_reference.png`
- `04_sample/style_master/image_heavy_reference.png`
- `04_sample/style_master/style_spec.json`
- `04_sample/style_master/locked_elements.json`
- 统一结果契约 JSON

## Hard Rules

1. 没有样稿 approval，不生成 approved sample reference。
2. `style_anchor.png` 和 `template_master.png` 是正稿必要输入。
3. 有导航条时必须生成 `navigation_bar_reference.png` 和 locked navigation rule。
4. style master 是图像参考 + JSON 坐标规则，不是纯文字描述。
5. 正稿每页必须引用 approved sample 或 style master。

