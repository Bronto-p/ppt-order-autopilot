---
name: ppt-qa-delivery
description: "PPT 质检与交付层。核对源内容、视觉质量、模板/样稿一致性、可编辑性、导出文件和 manifest；区分 Codex owner return 与企业微信客户发送。"
---

# PPT QA And Delivery

## QA

先通过 visual QA，再检查：源稿文字/数据差异、页数与页序、必需素材 fidelity、内容修改边界、style kit、导航/页码、跨页一致性、真实全尺寸渲染、溢出、PPTX 打开、PDF 回读、文件名和 output-mode 可编辑产物。

“没有溢出”不等于视觉合格。必须拒绝无依据的通用卡片模板、异常大面积留白、缺少主题视觉、低信息层级、风格漂移和模型编造文案。

## Owner Return

`owner_direct` QA 通过后生成 `07_delivery/owner_return_manifest.json`，只引用订单目录内已 hash 的成品和 `06_qa/qa_result.json`。commit `OWNER_RETURN_READY` 后运行：

```bash
python3 tools/autopilot.py finish <order_dir> --target owner
```

只有 `finish` 生成 `owner_return_receipt.json` 后才能在 Codex 返回文件并声称完成。

## Customer Send

客户样稿、成品和改稿继续要求 immutable file-send manifest、匹配 action 的 owner approval、发送前 hash 复核和 send receipt。绝不把 owner return 当作客户发送授权。
