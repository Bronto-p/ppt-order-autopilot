# Sample

样稿产物放在这里。

建议文件：

```text
sample_brief.md
sample_slide_plan.md
sample_contract.json
sample_deck.pptx
sample_deck.pdf
sample_preview_images/
owner_sample_manifest.json
owner_sample_decision.json
approved_sample_reference.json
style_kit/
sample_qa.md
sample_delivery_message.md
sample_send_manifest.json
sample_send_receipt.json
customer_sample_decision.json
```

`owner_direct` 的设计型任务先在 Codex 中展示一张带真实内容的完整单页样稿。`owner_sample_manifest.json` 绑定预览 hash，批准后由 `owner_sample_decision.json` 绑定 owner 证据；纯背景、moodboard 或 style anchor 不算样稿。

`style_kit/` 是正稿页面保持一致的主路径。样稿通过后，正稿每页必须引用 style kit 里的真实图像参考，不能只靠文字描述风格。

`sample_send_receipt.json` 证明样稿确已发送；`customer_sample_decision.json` 必须引用真实客户消息证据。样稿发出不等于客户通过。
