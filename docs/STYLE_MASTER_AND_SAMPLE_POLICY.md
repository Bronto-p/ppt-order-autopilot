# Style Kit And Sample Policy

Samples are not only for client approval. Approved samples create the visual anchors that make final production consistent.

## Required Style Kit

```text
04_sample/style_kit/
├── style_kit.json
├── style_anchor.png
├── template_master.png
├── navigation_bar.png
├── cover_ref.png
├── content_ref.png
├── data_ref.png
├── image_heavy_ref.png
└── locked_elements.json
```

## Meaning

- `style_anchor.png`: main visual anchor for all final slides.
- `template_master.png`: background, margins, title zone, footer, logo zone, navigation geometry.
- `navigation_bar.png`: separate reference for every slide with navigation.
- page family references: prevent every slide from collapsing into one layout pattern.
- `style_kit.json`: machine-readable sample paths, page-family references, and must-match rules.
- `locked_elements.json`: logo, page number, nav bar, footer, section label geometry and rules.

## Approval Output

`approved_sample_reference.json` must connect approved sample images to page families and production matching rules.

Final slides must reference approved sample/style kit images; “按样稿风格做” as text is not enough.
