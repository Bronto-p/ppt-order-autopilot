#!/usr/bin/env python3
"""Create a standard PPT order folder."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from bootstrap_runtime import bootstrap_runtime


TZ_SHANGHAI = timezone(timedelta(hours=8))
ORDER_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{3}(?:_[A-Za-z0-9-]+)?$")
ORDER_SUBDIRS = [
    "00_state",
    "01_chat/screenshots",
    "01_chat/ocr",
    "02_attachments_raw/from_chat",
    "02_attachments_raw/from_customer",
    "03_requirements",
    "04_sample",
    "05_production",
    "06_qa",
    "07_delivery",
    "08_closeout",
]


def slugify_title(title: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", " ", title).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:60] or "untitled"


def validate_order_id(order_id: str) -> str:
    if not ORDER_ID_RE.fullmatch(order_id):
        raise SystemExit(
            "invalid order_id; expected YYYY-MM-DD_NNN or YYYY-MM-DD_NNN_suffix with only letters, numbers, '-' and '_'"
        )
    if "/" in order_id or "\\" in order_id or ".." in order_id:
        raise SystemExit("invalid order_id; path separators and '..' are forbidden")
    return order_id


def next_sequence(orders_root: Path, date_prefix: str) -> int:
    max_seq = 0
    if not orders_root.exists():
        return 1
    for path in orders_root.iterdir():
        if not path.is_dir():
            continue
        match = re.match(rf"^{re.escape(date_prefix)}_(\d{{3}})", path.name)
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return max_seq + 1


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def write_json(path: Path, payload: dict) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def template_target_name(path: Path) -> str:
    name = path.name
    return name.replace(".template.", ".")


def copy_order_templates(project_root: Path, order_dir: Path, overwrite: bool) -> None:
    template_root = project_root / "templates" / "order"
    for source in template_root.rglob("*"):
        if source.is_dir():
            continue
        if source.relative_to(template_root).as_posix() == "00_state/state.template.json":
            continue
        relative_parent = source.relative_to(template_root).parent
        target = order_dir / relative_parent / template_target_name(source)
        if target.exists() and not overwrite:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def create_order(args: argparse.Namespace) -> Path:
    project_root = Path(__file__).resolve().parents[1]
    orders_root = (project_root / args.orders_root).resolve()
    if not orders_root.is_relative_to(project_root):
        raise SystemExit(f"orders_root must stay inside project root: {project_root}")
    orders_root.mkdir(parents=True, exist_ok=True)
    bootstrap_runtime(project_root)

    now = datetime.now(TZ_SHANGHAI)
    date_prefix = now.strftime("%Y-%m-%d")
    sequence = args.sequence or next_sequence(orders_root, date_prefix)
    order_id = validate_order_id(args.order_id or f"{date_prefix}_{sequence:03d}")
    title_slug = slugify_title(args.title)
    order_dir = orders_root / f"{order_id}_{title_slug}"
    if not order_dir.resolve().is_relative_to(orders_root):
        raise SystemExit("resolved order directory escaped orders root")
    existed_before = order_dir.exists()

    if order_dir.exists() and not args.allow_existing:
        raise SystemExit(f"Order folder already exists: {order_dir}")

    for subdir in ORDER_SUBDIRS:
        (order_dir / subdir).mkdir(parents=True, exist_ok=True)

    created_at = now.isoformat()
    state = {
        "state_version": 1,
        "order_id": order_id,
        "state": "IDLE",
        "previous_state": None,
        "current_gate": "base",
        "fixed_contact": args.contact,
        "last_action": "order_folder_created",
        "next_action": "wait_for_orchestrator",
        "created_at": created_at,
        "updated_at": created_at,
        "last_validated_at": None,
        "locked_by": None,
        "lock_expires_at": None,
        "can_send_message": False,
        "requires_owner_approval": False,
        "blocked_reason": None,
    }
    state_path = order_dir / "00_state" / "state.json"
    if not existed_before or not state_path.exists() or args.overwrite_state:
        write_json(state_path, state)

    for jsonl_name in ["events.jsonl", "approvals.jsonl"]:
        (order_dir / "00_state" / jsonl_name).touch(exist_ok=True)

    order_event = {
        "event": "order_created",
        "order_id": order_id,
        "title": args.title,
        "contact": args.contact,
        "order_path": str(order_dir.relative_to(project_root)),
        "timestamp": created_at,
    }
    if not existed_before:
        append_jsonl(order_dir / "00_state" / "events.jsonl", order_event)
        append_jsonl(project_root / "ledgers" / "orders.jsonl", order_event)

    readme = (
        f"# {args.title}\n\n"
        f"- Order ID: {order_id}\n"
        f"- Contact: {args.contact or 'not set'}\n"
        f"- Created at: {created_at}\n\n"
        "Generated artifacts should be written by their owning skills.\n"
    )
    readme_path = order_dir / "README.md"
    if not readme_path.exists() or args.overwrite_state:
        atomic_write_text(readme_path, readme)

    if args.with_templates:
        copy_order_templates(project_root, order_dir, args.overwrite_templates)

    return order_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a PPT order folder.")
    parser.add_argument("--title", required=True, help="Human-readable order title.")
    parser.add_argument("--contact", default=None, help="Fixed customer-service contact.")
    parser.add_argument("--orders-root", default="orders", help="Orders root relative to project root.")
    parser.add_argument("--sequence", type=int, default=None, help="Override daily sequence number.")
    parser.add_argument("--order-id", default=None, help="Override generated order id.")
    parser.add_argument("--allow-existing", action="store_true", help="Reuse an existing folder.")
    parser.add_argument("--overwrite-state", action="store_true", help="Overwrite state.json and README when reusing.")
    parser.add_argument("--with-templates", action="store_true", help="Copy order templates and schemas into the order folder.")
    parser.add_argument("--overwrite-templates", action="store_true", help="Overwrite existing copied template files.")
    return parser.parse_args()


def main() -> None:
    order_dir = create_order(parse_args())
    print(order_dir)


if __name__ == "__main__":
    main()
