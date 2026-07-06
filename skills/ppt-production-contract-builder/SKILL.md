---
name: ppt-production-contract-builder
description: "PPT 生产契约构建层。把已确认的 requirements、decision、approval 和附件索引转换成 production_contract.json，生成素材 allowlist 和需求覆盖矩阵。不能自行补需求或使用未批准附件。"
---

# PPT Production Contract Builder

## Purpose

在接单决策和正式生产之间建立明确接口。它负责把已确认的订单需求转换成 `production_contract.json`，让 production core 只吃干净契约。

## Inputs

- `03_requirements/requirements.json`
- `03_requirements/decision.md`
- `03_requirements/pending_approval.json`
- `00_state/approvals.jsonl`
- `02_attachments_raw/attachment_index.jsonl`

## Outputs

- `03_requirements/production_contract.json`
- 统一结果契约 JSON

## Required Contract Fields

- `deck_title`
- `page_count`
- `aspect_ratio`
- `deadline`
- `deliverables`
- `deck.requirements_source`
- `production_method`
- `style_system`
- `asset_registry`
- `asset_allowlist`
- `forbidden_assets`
- `coverage_matrix`
- `source_files`
- `brand_assets`
- `slides[].exact_content`
- `slides[].input_images`
- `slides[].must_preserve`
- `slides[].forbidden_changes`
- `slides[].worker`
- `slides[].qa_requirements`
- `approval.approval_id`

## Hard Rules

1. 没有 approved approval record，不生成生产契约。
2. 必填需求缺失时不生成生产契约。
3. 有未解决冲突时不生成生产契约。
4. 所有素材必须来自 `attachment_index.jsonl` 或人工确认的本地路径。
5. 生产契约必须写清楚每个客户要求覆盖到哪些 slide。
6. 每个 strict client asset 必须分配到具体 slide。
7. 每页必须包含 approved sample/style anchor、template reference 和 page family reference。
8. 有导航条的页必须包含 navigation reference。
