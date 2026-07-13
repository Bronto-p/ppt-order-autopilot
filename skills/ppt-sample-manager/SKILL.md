---
name: ppt-sample-manager
description: "PPT 样稿流程层。根据已确认需求判断样稿分支，生成样稿 brief、样稿 PPT/PDF、样稿 QA 和样稿交付话术。样稿交付必须人工确认。"
---

# PPT Sample Manager

## Purpose

管理样稿分支。样稿不是固定 gate，而是订单状态机的一条分支。

## Inputs

- `03_requirements/requirements.json`
- `03_requirements/decision.md`
- `02_attachments_raw/attachment_index.jsonl`
- `00_state/approvals.jsonl`

## Outputs

- `04_sample/sample_brief.md`
- `04_sample/sample_slide_plan.md`
- `04_sample/sample_deck.pptx`
- `04_sample/sample_deck.pdf`
- `04_sample/sample_preview_images/`
- `04_sample/sample_qa.md`
- `04_sample/sample_delivery_message.md`
- `04_sample/sample_contract.json`
- `04_sample/sample_send_manifest.json`
- `04_sample/sample_send_receipt.json`
- `04_sample/customer_sample_decision.json`
- 统一结果契约 JSON

## Sample Required Rule

样稿是否需要不能默认。必须满足至少一个条件：

- 聊天明确说要样稿。
- 客服明确说要样稿。
- 你明确确认先走样稿。

## Missing Sample Questions

缺这些就进入追问或人工确认：

1. 样稿要几页。
2. 样稿看风格还是完整内容。
3. 样稿是否使用真实客户内容。
4. 样稿通过后是否直接做全稿。
5. 样稿截止时间。

## Hard Rules

- 样稿文件和消息只有在 `send_sample` approval 与 file-send manifest 同时存在时，才能由 WeCom operator 发送。
- 样稿 QA 不通过不能进入样稿交付确认。
- 发送样稿后必须生成 receipt 并等待客户反馈，不能直接进入正稿。
- 客户明确通过时记录 message evidence 并继续；明确小修自动回到样稿生产；表述含糊或影响价格、截止、页数、整体风格时再请 owner 确认。
- 样稿不能承诺正稿价格和截止时间，除非已有人工确认。
