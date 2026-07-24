---
name: ppt-sample-manager
description: "PPT 样稿流程层。为设计型任务先生成一张带真实内容的完整单页样稿，完成 QA，并分别处理 Codex owner 审阅或客户样稿发送与反馈。"
---

# PPT Sample Manager

## Purpose

在逐页生产前锁定真实可扩展的页面设计。样稿必须是一张可直接作为成品页使用的完整幻灯片，不是背景图、moodboard、空白模板或 style anchor。

## Inputs

- `03_requirements/requirements.json`
- `03_requirements/decision.md`
- `04_sample/sample_contract.json`
- `02_attachments_raw/attachment_index.jsonl`
- `00_state/approvals.jsonl`

## Required Policy

- `owner_direct`：新做、美化、重设计等设计型任务默认且必须先做样稿。用户说“完成后直接返回成品”只定义最终交付位置，不表示跳过样稿确认。
- `customer_order`：客户或 owner 要求样稿时走客户样稿分支；发送和客户反馈仍受各自 gate 约束。
- 样稿选择一张有代表性的真实内容页。它必须包含该页最终需要的标题、正文、数据、图形和完整构图。
- 样稿与正稿使用相同的 `output_mode`、生成 backend、画布、内容保真规则和 locked chrome 策略。
- 设计型任务默认 `image_first`：图片模型一次生成完整页面。不得先生成“背景底图/视觉层”再由父 Agent 叠加主体文字冒充样稿。

## Owner-direct Outputs

- `04_sample/sample_brief.md`
- `04_sample/sample_slide_plan.md`
- `04_sample/sample_contract.json`
- `04_sample/sample_preview_images/{slide_id}.png`
- `04_sample/sample_qa.md`
- `04_sample/owner_sample_manifest.json`
- 审阅后生成 `04_sample/owner_sample_decision.json`

`owner_sample_manifest.json` 必须绑定预览文件 hash、完整页面 prompt、真实内容使用情况、backend 和以下 QA：完整构图、全部必需文字可见、不是纯背景、文字可读。

## Owner Review Gate

1. 在 Codex 中直接展示完整尺寸样稿预览，并说明这是哪一页。
2. 进入 `OWNER_SAMPLE_REVIEW` 后停止，不继续生产其他页面。
3. owner 批准时，将回复绑定到当前 manifest hash，写入 `owner_sample_decision.json` 和 `approvals.jsonl` 的 `approve_owner_sample` action。
4. 批准后才构建 approved sample/style kit、打包其余页面并进入 `FULL_PRODUCTION`。
5. owner 要求修改时回到 `OWNER_SAMPLE_PRODUCTION`；不得沿用旧 hash 的批准。

## Customer-order Outputs

- `04_sample/sample_deck.pptx`
- `04_sample/sample_deck.pdf`
- `04_sample/sample_preview_images/`
- `04_sample/sample_qa.md`
- `04_sample/sample_delivery_message.md`
- `04_sample/sample_send_manifest.json`
- `04_sample/sample_send_receipt.json`
- `04_sample/customer_sample_decision.json`

客户样稿文件和消息只有在 `send_sample` approval 与 file-send manifest 同时存在时才能发送。发送后必须生成 receipt 并等待客户反馈；明确小修回到样稿生产，表述含糊或影响价格、截止、页数、整体风格时再请 owner 确认。

## Hard Blocks

- 预览只是背景、装饰板、无真实内容或缺少该页主要文字。
- prompt 含“background plate”“visual layer”“no text”或暗示稍后再补主体内容。
- QA 未通过、预览 hash 不可验证、画布不是订单比例，或 backend 与正稿契约不一致。
- 未取得当前样稿 hash 对应的 owner/customer 批准。
