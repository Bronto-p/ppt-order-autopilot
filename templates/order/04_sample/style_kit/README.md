# Style Kit

`style_kit/` 是正稿生产前生成的视觉材料包。正稿每页 subagent 必须收到这里的真实图像附件，不能只读文字风格描述。

没有客户样稿时也必须生成 style kit。`style_kit.json.source` 要记录它来自客户模板、源 PPT 还是 owner 已批准的风格 brief；禁止用“直接生产”绕过视觉基准。

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
