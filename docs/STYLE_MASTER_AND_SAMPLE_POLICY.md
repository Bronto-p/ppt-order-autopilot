# Style Master And Sample Policy

Samples are one source of visual anchors, not a universal gate. Every production path needs a style kit, but direct production may build it from a customer template, source deck, or owner-approved style brief.

## Required Style Master

```text
04_sample/style_master/
├── style_anchor.png
├── template_master.png
├── navigation_bar_reference.png
├── cover_reference.png
├── section_reference.png
├── content_reference.png
├── data_reference.png
├── image_heavy_reference.png
├── style_spec.json
└── locked_elements.json
```

## Meaning

- `style_anchor.png`: main visual anchor for all final slides.
- `template_master.png`: background, margins, title zone, footer, logo zone, navigation geometry.
- `navigation_bar_reference.png`: separate reference for every slide with navigation.
- page family references: prevent every slide from collapsing into one layout pattern.
- `style_spec.json`: machine-readable palette, typography, spacing, card, shadow, image treatment.
- `locked_elements.json`: logo, page number, nav bar, footer, section label geometry and rules.

## Approval Output

`approved_sample_reference.json` must connect approved sample images to page families and production matching rules.

Final slides must reference approved sample/style kit images; “按样稿风格做” as text is not enough.

## Direct Production

When `sample_required=false`, the style kit records one explicit source type:

- `customer_template`
- `source_deck`
- `approved_style_brief`

It must still contain `style_anchor.png`, `template_master.png`, page-family references, locked elements, source paths, and the approval ID. Skipping customer-facing samples never permits skipping the internal visual system.
