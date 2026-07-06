# Style Kit

`style_kit/` 是样稿通过后生成的正稿视觉材料包。正稿每页 subagent 必须收到这里的真实图像附件，不能只读文字风格描述。

建议产物：

```text
style_kit.json
style_anchor.png
template_master.png
navigation_bar.png
cover_ref.png
content_ref.png
data_ref.png
image_heavy_ref.png
locked_elements.json
```

规则：

- `style_anchor.png` 是所有正稿页必须携带的主视觉参考。
- `template_master.png` 控制背景、标题区、页脚、logo 区和整体留白。
- `navigation_bar.png` 必须复制进所有有导航条页面的 `input_images/`。
- `cover_ref.png`、`content_ref.png`、`data_ref.png`、`image_heavy_ref.png` 是页面类型参考。
- `locked_elements.json` 记录 logo、页码、导航条、页脚、栏目高亮的位置规则。

