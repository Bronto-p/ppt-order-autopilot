---
name: ppt-slide-job-packager
description: "PPT 单页材料包构建层。把 production_contract.json 拆成每页一个 slide_XX bundle，复制真实 input_images，并生成 self-contained job.json、prompt.md 和 slide_jobs.json。"
---

# PPT Slide Job Packager

## Purpose

把总制作合同拆成 subagent 可直接执行的单页材料包。路径只供父流程定位；subagent 必须拿到本页 `input_images/` 里的真实图片附件。

## Inputs

- `03_requirements/production_contract.json`
- `04_sample/style_kit/style_kit.json`
- `04_sample/style_kit/*`
- `02_attachments_raw/from_chat/*`
- `02_attachments_raw/from_customer/*`
- `00_state/approvals.jsonl`

Raw attachments 只允许 packager 读取，用来复制到每页 bundle。production core 和 slide subagents 不能浏览 raw attachments。

## Outputs

```text
05_production/slide_jobs/
├── slide_jobs.json
├── slide_01/
│   ├── job.json
│   ├── prompt.md
│   └── input_images/
├── slide_02/
│   ├── job.json
│   ├── prompt.md
│   └── input_images/
└── ...
```

## Job Requirements

Each `job.json` must include:

- exact slide-ready content.
- bundled `input_images` with `bundle_path`.
- image role and fidelity rule for every bundled image.
- style anchor.
- template master.
- page family reference.
- navigation bar image when the slide uses navigation.
- strict client assets assigned to that slide.
- worker reasoning level.
- text-only fallback prohibition.

## Hard Rules

1. Required image missing from `input_images/` means blocked.
2. `strict_client_asset` must have a bundle file and fidelity rule.
3. No `low` reasoning level.
4. Pages with strict assets, navigation, data, old PPT references, timeline, process, cover, or sample roles must use `high`.
5. Subagents must not read raw attachments, chat logs, order brief, or full production contract.

