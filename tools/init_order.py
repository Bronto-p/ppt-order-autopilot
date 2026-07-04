#!/usr/bin/env python3
"""Create a standard PPT order folder.

This script intentionally does not create downstream generated artifacts such as
chat_coverage_report.md or requirements.json. Those files should be produced by
their owning skills so validation gates cannot pass accidentally.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path


TZ_SHANGHAI = timezone(timedelta(hours=8))

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
]


def slugify_title(title: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", " ", title).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:60] or "untitled"


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


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def create_order(args: argparse.Namespace) -> Path:
    project_root = Path(__file__).resolve().parents[1]
    orders_root = (project_root / args.orders_root).resolve()
    orders_root.mkdir(parents=True, exist_ok=True)

    now = datetime.now(TZ_SHANGHAI)
    date_prefix = now.strftime("%Y-%m-%d")
    sequence = args.sequence or next_sequence(orders_root, date_prefix)
    order_id = args.order_id or f"{date_prefix}_{sequence:03d}"
    title_slug = slugify_title(args.title)
    order_dir = orders_root / f"{order_id}_{title_slug}"

    if order_dir.exists() and not args.allow_existing:
        raise SystemExit(f"Order folder already exists: {order_dir}")

    for subdir in ORDER_SUBDIRS:
        (order_dir / subdir).mkdir(parents=True, exist_ok=True)

    created_at = now.isoformat()
    state = {
        "order_id": order_id,
        "state": "IDLE",
        "fixed_contact": args.contact,
        "last_action": "order_folder_created",
        "next_action": "wait_for_orchestrator",
        "created_at": created_at,
        "updated_at": created_at,
        "can_send_message": False,
        "requires_owner_approval": False,
        "blocked_reason": None,
    }
    write_json(order_dir / "00_state" / "state.json", state)

    for jsonl_name in ["events.jsonl", "approvals.jsonl"]:
        (order_dir / "00_state" / jsonl_name).touch(exist_ok=True)

    append_jsonl(
        order_dir / "00_state" / "events.jsonl",
        {
            "event": "order_created",
            "order_id": order_id,
            "title": args.title,
            "contact": args.contact,
            "timestamp": created_at,
        },
    )

    readme = (
        f"# {args.title}\n\n"
        f"- Order ID: {order_id}\n"
        f"- Contact: {args.contact or 'not set'}\n"
        f"- Created at: {created_at}\n\n"
        "Generated artifacts should be written by their owning skills.\n"
    )
    (order_dir / "README.md").write_text(readme, encoding="utf-8")

    return order_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a PPT order folder.")
    parser.add_argument("--title", required=True, help="Human-readable order title.")
    parser.add_argument("--contact", default=None, help="Fixed customer-service contact.")
    parser.add_argument("--orders-root", default="orders", help="Orders root relative to project root.")
    parser.add_argument("--sequence", type=int, default=None, help="Override daily sequence number.")
    parser.add_argument("--order-id", default=None, help="Override generated order id.")
    parser.add_argument("--allow-existing", action="store_true", help="Reuse an existing folder.")
    return parser.parse_args()


def main() -> None:
    order_dir = create_order(parse_args())
    print(order_dir)


if __name__ == "__main__":
    main()

