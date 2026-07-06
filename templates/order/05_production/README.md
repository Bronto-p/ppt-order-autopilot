# Production

正稿产物放在这里。

`ppt-production-core` 只能从 `03_requirements/production_contract.json` 开始生产。

生产 core 不直接做页面，而是拆成：

```text
1. build style master
2. build slide jobs
3. dispatch one slide per worker
4. visual consistency QA
5. assemble PPTX/PDF
```

建议产物：

```text
production_blueprint.json
slide_jobs.json
slide_run_state.json
prompts/slide_01.json
prompts/slide_02.json
origin_image/slide_01.png
origin_image/slide_02.png
visual_qa_result.json
```

每个 `prompts/slide_XX.json` 必须是 self-contained job，包含 exact content、style anchor、template master、navigation reference、page family reference、required client assets、fidelity rules、worker reasoning level、backend 和 QA requirements。
