# PPT Generation Accuracy

PPT 生产层的目标不是“能生成一套 PPT”，而是让每一页 subagent 拿到足够完整、可审计、可验证的输入。

## Core Rules

1. 每页必须有可全尺寸检查的 rendered preview。设计型任务默认 `image_first`，由生图模型一次生成包含全部可见文字、图形和构图的完整 canvas；纯背景或“稍后加文字”的 visual layer 禁止通过。只有明确且高置信的可编辑性/模板/图表要求才能选择 `hybrid`、native 或 editable 模式。
2. 父 agent 不直接做页面，只负责 contract、style kit、job packaging、dispatch、QA 和 assembly。
3. 每个 subagent 只做一页。
4. 每个 subagent 的 job 必须 self-contained。
5. 每页必须带真实 style/sample/template/nav 参考图，不能只靠文字描述。
6. 客户指定图片、logo、图表、证书必须作为 strict input asset 传入，不能生成相似物。
7. 样稿通过后，正稿每一页都必须带 approved sample 或 style anchor。
8. 有导航条、固定页脚、栏目标签时，必须有同画布 transparent overlay、hash、content safe box 和 locked element 规则；仅有 reference image 不够。
9. subagent reasoning 默认 high，low 禁止用于客户生产。
10. required image 无法传入所选 backend 时，必须 blocker，不能 text-only fallback。
11. 每次派发和修复必须保留 attempt snapshot；不得覆盖失败结果或让 worker 自行宣布 accepted。
12. 自动修复最多三次，缺素材和内容冲突不允许用重试掩盖。
13. owner-direct 设计任务必须先展示一张完整单页样稿并获得绑定 preview hash 的批准。客户样稿发送仍使用独立的发送和反馈 gate。

## Production Flow

```text
requirements.json
attachment_index.jsonl
approved decision
        |
        v
ppt-production-contract-builder
        |
        v
production_contract.json
        |
        v
ppt-style-master-builder
        |
        v
style_kit/
approved_sample_reference.json
        |
        v
ppt-slide-job-packager
        |
        v
05_production/slide_jobs/slide_XX/job.json
05_production/slide_jobs/slide_XX/input_images/*
slide_run_state.json
        |
        v
one slide per worker
        |
        v
raw attempt output
        |
        v
parent finalization + locked chrome
        |
        v
origin_image/slide_XX.png + finalization.json
        |
        v
ppt-visual-consistency-qa
        |
        v
repair / regenerate / assemble
```

## Validator Gates

- `contract_accuracy`: validates production contract depth.
- `sample_accuracy`: validates style kit and approved sample reference.
- `slide_jobs`: validates self-contained one-page jobs.
- `slide_run_state`: preserves attempt history and the parent-selected accepted attempt.
- `visual_qa`: validates asset fidelity, style drift, navigation consistency, text readability, and slide run state.
