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
slide_jobs/
├── slide_jobs.json
├── slide_01/
│   ├── job.json
│   ├── prompt.md
│   ├── render_result.json
│   └── input_images/
├── slide_02/
│   ├── job.json
│   ├── prompt.md
│   ├── render_result.json
│   └── input_images/
slide_run_state.json
origin_image/slide_01.png
origin_image/slide_02.png
visual_qa_result.json
```

每个 `slide_jobs/slide_XX/job.json` 必须是 self-contained job。subagent 只能看到本页 `job.json`、`prompt.md` 和本页 `input_images/` 里的真实文件，不能回头翻 raw 附件目录。
