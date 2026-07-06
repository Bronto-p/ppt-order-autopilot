# Image Reference Routing

Images must be routed by purpose before any production worker sees them.

## Asset Classes

- `strict_input_asset`: customer-specified logo, image, chart, screenshot, certificate, table, or proof that must appear on a slide.
- `style_reference_only`: reference image used only for style, palette, composition, or mood.
- `template_reference`: reusable layout system, background, navigation, title zone, margins, footer, or card system.
- `whole_slide_reference`: rendered source PPT slide used only to understand current page state.
- `decorative_template_asset`: background ornaments, repeated chrome, separators, or non-content assets.

## Rules

1. strict input assets must be assigned to specific slides.
2. strict input assets need exact-use or crop/fit-only fidelity rules.
3. style references must not be copied as client content.
4. whole-slide renders are page-state references, not crop sources.
5. production core cannot browse raw attachment folders for inspiration.
6. every slide job must list all required images explicitly in `input_images`.

## Old PPT Handling

For old PPT beautification or redesign, split the source deck into:

- `source_slide_render`: whole-slide image for page-state reference only.
- `extracted_content`: actual text, numbers, labels, and structure.
- `extracted_media`: original embedded media files.

If an embedded media file exists, do not crop it out of a rendered whole-slide image.

