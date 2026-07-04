# Tools

这里放最小本地工具。当前只提供骨架级工具，不做企业微信 UI 自动化。

## init_order.py

创建标准订单目录：

```bash
python3 tools/init_order.py --title "大学生创新创业项目路演PPT"
```

可选指定客服：

```bash
python3 tools/init_order.py --title "商业计划书" --contact "客服A"
```

## validate_order.py

按 gate 校验订单硬门槛：

```bash
python3 tools/validate_order.py orders/2026-07-05_001_商业计划书 --gate chat_capture
python3 tools/validate_order.py orders/2026-07-05_001_商业计划书 --gate decision
```

支持的 gate：

- `base`
- `chat_capture`
- `briefing`
- `decision`
- `production`
- `qa`
- `delivery`

