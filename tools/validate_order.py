#!/usr/bin/env python3
"""Validate hard gates for a PPT order folder."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable


ALLOWED_REQUIREMENT_CONFIDENCE = {"high", "medium", "low", "inferred", "missing"}
ALLOWED_ATTACHMENT_STATUS = {"success", "failed", "skipped"}
ALLOWED_QA_STATUS = {"pass", "blocked", "failed"}


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


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def exists_nonempty(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def load_json(path: Path, result: ValidationResult, label: str) -> dict[str, Any] | None:
    if not exists_nonempty(path):
        result.errors.append(f"missing or empty {label}")
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        result.errors.append(f"invalid JSON in {label}: line {exc.lineno} column {exc.colno}")
        return None
    if not isinstance(payload, dict):
        result.errors.append(f"{label} must be a JSON object")
        return None
    return payload


def load_json_optional(path: Path, result: ValidationResult, label: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path, result, label)


def load_jsonl(path: Path, result: ValidationResult, label: str, require_records: bool = True) -> list[dict[str, Any]]:
    if not path.exists():
        result.errors.append(f"missing {label}")
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as file:
            for line_no, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    result.errors.append(f"invalid JSONL in {label}: line {line_no} column {exc.colno}")
                    continue
                if not isinstance(payload, dict):
                    result.errors.append(f"{label} line {line_no} must be a JSON object")
                    continue
                records.append(payload)
    except OSError as exc:
        result.errors.append(f"could not read {label}: {exc}")
        return []
    if require_records and not records:
        result.errors.append(f"missing records in {label}")
    return records


def load_state_machine(result: ValidationResult) -> dict[str, Any] | None:
    return load_json(project_root() / "configs" / "state_machine.json", result, "configs/state_machine.json")


def approval_ids(order_dir: Path, result: ValidationResult) -> set[str]:
    local_records = load_jsonl(order_dir / "00_state" / "approvals.jsonl", result, "00_state/approvals.jsonl", False)
    global_path = project_root() / "ledgers" / "approvals.jsonl"
    global_records = load_jsonl(global_path, result, "ledgers/approvals.jsonl", False) if global_path.exists() else []
    return {
        str(record.get("approval_id"))
        for record in [*local_records, *global_records]
        if record.get("approval_id") and record.get("status") == "approved"
    }


def check_state_machine(order_dir: Path, result: ValidationResult, state: dict[str, Any]) -> None:
    machine = load_state_machine(result)
    if not machine:
        return
    states = machine.get("states")
    if not isinstance(states, dict):
        result.errors.append("configs/state_machine.json states must be an object")
        return
    current_state = state.get("state")
    result.require(isinstance(current_state, str), "state.json state must be a string")
    if not isinstance(current_state, str):
        return
    result.require(current_state in states, f"state.json state is not in state machine: {current_state}")

    previous_state = state.get("previous_state")
    if isinstance(previous_state, str) and previous_state in states:
        allowed_next = states.get(previous_state, {}).get("allowed_next", [])
        result.require(
            current_state in allowed_next or previous_state == current_state,
            f"illegal state transition: {previous_state} -> {current_state}",
        )

    required_artifacts = states.get(current_state, {}).get("required_artifacts", [])
    if isinstance(required_artifacts, list):
        for artifact in required_artifacts:
            if not isinstance(artifact, str) or artifact.startswith("ledgers/"):
                continue
            path = order_dir / artifact
            result.require(path.exists(), f"state {current_state} requires missing artifact: {artifact}")


def check_base(order_dir: Path, result: ValidationResult) -> None:
    state = load_json(order_dir / "00_state" / "state.json", result, "00_state/state.json")
    if state:
        for key in ["order_id", "state", "created_at", "updated_at"]:
            result.require(key in state, f"state.json missing key: {key}")
        result.require(state.get("state_version") == 1, "state.json state_version must be 1")
        check_state_machine(order_dir, result, state)
    result.require((order_dir / "00_state" / "events.jsonl").exists(), "missing 00_state/events.jsonl")


def check_coverage(order_dir: Path, result: ValidationResult) -> None:
    result.require(
        exists_nonempty(order_dir / "01_chat" / "chat_coverage_report.md"),
        "missing or empty 01_chat/chat_coverage_report.md",
    )
    coverage = load_json(order_dir / "01_chat" / "coverage_result.json", result, "01_chat/coverage_result.json")
    if not coverage:
        return
    result.require(coverage.get("status") == "success", "coverage_result.json status must be success")
    result.require(isinstance(coverage.get("screens_captured"), int) and coverage["screens_captured"] > 0, "coverage must capture at least one screen")
    result.require(not is_empty_value(coverage.get("top_anchor")), "coverage_result.json missing top_anchor")
    result.require(not is_empty_value(coverage.get("bottom_anchor")), "coverage_result.json missing bottom_anchor")
    overlap = coverage.get("adjacent_overlap_checks")
    if isinstance(overlap, dict):
        passed = overlap.get("passed")
        total = overlap.get("total")
        result.require(isinstance(passed, int) and isinstance(total, int), "coverage overlap passed/total must be integers")
        if isinstance(passed, int) and isinstance(total, int):
            result.require(passed == total, "coverage adjacent overlap checks did not all pass")
    else:
        result.errors.append("coverage_result.json missing adjacent_overlap_checks object")
    blocking = coverage.get("blocking_issues", [])
    result.require(isinstance(blocking, list), "coverage_result.json blocking_issues must be a list")
    if isinstance(blocking, list):
        result.require(not blocking, "coverage_result.json has blocking issues")


def check_message_index(order_dir: Path, result: ValidationResult) -> None:
    records = load_jsonl(order_dir / "01_chat" / "message_index.jsonl", result, "01_chat/message_index.jsonl")
    for index, record in enumerate(records, start=1):
        for key in ["message_id", "screen_ids", "sender", "sent_at", "text", "attachments", "ocr_confidence"]:
            result.require(key in record, f"message_index.jsonl record {index} missing {key}")
        result.require(isinstance(record.get("screen_ids"), list), f"message_index.jsonl record {index} screen_ids must be a list")
        result.require(isinstance(record.get("attachments"), list), f"message_index.jsonl record {index} attachments must be a list")


def check_attachment_index(order_dir: Path, result: ValidationResult) -> list[dict[str, Any]]:
    records = load_jsonl(
        order_dir / "02_attachments_raw" / "attachment_index.jsonl",
        result,
        "02_attachments_raw/attachment_index.jsonl",
        False,
    )
    for index, record in enumerate(records, start=1):
        for key in ["attachment_id", "saved_path", "source_message_id", "sha256", "download_status"]:
            result.require(key in record, f"attachment_index.jsonl record {index} missing {key}")
        status = record.get("download_status")
        result.require(status in ALLOWED_ATTACHMENT_STATUS, f"attachment_index.jsonl record {index} has invalid download_status")
        if status == "success":
            result.require(
                isinstance(record.get("sha256"), str) and re.fullmatch(r"sha256:[a-f0-9]{64}", record["sha256"]),
                f"attachment_index.jsonl record {index} success attachment must have sha256:<64 hex>",
            )
            saved_path = record.get("saved_path")
            if isinstance(saved_path, str):
                result.require((order_dir / saved_path).exists(), f"attachment_index.jsonl record {index} saved_path does not exist: {saved_path}")
    return records


def failed_attachments(order_dir: Path, result: ValidationResult) -> list[dict[str, Any]]:
    return [record for record in check_attachment_index(order_dir, result) if record.get("download_status") == "failed"]


def check_chat_capture(order_dir: Path, result: ValidationResult) -> None:
    check_base(order_dir, result)
    check_coverage(order_dir, result)
    check_message_index(order_dir, result)
    check_attachment_index(order_dir, result)
    result.warn(
        (order_dir / "02_attachments_raw" / "failed_downloads.md").exists(),
        "missing 02_attachments_raw/failed_downloads.md; acceptable only if no downloads failed",
    )


def check_requirements(order_dir: Path, result: ValidationResult) -> dict[str, Any] | None:
    requirements = load_json(order_dir / "03_requirements" / "requirements.json", result, "03_requirements/requirements.json")
    if not requirements:
        return None
    for field_name, field in requirements.items():
        if not isinstance(field, dict):
            result.errors.append(f"{field_name} must be an object")
            continue
        confidence = field.get("confidence")
        result.require(confidence in ALLOWED_REQUIREMENT_CONFIDENCE, f"{field_name} has invalid confidence")
        result.require("value" in field, f"{field_name} missing value key")
        result.require("evidence" in field, f"{field_name} missing evidence key")
        if field.get("required") is True:
            result.require(not is_empty_value(field.get("value")), f"{field_name} is required but value is empty")
            result.require(not is_empty_value(field.get("evidence")), f"{field_name} is required but evidence is empty")
            result.require(confidence != "missing", f"{field_name} is required but confidence is missing")
    return requirements


def check_briefing(order_dir: Path, result: ValidationResult) -> None:
    check_chat_capture(order_dir, result)
    req_dir = order_dir / "03_requirements"
    result.require(exists_nonempty(req_dir / "order_brief.md"), "missing or empty 03_requirements/order_brief.md")
    result.require((req_dir / "missing_questions.md").exists(), "missing 03_requirements/missing_questions.md")
    result.require((req_dir / "conflicts.md").exists(), "missing 03_requirements/conflicts.md")
    check_requirements(order_dir, result)


def check_pending_approval(order_dir: Path, result: ValidationResult) -> dict[str, Any] | None:
    req_dir = order_dir / "03_requirements"
    result.require(exists_nonempty(req_dir / "pending_approval.md"), "missing or empty 03_requirements/pending_approval.md")
    pending = load_json(req_dir / "pending_approval.json", result, "03_requirements/pending_approval.json")
    if not pending:
        return None
    for key in ["approval_id", "action_type", "draft_message", "draft_sha256", "status"]:
        result.require(key in pending, f"pending_approval.json missing {key}")
    result.require(pending.get("status") in {"pending", "approved", "rejected"}, "pending_approval.json status is invalid")
    draft_sha = pending.get("draft_sha256")
    result.require(
        isinstance(draft_sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", draft_sha),
        "pending_approval.json draft_sha256 must be sha256:<64 hex>",
    )
    return pending


def check_decision(order_dir: Path, result: ValidationResult) -> None:
    check_briefing(order_dir, result)
    req_dir = order_dir / "03_requirements"
    result.require(exists_nonempty(req_dir / "decision.md"), "missing or empty 03_requirements/decision.md")
    check_pending_approval(order_dir, result)


def deliverables_from_contract(order_dir: Path, result: ValidationResult) -> set[str]:
    contract = load_json(order_dir / "03_requirements" / "production_contract.json", result, "03_requirements/production_contract.json")
    if not contract:
        return set()
    deliverables = contract.get("deliverables")
    result.require(isinstance(deliverables, list) and bool(deliverables), "production_contract.json deliverables must be a non-empty list")
    if not isinstance(deliverables, list):
        return set()
    normalized = {str(item).lower() for item in deliverables}
    result.require(normalized <= {"pptx", "pdf"}, "production_contract.json deliverables may only include pptx/pdf")

    approval = contract.get("approval")
    result.require(isinstance(approval, dict), "production_contract.json approval must be an object")
    if isinstance(approval, dict):
        approval_id = approval.get("approval_id")
        result.require(not is_empty_value(approval_id), "production_contract.json approval.approval_id is required")
        if approval_id:
            result.require(str(approval_id) in approval_ids(order_dir, result), f"production approval_id not approved: {approval_id}")
    return normalized


def check_production(order_dir: Path, result: ValidationResult) -> None:
    check_decision(order_dir, result)
    failed = failed_attachments(order_dir, result)
    result.require(not failed, "failed attachment downloads block production")
    deliverables_from_contract(order_dir, result)


def qa_status_from_markdown(path: Path) -> str | None:
    if not exists_nonempty(path):
        return None
    content = path.read_text(encoding="utf-8")
    match = re.search(r"Status:\s*(pass|blocked|failed)", content, re.IGNORECASE)
    return match.group(1).lower() if match else None


def check_qa(order_dir: Path, result: ValidationResult) -> None:
    check_production(order_dir, result)
    required_deliverables = deliverables_from_contract(order_dir, result)
    prod_dir = order_dir / "05_production"
    if "pptx" in required_deliverables:
        result.require(any(prod_dir.glob("*.pptx")), "missing production PPTX")
    if "pdf" in required_deliverables:
        result.require(any(prod_dir.glob("*.pdf")), "missing production PDF")

    result.require(exists_nonempty(order_dir / "06_qa" / "qa_report.md"), "missing or empty 06_qa/qa_report.md")
    qa_result = load_json_optional(order_dir / "06_qa" / "qa_result.json", result, "06_qa/qa_result.json")
    if qa_result:
        status = qa_result.get("status")
        result.require(status in ALLOWED_QA_STATUS, "qa_result.json status is invalid")
        result.require(status == "pass", "qa_result.json status must be pass")
        result.require(set(qa_result.get("required_deliverables", [])) >= required_deliverables, "qa_result.json missing required deliverables")
    else:
        status = qa_status_from_markdown(order_dir / "06_qa" / "qa_report.md")
        result.require(status == "pass", "qa_report.md Status must be pass")


def check_delivery(order_dir: Path, result: ValidationResult) -> None:
    check_qa(order_dir, result)
    result.require(exists_nonempty(order_dir / "07_delivery" / "delivery_message.md"), "missing or empty 07_delivery/delivery_message.md")
    result.require(approval_ids(order_dir, result), "missing approved approval record before delivery")


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
