---
name: ppt-qa-delivery
description: "PPT 质检和交付层。检查 PPTX/PDF、页数、需求覆盖、附件使用、错别字、溢出和文件名，生成 QA report 和交付话术。不能自动发送。"
---

# PPT QA Delivery

## Purpose

在交付前做独立 QA，并生成待人工确认的交付话术。

## Inputs

- `03_requirements/requirements.json`
- `03_requirements/production_contract.json`
- `05_production/*.pptx`
- `05_production/*.pdf`
- `05_production/origin_image/`

## Outputs

- `06_qa/qa_report.md`
- `06_qa/slide_screenshots/`
- `06_qa/issues.json`
- `06_qa/final_checklist.md`
- `07_delivery/delivery_message.md`
- 统一结果契约 JSON

## Checklist

1. 页数是否正确。
2. 标题是否覆盖客户主题。
3. 每页是否有明显文字溢出。
4. 字体是否过小。
5. 图片是否模糊。
6. 是否使用客户要求的 Logo、图片和文件。
7. 是否遗漏关键聊天需求。
8. 是否有错别字。
9. PPTX 是否能打开。
10. PDF 是否成功导出。
11. 文件名是否正确。
12. 是否生成交付话术。

## Hard Rules

- QA 不通过不能进入 `DELIVERY_READY`。
- 即使 QA 通过，也不能自动发送交付消息。
- 交付话术必须进入 owner approval。

