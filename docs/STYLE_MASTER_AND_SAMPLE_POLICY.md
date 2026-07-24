# Style Kit And Sample Policy

A reviewed complete-slide sample is the visual gate for design-bearing work. For `owner_direct`, the Agent first generates one representative page with real content, shows it in Codex, and waits for approval bound to that preview hash. A background, moodboard, blank template, or internal style anchor is not a sample.

## Required Style Kit

```text
04_sample/style_kit/
├── style_kit.json
├── style_anchor.png
├── template_master.png
├── navigation_bar.png
├── locked_chrome_default.png
├── locked_chrome_section_*.png
├── cover_ref.png
├── section_ref.png
├── content_ref.png
├── data_ref.png
├── image_heavy_ref.png
└── locked_elements.json
```

## Meaning

- `style_anchor.png`: main visual anchor for all final slides.
- `template_master.png`: background, margins, title zone, footer, logo zone, navigation geometry.
- `navigation_bar.png`: visual reference for navigation.
- `locked_chrome_*.png`: one full-canvas overlay per slide, with registered slide number, page-number text, active section, path, and hash. Alpha is binary (0/255); antialiasing and shadows are flattened onto opaque fixed-background pixels.
- `invariant_skeleton`: the shared full-canvas chrome skeleton. Every per-slide variant must match it pixel-for-pixel outside declared active-highlight/page-number dynamic regions.
- page family references: prevent every slide from collapsing into one layout pattern.
- `style_kit.json`: machine-readable sample paths, page-family references, and must-match rules.
- `locked_elements.json`: canvas, content safe box, logo/page number/nav/footer geometry, render strategy, and overlay variants.

## Approval Output

`approved_sample_reference.json` must connect approved complete-page images to page families, production matching rules, and the evidence-backed `owner_sample_decision.json` or `customer_sample_decision.json` that authorized continued production.

Final slides must reference approved sample/style kit images; “按样稿风格做” as text is not enough.

## Owner-direct Production

Design-bearing owner-direct work cannot skip the reviewed sample. A customer template, source deck, brand guide, or owner style brief may guide the sample, but none of them replaces approval of the generated complete page.

After approval, the style kit records:

- `owner_sample_decision.json` and its approval evidence;
- the exact sample preview path and SHA-256;
- any template/source-deck/brand-guide inputs used;
- `style_anchor.png`, `template_master.png`, page-family references, and locked elements extracted from the approved complete page.

The sample and final pages use the same output mode and generation backend. In `image_first`, every worker generates the full page—including all visible content—in one image-generation task; the parent may only add approved deterministic locked chrome.
