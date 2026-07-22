#!/usr/bin/env python3
"""Apply a pixel-stable transparent chrome overlay to an accepted slide image."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops


OUTPUT_MODES = {
    "image_first",
    "hybrid",
    "template_native",
    "editable_reconstruction",
}
EDITABLE_ARTIFACT_ROLES = {
    "native_slide",
    "editable_layer_spec",
    "chart_data",
    "table_data",
    "speaker_notes",
}


def resolve_within(root: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"path must be relative to the order: {relative_path}")
    root = root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes the order: {relative_path}") from exc
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def safe_box_is_clear(overlay: Image.Image, safe_box: tuple[int, int, int, int]) -> bool:
    x, y, width, height = safe_box
    if width <= 0 or height <= 0 or x < 0 or y < 0:
        return False
    if x + width > overlay.width or y + height > overlay.height:
        return False
    return overlay.getchannel("A").crop((x, y, x + width, y + height)).getbbox() is None


def alpha_is_binary(overlay: Image.Image) -> bool:
    extrema = overlay.getchannel("A").getextrema()
    if extrema == (0, 0) or extrema == (255, 255):
        return True
    histogram = overlay.getchannel("A").histogram()
    return sum(histogram[1:255]) == 0


def opaque_pixels_match(final_image: Image.Image, overlay: Image.Image) -> bool:
    opaque_mask = overlay.getchannel("A").point(lambda alpha: 255 if alpha == 255 else 0)
    if opaque_mask.getbbox() is None:
        return False
    difference = ImageChops.difference(final_image.convert("RGB"), overlay.convert("RGB"))
    black = Image.new("RGB", final_image.size, (0, 0, 0))
    return Image.composite(difference, black, opaque_mask).getbbox() is None


def atomic_save_png(image: Image.Image, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".png", dir=output_path.parent, delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        image.save(temp_path, format="PNG")
        os.replace(temp_path, output_path)
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_write_json(payload: dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_path.parent, delete=False) as temp_file:
        json.dump(payload, temp_file, ensure_ascii=False, indent=2)
        temp_file.write("\n")
        temp_path = Path(temp_file.name)
    try:
        os.replace(temp_path, output_path)
    finally:
        temp_path.unlink(missing_ok=True)


def load_editable_artifacts(order_dir: Path, manifest: str | None, output_mode: str) -> list[dict[str, str]]:
    if manifest is None:
        if output_mode != "image_first":
            raise SystemExit("editable output modes require --editable-artifacts-json")
        return []
    manifest_path = resolve_within(order_dir, manifest)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read editable artifacts manifest: {exc}") from exc
    if not isinstance(payload, list) or not payload:
        raise SystemExit("editable artifacts manifest must be a non-empty JSON array")
    artifacts: list[dict[str, str]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict) or set(item) != {"path", "role"}:
            raise SystemExit(f"editable artifact {index} must contain only path and role")
        path = item.get("path")
        role = item.get("role")
        if not isinstance(path, str) or not isinstance(role, str) or role not in EDITABLE_ARTIFACT_ROLES:
            raise SystemExit(f"editable artifact {index} is invalid")
        artifact_path = resolve_within(order_dir, path)
        if not artifact_path.is_file():
            raise SystemExit(f"editable artifact does not exist: {path}")
        artifacts.append({"path": path, "sha256": sha256_file(artifact_path), "role": role})
    return artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Composite an immutable locked-chrome overlay onto a slide.")
    parser.add_argument("--order-dir", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--slide-no", required=True, type=int)
    parser.add_argument("--accepted-attempt", required=True, type=int)
    parser.add_argument("--variant-id", required=True)
    parser.add_argument("--active-navigation-section")
    parser.add_argument("--raw-image", required=True)
    parser.add_argument("--overlay-image", required=True)
    parser.add_argument("--expected-overlay-sha256", required=True)
    parser.add_argument("--output-image", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--output-mode", choices=sorted(OUTPUT_MODES), default="image_first")
    parser.add_argument(
        "--editable-artifacts-json",
        help="Order-relative JSON array of {path, role}; required outside image_first mode.",
    )
    parser.add_argument("--safe-box", required=True, nargs=4, type=int, metavar=("X", "Y", "W", "H"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    order_dir = Path(args.order_dir).resolve()
    raw_path = resolve_within(order_dir, args.raw_image)
    overlay_path = resolve_within(order_dir, args.overlay_image)
    output_path = resolve_within(order_dir, args.output_image)
    receipt_path = resolve_within(order_dir, args.receipt)
    editable_artifacts = load_editable_artifacts(order_dir, args.editable_artifacts_json, args.output_mode)
    if raw_path == output_path:
        raise SystemExit("raw slide and final output paths must be different")

    actual_overlay_sha256 = sha256_file(overlay_path)
    if actual_overlay_sha256 != args.expected_overlay_sha256:
        raise SystemExit("locked chrome sha256 does not match the slide job")

    raw_image = Image.open(raw_path).convert("RGBA")
    overlay = Image.open(overlay_path).convert("RGBA")
    if raw_image.size != overlay.size:
        raise SystemExit("raw slide and locked chrome must use the same canvas")
    if not alpha_is_binary(overlay):
        raise SystemExit("locked chrome alpha must be binary (fully transparent or fully opaque)")
    safe_box = tuple(args.safe_box)
    if not safe_box_is_clear(overlay, safe_box):
        raise SystemExit("locked chrome overlaps the declared content safe box")

    final_image = Image.alpha_composite(raw_image, overlay)
    pixel_match = opaque_pixels_match(final_image, overlay)
    if not pixel_match:
        raise SystemExit("locked chrome opaque pixels were not preserved")
    atomic_save_png(final_image, output_path)
    saved_image = Image.open(output_path).convert("RGBA")
    if ImageChops.difference(saved_image, final_image).getbbox() is not None:
        output_path.unlink(missing_ok=True)
        raise SystemExit("saved final image does not match the composed pixels")

    receipt = {
        "job_id": args.job_id,
        "slide_no": args.slide_no,
        "output_mode": args.output_mode,
        "accepted_attempt": args.accepted_attempt,
        "status": "pass",
        "raw_output_image": args.raw_image,
        "raw_output_sha256": sha256_file(raw_path),
        "final_output_image": args.output_image,
        "final_output_sha256": sha256_file(output_path),
        "editable_artifacts": editable_artifacts,
        "locked_chrome": {
            "mode": "post_generation_composite",
            "variant_id": args.variant_id,
            "active_navigation_section": args.active_navigation_section,
            "overlay_path": args.overlay_image,
            "overlay_sha256": actual_overlay_sha256,
            "applied": True,
            "pixel_match": True,
            "content_safe_zone_clear": True,
        },
        "finalized_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_json(receipt, receipt_path)
    print(output_path)


if __name__ == "__main__":
    main()
