#!/usr/bin/env python3
"""Validate hard gates for a PPT order folder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def warn(self, condition: bool, message: str) -> None:
        if not condition:
            self.warnings.append(message)


def exists_nonempty(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def jsonl_has_records(path: Path) -> bool:
    if not exists_nonempty(path):
        return False
    with path.open("r", encoding="utf-8") as file:
        return any(line.strip() for line in file)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def check_base(order_dir: Path, result: ValidationResult) -> None:
    state_path = order_dir / "00_state" / "state.json"
    result.require(state_path.exists(), "missing 00_state/state.json")
    if state_path.exists():
        state = load_json(state_path)
        for key in ["order_id", "state", "created_at", "updated_at"]:
            result.require(key in state, f"state.json missing key: {key}")
    result.require((order_dir / "00_state" / "events.jsonl").exists(), "missing 00_state/events.jsonl")


def check_chat_capture(order_dir: Path, result: ValidationResult) -> None:
    check_base(order_dir, result)
    result.require(
        exists_nonempty(order_dir / "01_chat" / "chat_coverage_report.md"),
        "missing or empty 01_chat/chat_coverage_report.md",
    )
    result.require(
        jsonl_has_records(order_dir / "01_chat" / "message_index.jsonl"),
        "missing or empty 01_chat/message_index.jsonl",
    )
    result.require(
        (order_dir / "02_attachments_raw" / "attachment_index.jsonl").exists(),
        "missing 02_attachments_raw/attachment_index.jsonl",
    )
    result.warn(
        (order_dir / "02_attachments_raw" / "failed_downloads.md").exists(),
        "missing 02_attachments_raw/failed_downloads.md; acceptable only if no downloads failed",
    )


def check_briefing(order_dir: Path, result: ValidationResult) -> None:
    check_chat_capture(order_dir, result)
    req_dir = order_dir / "03_requirements"
    result.require(exists_nonempty(req_dir / "order_brief.md"), "missing or empty 03_requirements/order_brief.md")
    result.require(exists_nonempty(req_dir / "requirements.json"), "missing or empty 03_requirements/requirements.json")
    result.require((req_dir / "missing_questions.md").exists(), "missing 03_requirements/missing_questions.md")
    result.require((req_dir / "conflicts.md").exists(), "missing 03_requirements/conflicts.md")
    if (req_dir / "requirements.json").exists():
        requirements = load_json(req_dir / "requirements.json")
        for field_name, field in requirements.items():
            if isinstance(field, dict) and field.get("required") is True:
                result.require("confidence" in field, f"{field_name} missing confidence")
                result.require("evidence" in field, f"{field_name} missing evidence key")


def check_decision(order_dir: Path, result: ValidationResult) -> None:
    check_briefing(order_dir, result)
    req_dir = order_dir / "03_requirements"
    result.require(exists_nonempty(req_dir / "decision.md"), "missing or empty 03_requirements/decision.md")
    result.require(exists_nonempty(req_dir / "pending_approval.md"), "missing or empty 03_requirements/pending_approval.md")


def check_production(order_dir: Path, result: ValidationResult) -> None:
    check_decision(order_dir, result)
    result.require(
        exists_nonempty(order_dir / "03_requirements" / "production_contract.json"),
        "missing or empty 03_requirements/production_contract.json",
    )
    result.require(
        jsonl_has_records(order_dir / "00_state" / "approvals.jsonl"),
        "missing approval record before production",
    )


def check_qa(order_dir: Path, result: ValidationResult) -> None:
    check_production(order_dir, result)
    prod_dir = order_dir / "05_production"
    result.require(any(prod_dir.glob("*.pptx")), "missing production PPTX")
    result.warn(any(prod_dir.glob("*.pdf")), "missing production PDF")
    result.require(exists_nonempty(order_dir / "06_qa" / "qa_report.md"), "missing or empty 06_qa/qa_report.md")


def check_delivery(order_dir: Path, result: ValidationResult) -> None:
    check_qa(order_dir, result)
    result.require(exists_nonempty(order_dir / "07_delivery" / "delivery_message.md"), "missing or empty 07_delivery/delivery_message.md")


GATES: dict[str, Callable[[Path, ValidationResult], None]] = {
    "base": check_base,
    "chat_capture": check_chat_capture,
    "briefing": check_briefing,
    "decision": check_decision,
    "production": check_production,
    "qa": check_qa,
    "delivery": check_delivery,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a PPT order folder gate.")
    parser.add_argument("order_dir", help="Order folder path.")
    parser.add_argument("--gate", choices=sorted(GATES), default="base")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    order_dir = Path(args.order_dir).resolve()
    result = ValidationResult()
    result.require(order_dir.exists() and order_dir.is_dir(), f"not an order directory: {order_dir}")
    if result.ok:
        GATES[args.gate](order_dir, result)

    for warning in result.warnings:
        print(f"WARN: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")

    if result.ok:
        print(f"OK: {args.gate} gate passed for {order_dir}")
        return
    raise SystemExit(1)


if __name__ == "__main__":
    main()

