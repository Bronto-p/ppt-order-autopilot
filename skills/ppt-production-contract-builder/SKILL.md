---
name: ppt-production-contract-builder
description: "PPT 生产契约层。把已确认 requirements、真实 owner/customer approval 和附件索引转换成 production_contract.json；支持 image-first、hybrid、template-native、editable reconstruction 和混合页面。"
---

# PPT Production Contract Builder

只从 requirements、evidence index、approval 和明确允许的素材生成 `03_requirements/production_contract.json`。

## Approval

- customer order：要求 `accept_order` 或 `approve_production` approval。
- owner direct：用户 exact prompt 可形成 order-scoped `owner_direct_instruction` approval；只授权内部生产与返回 owner，不授权客户发送。

## Contract

冻结 deck goal、audience、language、画布、交付格式、页数策略、内容修改边界和 style source。`method.production_mode` 可为 `image_first`、`hybrid`、`template_native`、`editable_reconstruction` 或 `mixed`；每页必须有自己的 `output_mode`、exact content source、资产和 job path。

美化/visual redesign 默认冻结为 `image_first`。非 `image_first` 必须与 requirements 中明确、high-confidence 的可编辑或模板要求一致；禁止把模型偏好写成用户要求。样稿和正稿使用同一 output mode 和同一类 backend。

有未解决冲突、缺必需字段、未知 approval 或未索引素材时不生成契约。直接生产也必须建立 style kit，来源只能是客户模板、源 deck 或已批准 style brief。
