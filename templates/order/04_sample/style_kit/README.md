# Style Kit

`style_kit/` 是正稿生产前生成的视觉材料包。正稿每页 subagent 必须收到这里的真实图像附件，不能只读文字风格描述。

没有客户样稿时也必须生成 style kit。`style_kit.json.source` 要记录它来自客户模板、源 PPT 还是 owner 已批准的风格 brief；禁止用“直接生产”绕过视觉基准。

建议产物：

```text
style_kit.json
style_anchor.png
template_master.png
navigation_bar.png
locked_chrome_default.png
locked_chrome_section_*.png
cover_ref.png
content_ref.png
data_ref.png
image_heavy_ref.png
locked_elements.json
```

规则：

- `style_anchor.png` 是所有正稿页必须携带的主视觉参考。
- `template_master.png` 控制背景、标题区、页脚、logo 区和整体留白。
- `navigation_bar.png` 是视觉参考。需要跨页像素稳定时，还必须为每页生成唯一同画布 locked-chrome variant，注册页码文本和 active section，并原样复制进本页 `input_images/`。Overlay alpha 只能是 0/255。
- `cover_ref.png`、`content_ref.png`、`data_ref.png`、`image_heavy_ref.png` 是页面类型参考。
- `locked_elements.json` 记录 canvas、content safe box、logo/页码/导航/页脚位置，以及每个 overlay variant 的 path/hash。
