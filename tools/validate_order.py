#!/usr/bin/env python3
"""Validate hard gates for a PPT order folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageChops, ImageDraw

from bootstrap_runtime import ledger_root


ALLOWED_REQUIREMENT_CONFIDENCE = {"high", "medium", "low", "inferred", "missing"}
ALLOWED_ATTACHMENT_STATUS = {"success", "failed", "skipped"}
ALLOWED_QA_STATUS = {"pass", "blocked", "failed"}
ALLOWED_WORKER_REASONING = {"medium", "high"}
ALLOWED_EXECUTION_MODES = {"customer_order", "owner_direct"}
ALLOWED_INTAKE_SOURCES = {"wecom", "codex_attachment", "workspace_file"}
ALLOWED_OUTPUT_MODES = {"image_first", "hybrid", "template_native", "editable_reconstruction"}
ALLOWED_PRODUCTION_MODES = ALLOWED_OUTPUT_MODES | {"mixed"}
IMAGE_GENERATION_MODES = {"image_first", "hybrid"}
ALLOWED_STYLE_SOURCES = {"approved_sample", "customer_template", "source_deck", "approved_style_brief"}
STYLE_ANCHOR_ROLES = {"approved_sample_style_anchor", "style_anchor"}
TEMPLATE_ROLES = {"template_reference", "template_master"}
PAGE_FAMILY_ROLES = {"page_family_reference", "cover_reference", "section_reference", "content_reference", "data_reference", "image_heavy_reference"}
NAVIGATION_ROLES = {"navigation_reference", "navigation_bar_reference"}


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
    if isinstance(value, (list, tuple, set, dict)):
        return not value
    return False


def is_nonempty_collection(value: Any) -> bool:
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return not is_empty_value(value)


def has_deep_content(value: Any) -> bool:
    if isinstance(value, dict):
        return any(has_deep_content(child) for child in value.values())
    if isinstance(value, list):
        return any(has_deep_content(child) for child in value)
    return not is_empty_value(value)


def resolve_within(root: Path, rel_path: Any) -> Path | None:
    """Resolve a runtime path without allowing absolute paths or parent escapes."""
    if not isinstance(rel_path, str) or not rel_path.strip():
        return None
    candidate = Path(rel_path)
    if candidate.is_absolute():
        return None
    root = root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def safe_runtime_path(root: Path, rel_path: Any, result: ValidationResult, label: str) -> Path | None:
    path = resolve_within(root, rel_path)
    result.require(path is not None, f"{label} must stay inside {root}")
    return path


def rel_path_exists(order_dir: Path, rel_path: Any) -> bool:
    path = resolve_within(order_dir, rel_path)
    return path is not None and path.exists()


def path_list(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


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


def order_id_from_state(order_dir: Path, result: ValidationResult) -> str | None:
    state = load_json(order_dir / "00_state" / "state.json", result, "00_state/state.json")
    if not state:
        return None
    order_id = state.get("order_id")
    result.require(isinstance(order_id, str) and bool(order_id), "state.json order_id must be a non-empty string")
    return order_id if isinstance(order_id, str) and order_id else None


def load_order_state(order_dir: Path, result: ValidationResult) -> dict[str, Any] | None:
    return load_json(order_dir / "00_state" / "state.json", result, "00_state/state.json")


def execution_mode(order_dir: Path, result: ValidationResult) -> str | None:
    state = load_order_state(order_dir, result)
    if not state:
        return None
    mode = state.get("execution_mode", "customer_order")
    result.require(mode in ALLOWED_EXECUTION_MODES, "state.json execution_mode is invalid")
    return mode if mode in ALLOWED_EXECUTION_MODES else None


def approved_records(order_dir: Path, result: ValidationResult) -> list[dict[str, Any]]:
    local_records = load_jsonl(order_dir / "00_state" / "approvals.jsonl", result, "00_state/approvals.jsonl", False)
    global_path = ledger_root(project_root()) / "approvals.jsonl"
    global_records = load_jsonl(global_path, result, "ledgers/approvals.jsonl", False) if global_path.exists() else []
    order_id = order_id_from_state(order_dir, result)
    return [
        record
        for record in [*local_records, *global_records]
        if record.get("approval_id")
        and record.get("status") == "approved"
        and order_id is not None
        and record.get("order_id") == order_id
    ]


def approval_ids(order_dir: Path, result: ValidationResult, action_types: set[str] | None = None) -> set[str]:
    return {
        str(record["approval_id"])
        for record in approved_records(order_dir, result)
        if action_types is None or record.get("action_type") in action_types
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
    result.require("previous_state" in state, "state.json previous_state is required")
    if current_state == machine.get("initial_state"):
        result.require(previous_state is None or previous_state == current_state, "initial state previous_state must be null or itself")
    else:
        result.require(isinstance(previous_state, str) and previous_state in states, "non-initial state requires a valid previous_state")
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
            path = safe_runtime_path(order_dir, artifact, result, f"state {current_state} artifact {artifact}")
            if path is not None:
                result.require(path.exists(), f"state {current_state} requires missing artifact: {artifact}")


def check_base(order_dir: Path, result: ValidationResult) -> None:
    state = load_json(order_dir / "00_state" / "state.json", result, "00_state/state.json")
    if state:
        for key in ["order_id", "state", "created_at", "updated_at"]:
            result.require(key in state, f"state.json missing key: {key}")
        result.require(state.get("state_version") == 1, "state.json state_version must be 1")
        mode = state.get("execution_mode", "customer_order")
        result.require(mode in ALLOWED_EXECUTION_MODES, "state.json execution_mode is invalid")
        intake_source = state.get("intake_source")
        result.require(intake_source is None or intake_source in ALLOWED_INTAKE_SOURCES, "state.json intake_source is invalid")
        expected_target = "owner_codex" if mode == "owner_direct" else "customer_wecom"
        result.require(state.get("delivery_target", expected_target) == expected_target, "state.json delivery_target conflicts with execution_mode")
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
    source_type = coverage.get("source_type", "wecom")
    result.require(source_type in ALLOWED_INTAKE_SOURCES, "coverage_result.json source_type is invalid")
    if source_type in {"codex_attachment", "workspace_file"}:
        result.require(
            is_nonempty_collection(coverage.get("source_attachment_paths")),
            "direct file intake requires source_attachment_paths",
        )
        for source_path in path_list(coverage.get("source_attachment_paths")):
            result.require(rel_path_exists(order_dir, source_path), f"direct source file does not exist: {source_path}")
    else:
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
            path = safe_runtime_path(order_dir, saved_path, result, f"attachment_index.jsonl record {index} saved_path")
            if path is not None:
                result.require(path.exists(), f"attachment_index.jsonl record {index} saved_path does not exist: {saved_path}")
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
    result.require(not is_empty_value(pending.get("draft_message")), "pending_approval.json draft_message must not be empty")
    result.require(pending.get("status") in {"pending", "approved", "rejected"}, "pending_approval.json status is invalid")
    draft_sha = pending.get("draft_sha256")
    result.require(
        isinstance(draft_sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", draft_sha),
        "pending_approval.json draft_sha256 must be sha256:<64 hex>",
    )
    draft_message = pending.get("draft_message")
    if isinstance(draft_message, str) and isinstance(draft_sha, str):
        result.require(sha256_text(draft_message) == draft_sha, "pending_approval.json draft_sha256 does not match draft_message")

    order_id = order_id_from_state(order_dir, result)
    result.require(pending.get("order_id") == order_id, "pending_approval.json order_id must match state.json")

    if pending.get("status") == "approved":
        matches = [
            record
            for record in approved_records(order_dir, result)
            if record.get("approval_id") == pending.get("approval_id")
        ]
        result.require(bool(matches), "approved pending_approval.json has no matching order-scoped approval record")
        for record in matches:
            result.require(record.get("action_type") == pending.get("action_type"), "approval action_type does not match pending approval")
            result.require(record.get("draft_sha256") == draft_sha, "approval draft_sha256 does not match pending approval")
    return pending


def check_decision(order_dir: Path, result: ValidationResult) -> None:
    check_briefing(order_dir, result)
    req_dir = order_dir / "03_requirements"
    result.require(exists_nonempty(req_dir / "decision.md"), "missing or empty 03_requirements/decision.md")
    check_pending_approval(order_dir, result)


def load_production_contract(order_dir: Path, result: ValidationResult) -> dict[str, Any] | None:
    return load_json(order_dir / "03_requirements" / "production_contract.json", result, "03_requirements/production_contract.json")


def contract_deck(contract: dict[str, Any]) -> dict[str, Any]:
    deck = contract.get("deck")
    if isinstance(deck, dict):
        return deck
    return contract


def contract_deliverables(contract: dict[str, Any]) -> set[str]:
    deck = contract_deck(contract)
    deliverables = deck.get("deliverables")
    if not isinstance(deliverables, list):
        return set()
    return {str(item).lower() for item in deliverables}


def deliverables_from_contract(order_dir: Path, result: ValidationResult) -> set[str]:
    contract = load_production_contract(order_dir, result)
    if not contract:
        return set()
    deck = contract_deck(contract)
    deliverables = deck.get("deliverables")
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
            result.require(
                str(approval_id)
                in approval_ids(
                    order_dir,
                    result,
                    {"accept_order", "approve_production", "owner_direct_instruction"},
                ),
                f"production approval_id not approved for production: {approval_id}",
            )
    return normalized


def check_production(order_dir: Path, result: ValidationResult) -> None:
    mode = execution_mode(order_dir, result)
    if mode == "owner_direct":
        check_briefing(order_dir, result)
        result.require(
            bool(approval_ids(order_dir, result, {"owner_direct_instruction", "approve_production"})),
            "owner_direct production requires an order-scoped owner instruction approval",
        )
    else:
        check_decision(order_dir, result)
    failed = failed_attachments(order_dir, result)
    result.require(not failed, "failed attachment downloads block production")
    deliverables_from_contract(order_dir, result)


def required_requirement_fields(order_dir: Path, result: ValidationResult) -> set[str]:
    requirements = check_requirements(order_dir, result)
    if not requirements:
        return set()
    return {
        field_name
        for field_name, field in requirements.items()
        if isinstance(field, dict) and field.get("required") is True and not is_empty_value(field.get("value"))
    }


def check_exact_content(label: str, exact_content: Any, result: ValidationResult) -> None:
    result.require(isinstance(exact_content, dict), f"{label} exact_content must be an object")
    if not isinstance(exact_content, dict):
        return
    result.require(has_deep_content(exact_content), f"{label} exact_content is empty")
    result.require(set(exact_content.keys()) - {"topic", "purpose"}, f"{label} exact_content cannot only contain topic/purpose")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def check_contract_accuracy(order_dir: Path, result: ValidationResult) -> None:
    check_production(order_dir, result)
    contract = load_production_contract(order_dir, result)
    if not contract:
        return

    deck = contract.get("deck")
    result.require(isinstance(deck, dict), "production_contract.json deck must be an object")
    if not isinstance(deck, dict):
        return
    page_count = deck.get("page_count")
    result.require(isinstance(page_count, int) and page_count > 0, "production_contract.deck.page_count must be a positive integer")

    method = contract.get("method")
    result.require(isinstance(method, dict), "production_contract.method must be an object")
    if isinstance(method, dict):
        result.require(method.get("production_mode") in ALLOWED_PRODUCTION_MODES, "production_mode is invalid")
        result.require(method.get("subagents_required") is True, "subagents_required must be true")
        result.require(method.get("default_reasoning_level") in ALLOWED_WORKER_REASONING, "default reasoning must be medium/high")

    style_kit = contract.get("style_kit")
    result.require(isinstance(style_kit, dict), "production_contract.style_kit must be an object")
    if isinstance(style_kit, dict):
        result.require(style_kit.get("path") == "04_sample/style_kit/style_kit.json", "style_kit.path must point to 04_sample/style_kit/style_kit.json")
        result.require(isinstance(style_kit.get("required"), bool), "style_kit.required must be boolean")
        result.require(style_kit.get("source_type") in ALLOWED_STYLE_SOURCES, "style_kit.source_type is invalid")

    asset_registry = contract.get("asset_registry")
    result.require(isinstance(asset_registry, list), "production_contract.asset_registry must be a list")
    registered_assets: dict[str, dict[str, Any]] = {}
    if isinstance(asset_registry, list):
        for index, asset in enumerate(asset_registry, start=1):
            result.require(isinstance(asset, dict), f"asset_registry record {index} must be an object")
            if not isinstance(asset, dict):
                continue
            for key in ["asset_id", "asset_role", "source_path", "fidelity_rule", "if_missing"]:
                result.require(not is_empty_value(asset.get(key)), f"asset_registry record {index} missing {key}")
            source_path = safe_runtime_path(
                order_dir,
                asset.get("source_path"),
                result,
                f"asset_registry record {index} source_path",
            )
            if source_path is not None and asset.get("if_missing") == "block":
                result.require(source_path.exists(), f"asset_registry record {index} required source_path does not exist")
            if isinstance(asset.get("asset_id"), str):
                registered_assets[asset["asset_id"]] = asset

    slides = contract.get("slides")
    result.require(isinstance(slides, list), "production_contract.slides must be a list")
    if not isinstance(slides, list):
        return
    if isinstance(page_count, int):
        result.require(len(slides) == page_count, "production_contract.slides count must equal deck.page_count")

    seen_slide_numbers: set[int] = set()
    for index, slide in enumerate(slides, start=1):
        label = f"slide {index}"
        result.require(isinstance(slide, dict), f"{label} must be an object")
        if not isinstance(slide, dict):
            continue
        slide_no = slide.get("slide_no")
        result.require(isinstance(slide_no, int) and slide_no > 0, f"{label} slide_no must be positive integer")
        if isinstance(slide_no, int):
            result.require(slide_no not in seen_slide_numbers, f"duplicate slide_no: {slide_no}")
            seen_slide_numbers.add(slide_no)
            label = f"slide {slide_no}"
        for key in ["title", "page_type", "output_mode", "exact_content_source", "job_path"]:
            result.require(not is_empty_value(slide.get(key)), f"{label} missing {key}")
        slide_output_mode = slide.get("output_mode")
        result.require(slide_output_mode in ALLOWED_OUTPUT_MODES, f"{label} output_mode is invalid")
        if isinstance(method, dict) and method.get("production_mode") != "mixed":
            result.require(
                slide_output_mode == method.get("production_mode"),
                f"{label} output_mode must match deck production_mode unless it is mixed",
            )
        content_source = safe_runtime_path(order_dir, slide.get("exact_content_source"), result, f"{label} exact_content_source")
        if content_source is not None:
            result.require(content_source.exists(), f"{label} exact_content_source does not exist")
        asset_ids = slide.get("required_asset_ids")
        result.require(isinstance(asset_ids, list), f"{label} required_asset_ids must be a list")
        if isinstance(asset_ids, list):
            for asset_id in asset_ids:
                if str(asset_id).startswith(("style_", "template_", "navigation_", "page_family_")):
                    continue
                result.require(asset_id in registered_assets, f"{label} references unknown asset_id: {asset_id}")
        job_path = slide.get("job_path")
        if isinstance(job_path, str):
            result.require(job_path == f"05_production/slide_jobs/slide_{slide_no:02d}/job.json", f"{label} job_path must match slide bundle")
            safe_runtime_path(order_dir, job_path, result, f"{label} job_path")

    coverage = contract.get("coverage_matrix")
    if coverage is not None:
        result.require(isinstance(coverage, list), "coverage_matrix must be a list when present")
        covered_sources = " ".join(str(item.get("source", "")) + " " + str(item.get("requirement", "")) for item in coverage if isinstance(item, dict))
        for field_name in required_requirement_fields(order_dir, result):
            result.require(field_name in covered_sources, f"coverage_matrix does not cover required requirement: {field_name}")


def is_sample_required(order_dir: Path, result: ValidationResult) -> bool:
    requirements = check_requirements(order_dir, result)
    if not requirements:
        return False
    sample = requirements.get("sample_required")
    if not isinstance(sample, dict):
        return False
    value = sample.get("value")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "需要", "要", "required"}
    return False


def check_locked_elements(order_dir: Path, result: ValidationResult, locked: dict[str, Any] | None) -> None:
    if not locked:
        return
    canvas = locked.get("canvas")
    result.require(isinstance(canvas, dict), "locked_elements.json canvas must be an object")
    if isinstance(canvas, dict):
        result.require(isinstance(canvas.get("width"), int) and canvas["width"] > 0, "locked canvas width must be positive")
        result.require(isinstance(canvas.get("height"), int) and canvas["height"] > 0, "locked canvas height must be positive")

    strategy = locked.get("render_strategy")
    result.require(strategy in {"reference_only", "post_generation_composite"}, "locked render_strategy is invalid")
    fixed_elements = any(locked.get(name) is not None for name in ["logo", "navigation_bar", "footer", "page_number"])
    if fixed_elements:
        result.require(strategy == "post_generation_composite", "fixed chrome requires post_generation_composite")
    if strategy != "post_generation_composite":
        return

    safe_box = locked.get("content_safe_box")
    result.require(isinstance(safe_box, dict), "locked chrome requires content_safe_box")
    if isinstance(safe_box, dict) and isinstance(canvas, dict):
        values = [safe_box.get(name) for name in ["x", "y", "w", "h"]]
        result.require(all(isinstance(value, int) for value in values), "locked chrome content_safe_box must use integer coordinates")
        if all(isinstance(value, int) for value in values):
            x, y, width, height = values
            result.require(width > 0 and height > 0, "locked chrome content_safe_box must have positive size")
            result.require(x >= 0 and y >= 0, "locked chrome content_safe_box cannot use negative coordinates")
            if isinstance(canvas.get("width"), int) and isinstance(canvas.get("height"), int):
                result.require(x + width <= canvas["width"] and y + height <= canvas["height"], "locked chrome content_safe_box exceeds canvas")
    variants = locked.get("overlay_variants")
    result.require(isinstance(variants, list) and bool(variants), "locked chrome requires overlay_variants")
    skeleton = locked.get("invariant_skeleton")
    result.require(isinstance(skeleton, dict), "locked chrome requires invariant_skeleton")
    skeleton_path = None
    if isinstance(skeleton, dict):
        skeleton_rel = skeleton.get("source_path")
        result.require(isinstance(skeleton_rel, str) and skeleton_rel.startswith("04_sample/style_kit/"), "locked chrome skeleton must stay in style_kit")
        skeleton_path = safe_runtime_path(order_dir, skeleton_rel, result, "locked chrome skeleton source_path")
        skeleton_sha = skeleton.get("sha256")
        result.require(isinstance(skeleton_sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", skeleton_sha), "locked chrome skeleton sha256 is invalid")
        if skeleton_path is not None:
            result.require(skeleton_path.exists(), "locked chrome skeleton does not exist")
            if skeleton_path.exists() and isinstance(skeleton_sha, str):
                result.require(sha256_file(skeleton_path) == skeleton_sha, "locked chrome skeleton sha256 mismatch")

    dynamic_regions = locked.get("dynamic_regions")
    result.require(isinstance(dynamic_regions, list) and bool(dynamic_regions), "locked chrome requires dynamic_regions")
    region_boxes: dict[str, tuple[str, int, int, int, int]] = {}
    if isinstance(dynamic_regions, list) and isinstance(canvas, dict):
        for index, box in enumerate(dynamic_regions, start=1):
            values = [box.get(name) for name in ["x", "y", "w", "h"]] if isinstance(box, dict) else []
            region_id = box.get("region_id") if isinstance(box, dict) else None
            region_role = box.get("role") if isinstance(box, dict) else None
            result.require(isinstance(region_id, str) and bool(region_id), f"locked dynamic region {index} region_id is invalid")
            if isinstance(region_id, str):
                result.require(region_id not in region_boxes, f"locked dynamic region_id is duplicated: {region_id}")
            result.require(region_role in {"active_highlight", "page_number"}, f"locked dynamic region {index} role is invalid")
            result.require(len(values) == 4 and all(isinstance(value, int) for value in values), f"locked dynamic region {index} is invalid")
            if len(values) == 4 and all(isinstance(value, int) for value in values):
                x, y, width, height = values
                result.require(x >= 0 and y >= 0 and width > 0 and height > 0, f"locked dynamic region {index} has invalid geometry")
                if isinstance(canvas.get("width"), int) and isinstance(canvas.get("height"), int):
                    result.require(x + width <= canvas["width"] and y + height <= canvas["height"], f"locked dynamic region {index} exceeds canvas")
                target_box = locked.get("navigation_bar" if region_role == "active_highlight" else "page_number")
                result.require(isinstance(target_box, dict), f"locked dynamic region {index} has no matching locked element")
                if isinstance(target_box, dict):
                    tx, ty, tw, th = (target_box.get(name) for name in ["x", "y", "w", "h"])
                    if all(isinstance(value, int) for value in [tx, ty, tw, th]):
                        result.require(x >= tx and y >= ty and x + width <= tx + tw and y + height <= ty + th, f"locked dynamic region {index} escapes its locked element")
                        if region_role == "active_highlight" and tw * th > 1:
                            result.require(width * height < tw * th, f"locked dynamic region {index} cannot cover the entire navigation bar")
                if isinstance(region_id, str) and region_role in {"active_highlight", "page_number"}:
                    region_boxes[region_id] = (region_role, x, y, width, height)

    page_policy = locked.get("page_number_policy")
    result.require(isinstance(page_policy, dict), "locked chrome requires page_number_policy")
    policy_mode = page_policy.get("mode") if isinstance(page_policy, dict) else None
    result.require(policy_mode in {"none", "plain", "zero_padded_2", "current_over_total", "custom"}, "locked page number policy is invalid")
    if locked.get("page_number") is not None:
        result.require(policy_mode != "none", "locked page number requires a numbering policy")
    contract = load_production_contract(order_dir, result)
    deck_page_count = contract.get("deck", {}).get("page_count") if isinstance(contract, dict) else None
    if policy_mode == "current_over_total":
        result.require(isinstance(page_policy.get("total_slides"), int), "current_over_total page policy requires total_slides")
        if isinstance(deck_page_count, int):
            result.require(page_policy.get("total_slides") == deck_page_count, "page number total_slides must match production contract")
    if policy_mode == "custom":
        result.require(isinstance(page_policy.get("custom_values"), dict) and bool(page_policy.get("custom_values")), "custom page policy requires custom_values")

    skeleton_image = None
    if skeleton_path is not None and skeleton_path.exists():
        try:
            skeleton_image = Image.open(skeleton_path).convert("RGBA")
        except OSError:
            result.errors.append("locked chrome skeleton is not a readable image")
    if not isinstance(variants, list):
        return
    seen_variant_ids: set[str] = set()
    seen_variant_slides: set[int] = set()
    for index, variant in enumerate(variants, start=1):
        result.require(isinstance(variant, dict), f"locked overlay variant {index} must be an object")
        if not isinstance(variant, dict):
            continue
        variant_id = variant.get("variant_id")
        result.require(isinstance(variant_id, str) and bool(variant_id), f"locked overlay variant {index} variant_id is invalid")
        if isinstance(variant_id, str):
            result.require(variant_id not in seen_variant_ids, f"locked overlay variant_id is duplicated: {variant_id}")
            seen_variant_ids.add(variant_id)
        variant_slide = variant.get("slide_no")
        result.require(isinstance(variant_slide, int) and variant_slide > 0, f"locked overlay variant {index} slide_no is invalid")
        if isinstance(variant_slide, int):
            result.require(variant_slide not in seen_variant_slides, f"locked overlay slide_no is duplicated: {variant_slide}")
            seen_variant_slides.add(variant_slide)
        page_number_text = variant.get("page_number_text")
        selected_region_ids = variant.get("dynamic_region_ids")
        result.require(isinstance(selected_region_ids, list) and bool(selected_region_ids), f"locked overlay variant {index} dynamic_region_ids is empty")
        selected_regions = [region_boxes.get(region_id) for region_id in selected_region_ids or [] if isinstance(region_id, str)]
        result.require(all(region is not None for region in selected_regions), f"locked overlay variant {index} references an unknown dynamic region")
        selected_roles = {region[0] for region in selected_regions if region is not None}
        if locked.get("navigation_bar") is not None:
            result.require("active_highlight" in selected_roles, f"locked overlay variant {index} lacks an active highlight region")
        if locked.get("page_number") is not None:
            result.require("page_number" in selected_roles, f"locked overlay variant {index} lacks a page number region")
            result.require(not is_empty_value(page_number_text), f"locked overlay variant {index} page_number_text is required")
        expected_page_number = None
        if isinstance(variant_slide, int) and isinstance(page_policy, dict):
            if policy_mode == "plain":
                expected_page_number = str(variant_slide)
            elif policy_mode == "zero_padded_2":
                expected_page_number = f"{variant_slide:02d}"
            elif policy_mode == "current_over_total" and isinstance(page_policy.get("total_slides"), int):
                expected_page_number = f"{variant_slide}/{page_policy['total_slides']}"
            elif policy_mode == "custom" and isinstance(page_policy.get("custom_values"), dict):
                expected_page_number = page_policy["custom_values"].get(str(variant_slide))
        result.require(page_number_text == expected_page_number, f"locked overlay variant {index} page_number_text violates policy")
        source_rel = variant.get("source_path")
        result.require(isinstance(source_rel, str) and source_rel.startswith("04_sample/style_kit/"), f"locked overlay variant {index} must stay in style_kit")
        source_path = safe_runtime_path(
            order_dir,
            source_rel,
            result,
            f"locked overlay variant {index} source_path",
        )
        expected_sha = variant.get("sha256")
        result.require(
            isinstance(expected_sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", expected_sha),
            f"locked overlay variant {index} sha256 is invalid",
        )
        if source_path is not None:
            result.require(source_path.exists(), f"locked overlay variant {index} source does not exist")
            if source_path.exists() and isinstance(expected_sha, str):
                result.require(sha256_file(source_path) == expected_sha, f"locked overlay variant {index} sha256 mismatch")
            if source_path.exists() and skeleton_image is not None:
                try:
                    variant_image = Image.open(source_path).convert("RGBA")
                    result.require(variant_image.size == skeleton_image.size, f"locked overlay variant {index} canvas differs from skeleton")
                    alpha_histogram = variant_image.getchannel("A").histogram()
                    result.require(sum(alpha_histogram[1:255]) == 0, f"locked overlay variant {index} alpha must be binary")
                    if variant_image.size == skeleton_image.size:
                        invariant_mask = Image.new("L", variant_image.size, 255)
                        mask_draw = ImageDraw.Draw(invariant_mask)
                        for _, x, y, width, height in [region for region in selected_regions if region is not None]:
                            mask_draw.rectangle((x, y, x + width - 1, y + height - 1), fill=0)
                        rgb_difference = ImageChops.difference(variant_image.convert("RGB"), skeleton_image.convert("RGB"))
                        invariant_rgb_difference = Image.new("RGB", variant_image.size, (0, 0, 0))
                        invariant_rgb_difference.paste(rgb_difference, mask=invariant_mask)
                        alpha_difference = ImageChops.difference(variant_image.getchannel("A"), skeleton_image.getchannel("A"))
                        invariant_alpha_difference = Image.new("L", variant_image.size, 0)
                        invariant_alpha_difference.paste(alpha_difference, mask=invariant_mask)
                        result.require(
                            invariant_rgb_difference.getbbox() is None and invariant_alpha_difference.getbbox() is None,
                            f"locked overlay variant {index} changes invariant skeleton pixels",
                        )
                except OSError:
                    result.errors.append(f"locked overlay variant {index} is not a readable image")


def check_sample_accuracy(order_dir: Path, result: ValidationResult) -> None:
    check_contract_accuracy(order_dir, result)
    sample_dir = order_dir / "04_sample"
    style_kit = sample_dir / "style_kit"
    result.require(exists_nonempty(sample_dir / "sample_contract.json") or not is_sample_required(order_dir, result), "sample_required=true requires 04_sample/sample_contract.json")
    kit = load_json(style_kit / "style_kit.json", result, "04_sample/style_kit/style_kit.json")
    if kit:
        source = kit.get("source")
        result.require(isinstance(source, dict), "style_kit.json source must be an object")
        if isinstance(source, dict):
            source_type = source.get("source_type")
            result.require(source_type in ALLOWED_STYLE_SOURCES, "style_kit.json source_type is invalid")
            result.require(is_nonempty_collection(source.get("source_paths")), "style_kit.json source_paths must not be empty")
            for source_path in path_list(source.get("source_paths")):
                result.require(rel_path_exists(order_dir, source_path), f"style_kit source path does not exist: {source_path}")
            if is_sample_required(order_dir, result):
                result.require(source_type == "approved_sample", "sample-required order must use approved_sample style source")
                result.require(is_nonempty_collection(kit.get("approved_sample_paths")), "approved_sample style source requires approved_sample_paths")
                decision_path = source.get("customer_decision_path")
                result.require(
                    decision_path == "04_sample/customer_sample_decision.json",
                    "approved_sample style source must reference customer_sample_decision.json",
                )
                check_customer_sample_decision(order_dir, result, {"approved"})
                approved_reference = load_json(
                    sample_dir / "approved_sample_reference.json",
                    result,
                    "04_sample/approved_sample_reference.json",
                )
                if approved_reference:
                    result.require(
                        approved_reference.get("customer_decision_path") == "04_sample/customer_sample_decision.json",
                        "approved sample reference must link customer_sample_decision.json",
                    )
                    approved_samples = approved_reference.get("approved_samples")
                    result.require(
                        isinstance(approved_samples, list) and bool(approved_samples),
                        "approved sample reference approved_samples must not be empty",
                    )
                    if isinstance(approved_samples, list):
                        for index, approved_sample in enumerate(approved_samples, start=1):
                            sample_path = approved_sample.get("path") if isinstance(approved_sample, dict) else None
                            result.require(
                                isinstance(sample_path, str) and rel_path_exists(order_dir, sample_path),
                                f"approved sample reference item {index} path does not exist",
                            )
            else:
                result.require(source_type in ALLOWED_STYLE_SOURCES - {"approved_sample"}, "direct production must use a non-sample style source")
                approval_id = source.get("approval_id")
                result.require(not is_empty_value(approval_id), "direct style source approval_id is required")
                if approval_id:
                    result.require(str(approval_id) in approval_ids(order_dir, result), "style_kit source approval_id is not approved")
            contract = load_production_contract(order_dir, result)
            contract_style = contract.get("style_kit") if contract else None
            contract_source = contract_style.get("source_type") if isinstance(contract_style, dict) else None
            result.require(source_type == contract_source, "style_kit source_type must match production contract")
        family_refs = kit.get("page_family_refs")
        result.require(isinstance(family_refs, dict) and bool(family_refs), "style_kit.json page_family_refs must not be empty")
    for rel_path in [
        "style_anchor.png",
        "template_master.png",
        "style_kit.json",
        "locked_elements.json",
    ]:
        result.require((style_kit / rel_path).exists(), f"missing style kit artifact: 04_sample/style_kit/{rel_path}")
    locked = load_json(style_kit / "locked_elements.json", result, "04_sample/style_kit/locked_elements.json")
    check_locked_elements(order_dir, result, locked)


def check_customer_sample_decision(
    order_dir: Path,
    result: ValidationResult,
    allowed_statuses: set[str] | None = None,
) -> dict[str, Any] | None:
    decision = load_json(
        order_dir / "04_sample" / "customer_sample_decision.json",
        result,
        "04_sample/customer_sample_decision.json",
    )
    if not decision:
        return None
    order_id = order_id_from_state(order_dir, result)
    result.require(decision.get("order_id") == order_id, "customer sample decision order_id must match state.json")
    status = decision.get("status")
    result.require(status in {"approved", "revision_requested", "ambiguous"}, "customer sample decision status is invalid")
    if allowed_statuses is not None:
        result.require(status in allowed_statuses, f"customer sample decision status must be one of {sorted(allowed_statuses)}")
    result.require(is_nonempty_collection(decision.get("source_message_ids")), "customer sample decision requires source_message_ids")
    result.require(not is_empty_value(decision.get("evidence_text")), "customer sample decision requires evidence_text")
    result.require(decision.get("confidence") in {"high", "medium", "low"}, "customer sample decision confidence is invalid")
    if status == "revision_requested":
        result.require(is_nonempty_collection(decision.get("requested_changes")), "sample revision decision requires requested_changes")
    return decision


def load_slide_jobs(order_dir: Path, result: ValidationResult) -> dict[str, Any] | None:
    return load_json(order_dir / "05_production" / "slide_jobs" / "slide_jobs.json", result, "05_production/slide_jobs/slide_jobs.json")


def check_slide_job_payload(
    order_dir: Path,
    job_path: Path,
    result: ValidationResult,
    expected_job_id: str,
    expected_slide_no: int,
    bundle_dir: Path,
) -> None:
    rel_label = str(job_path.relative_to(order_dir))
    job = load_json(job_path, result, rel_label)
    if not job:
        return
    result.require(job.get("job_id") == expected_job_id, f"{rel_label} job_id does not match slide_jobs.json")
    result.require(job.get("slide_no") == expected_slide_no, f"{rel_label} slide_no does not match slide_jobs.json")
    output_mode = job.get("output_mode")
    result.require(output_mode in ALLOWED_OUTPUT_MODES, f"{rel_label} output_mode is invalid")
    result.require(job.get("attempt") == 1, f"{rel_label} base job attempt must be 1")
    result.require(isinstance(job.get("max_attempts"), int) and 1 <= job["max_attempts"] <= 3, f"{rel_label} max_attempts must be 1-3")
    result.require(isinstance(job.get("deck_context"), dict) and bool(job.get("deck_context")), f"{rel_label} deck_context must be a non-empty object")
    result.require(isinstance(job.get("local_context"), dict) and bool(job.get("local_context")), f"{rel_label} local_context must be a non-empty object")
    check_exact_content(rel_label, job.get("exact_content"), result)
    result.require(isinstance(job.get("visual_constraints"), dict) and bool(job.get("visual_constraints")), f"{rel_label} visual_constraints must be a non-empty object")
    visual_constraints = job.get("visual_constraints")
    input_images = job.get("input_images")
    result.require(isinstance(input_images, list) and bool(input_images), f"{rel_label} input_images must not be empty")
    roles = {image.get("role") for image in input_images if isinstance(input_images, list) and isinstance(image, dict)}
    result.require(roles & STYLE_ANCHOR_ROLES, f"{rel_label} missing style anchor input")
    result.require(roles & TEMPLATE_ROLES, f"{rel_label} missing template reference input")
    result.require(roles & PAGE_FAMILY_ROLES, f"{rel_label} missing page family reference input")
    backend = job.get("backend")
    backend_is_named = isinstance(backend, dict) and not is_empty_value(backend.get("selected_backend"))
    result.require(backend_is_named, f"{rel_label} backend must name selected_backend")
    if isinstance(backend, dict):
        result.require(
            backend.get("mode")
            in {
                "reference_guided_generation",
                "image_edit",
                "hybrid_assets",
                "template_native",
                "editable_reconstruction",
            },
            f"{rel_label} backend mode is invalid",
        )
        result.require(backend.get("requires_image_inputs") is True, f"{rel_label} backend must support image inputs")
    qa_requirements = job.get("qa_requirements")
    result.require(isinstance(qa_requirements, list) and bool(qa_requirements), f"{rel_label} qa_requirements must not be empty")
    if isinstance(qa_requirements, list):
        required_qa = {"exact_content", "text_readability", "style_match"}
        result.require(required_qa <= set(qa_requirements), f"{rel_label} qa_requirements missing core checks")
    if isinstance(input_images, list):
        for image_index, image in enumerate(input_images, start=1):
            if not isinstance(image, dict):
                result.errors.append(f"{rel_label} input image {image_index} must be an object")
                continue
            bundle_path = image.get("bundle_path")
            result.require(isinstance(bundle_path, str) and bundle_path.startswith("input_images/"), f"{rel_label} input image {image_index} invalid bundle_path")
            image_path = safe_runtime_path(bundle_dir, bundle_path, result, f"{rel_label} input image {image_index} bundle_path")
            if image_path:
                result.require(image_path.exists(), f"{rel_label} input image {image_index} bundle file missing: {bundle_path}")
                expected_sha = image.get("sha256")
                if isinstance(expected_sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", expected_sha) and image_path.exists():
                    result.require(sha256_file(image_path) == expected_sha, f"{rel_label} input image {image_index} sha256 mismatch")
            if image.get("required") is True:
                result.require(not is_empty_value(image.get("fidelity_rule")), f"{rel_label} required input image {image_index} missing fidelity_rule")
    if isinstance(visual_constraints, dict):
        locked_chrome = visual_constraints.get("locked_chrome")
        result.require(isinstance(locked_chrome, dict), f"{rel_label} locked_chrome must be an object")
        if isinstance(locked_chrome, dict):
            chrome_mode = locked_chrome.get("mode")
            result.require(chrome_mode in {"none", "post_generation_composite"}, f"{rel_label} locked_chrome mode is invalid")
            if visual_constraints.get("use_navigation_bar") is True:
                result.require(chrome_mode == "post_generation_composite", f"{rel_label} navigation requires locked chrome composite")
            if chrome_mode == "post_generation_composite":
                variant_id = locked_chrome.get("variant_id")
                result.require(isinstance(variant_id, str) and bool(variant_id), f"{rel_label} locked chrome variant_id is required")
                if visual_constraints.get("use_navigation_bar") is True:
                    result.require(not is_empty_value(locked_chrome.get("active_navigation_section")), f"{rel_label} navigation active section is required")
                    result.require(
                        locked_chrome.get("active_navigation_section") == visual_constraints.get("active_navigation_section"),
                        f"{rel_label} active navigation section sources disagree",
                    )
                locked_registry = load_json(
                    order_dir / "04_sample" / "style_kit" / "locked_elements.json",
                    result,
                    "04_sample/style_kit/locked_elements.json",
                )
                registry_variants = locked_registry.get("overlay_variants", []) if isinstance(locked_registry, dict) else []
                matching_variants = [
                    variant
                    for variant in registry_variants
                    if isinstance(variant, dict) and variant.get("variant_id") == variant_id
                ]
                result.require(len(matching_variants) == 1, f"{rel_label} locked chrome variant is not uniquely registered in style kit")
                registered_variant = matching_variants[0] if len(matching_variants) == 1 else None
                if isinstance(registered_variant, dict):
                    result.require(registered_variant.get("slide_no") == expected_slide_no, f"{rel_label} locked chrome variant belongs to another slide")
                    result.require(registered_variant.get("active_navigation_section") == locked_chrome.get("active_navigation_section"), f"{rel_label} locked chrome active section differs from style kit")
                    result.require(registered_variant.get("page_number_text") == locked_chrome.get("page_number_text"), f"{rel_label} locked chrome page number differs from style kit")
                    result.require(registered_variant.get("source_path") == locked_chrome.get("style_variant_path"), f"{rel_label} locked chrome style source path mismatch")
                    result.require(registered_variant.get("sha256") == locked_chrome.get("style_variant_sha256"), f"{rel_label} locked chrome style source sha256 mismatch")
                    result.require(registered_variant.get("sha256") == locked_chrome.get("overlay_sha256"), f"{rel_label} bundled overlay differs from approved style variant")
                    result.require(locked_registry.get("content_safe_box") == locked_chrome.get("content_safe_box"), f"{rel_label} locked chrome safe box differs from style kit")
                overlay_bundle_path = locked_chrome.get("overlay_bundle_path")
                overlay_path = safe_runtime_path(
                    bundle_dir,
                    overlay_bundle_path,
                    result,
                    f"{rel_label} locked chrome overlay",
                )
                expected_sha = locked_chrome.get("overlay_sha256")
                result.require(
                    isinstance(expected_sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", expected_sha),
                    f"{rel_label} locked chrome sha256 is invalid",
                )
                if overlay_path is not None:
                    result.require(overlay_path.exists(), f"{rel_label} locked chrome overlay is missing")
                    if overlay_path.exists() and isinstance(expected_sha, str):
                        result.require(sha256_file(overlay_path) == expected_sha, f"{rel_label} locked chrome sha256 mismatch")
                safe_box = locked_chrome.get("content_safe_box")
                result.require(isinstance(safe_box, dict), f"{rel_label} locked chrome content_safe_box is required")
                matching_inputs = [
                    image
                    for image in input_images or []
                    if isinstance(image, dict)
                    and image.get("bundle_path") == overlay_bundle_path
                    and image.get("role") == "locked_chrome_reference"
                    and image.get("required") is True
                ]
                result.require(bool(matching_inputs), f"{rel_label} locked chrome must be a required input image")
    worker = job.get("worker_policy")
    if isinstance(worker, dict):
        result.require(worker.get("reasoning_level") in ALLOWED_WORKER_REASONING, f"{rel_label} worker reasoning must be medium/high")
        result.require(worker.get("reasoning_level") != "low", f"{rel_label} worker reasoning cannot be low")
        result.require(worker.get("one_slide_only") is True, f"{rel_label} worker must be limited to one slide")
        result.require(isinstance(worker.get("uses_image_generation"), bool), f"{rel_label} uses_image_generation must be boolean")
        result.require(isinstance(worker.get("image_generation_only"), bool), f"{rel_label} image_generation_only must be boolean")
        if output_mode == "image_first":
            result.require(worker.get("uses_image_generation") is True, f"{rel_label} image_first requires image generation")
            result.require(worker.get("image_generation_only") is True, f"{rel_label} image_first worker must return a full-slide image")
        elif output_mode == "hybrid":
            result.require(worker.get("uses_image_generation") is True, f"{rel_label} hybrid requires an image-generated visual layer")
            result.require(worker.get("image_generation_only") is False, f"{rel_label} hybrid also requires editable artifacts")
        else:
            result.require(worker.get("image_generation_only") is False, f"{rel_label} editable modes cannot be image-generation-only")
        result.require(worker.get("must_not_use_text_only_fallback") is True, f"{rel_label} must not use text-only fallback")
        result.require(worker.get("if_required_image_missing") == "block", f"{rel_label} if_required_image_missing must be block")
        high_required_types = {"cover", "data", "timeline", "process", "old_ppt_redesign"}
        if job.get("page_type") in high_required_types or (isinstance(job.get("visual_constraints"), dict) and job["visual_constraints"].get("use_navigation_bar") is True):
            result.require(worker.get("reasoning_level") == "high", f"{rel_label} requires high reasoning")
        if isinstance(input_images, list) and any(isinstance(img, dict) and img.get("role") == "strict_client_asset" for img in input_images):
            result.require(worker.get("reasoning_level") == "high", f"{rel_label} strict_client_asset requires high reasoning")

    contract = load_production_contract(order_dir, result)
    contract_slides = contract.get("slides", []) if isinstance(contract, dict) else []
    matching_contract_slides = [
        slide
        for slide in contract_slides
        if isinstance(slide, dict) and slide.get("slide_no") == expected_slide_no
    ]
    result.require(len(matching_contract_slides) == 1, f"{rel_label} must map to exactly one contract slide")
    if len(matching_contract_slides) == 1:
        result.require(
            output_mode == matching_contract_slides[0].get("output_mode"),
            f"{rel_label} output_mode differs from production contract",
        )


def check_slide_jobs(order_dir: Path, result: ValidationResult) -> None:
    check_sample_accuracy(order_dir, result)
    jobs_payload = load_slide_jobs(order_dir, result)
    if not jobs_payload:
        return
    contract = load_production_contract(order_dir, result)
    page_count = contract.get("deck", {}).get("page_count") if contract else None
    jobs = jobs_payload.get("jobs")
    result.require(isinstance(jobs, list) and bool(jobs), "slide_jobs.json jobs must not be empty")
    if isinstance(page_count, int) and isinstance(jobs, list):
        result.require(len(jobs) == page_count, "slide_jobs.json jobs count must equal deck.page_count")
    if not isinstance(jobs, list):
        return
    seen_job_ids: set[str] = set()
    seen_slide_nos: set[int] = set()
    seen_output_images: set[str] = set()
    for index, job_record in enumerate(jobs, start=1):
        result.require(isinstance(job_record, dict), f"slide_jobs.json record {index} must be an object")
        if not isinstance(job_record, dict):
            continue
        job_id = job_record.get("job_id")
        slide_no = job_record.get("slide_no")
        bundle_dir = job_record.get("bundle_dir")
        job_file = job_record.get("job_file")
        prompt_file = job_record.get("prompt_file")
        input_images_dir = job_record.get("input_images_dir")
        finalization_file = job_record.get("finalization_file")
        output_image = job_record.get("output_image")
        result.require(isinstance(job_id, str) and bool(job_id), f"slide_jobs.json record {index} missing job_id")
        if isinstance(job_id, str):
            result.require(job_id not in seen_job_ids, f"duplicate slide job_id: {job_id}")
            seen_job_ids.add(job_id)
        result.require(isinstance(slide_no, int), f"slide_jobs.json record {index} missing slide_no")
        if isinstance(slide_no, int):
            result.require(slide_no not in seen_slide_nos, f"duplicate slide_no: {slide_no}")
            seen_slide_nos.add(slide_no)
        result.require(isinstance(bundle_dir, str) and bundle_dir.startswith("05_production/slide_jobs/slide_"), f"slide_jobs.json record {index} invalid bundle_dir")
        result.require(isinstance(job_file, str) and job_file.endswith("/job.json"), f"slide_jobs.json record {index} invalid job_file")
        result.require(isinstance(prompt_file, str) and prompt_file.endswith("/prompt.md"), f"slide_jobs.json record {index} invalid prompt_file")
        result.require(isinstance(input_images_dir, str) and input_images_dir.endswith("/input_images"), f"slide_jobs.json record {index} invalid input_images_dir")
        result.require(isinstance(finalization_file, str) and finalization_file.endswith("/finalization.json"), f"slide_jobs.json record {index} invalid finalization_file")
        result.require(isinstance(output_image, str) and output_image.startswith("05_production/origin_image/"), f"slide_jobs.json record {index} invalid output_image")
        if isinstance(output_image, str):
            result.require(output_image not in seen_output_images, f"duplicate canonical output_image: {output_image}")
            seen_output_images.add(output_image)
        if isinstance(slide_no, int):
            expected_prefix = f"05_production/slide_jobs/slide_{slide_no:02d}"
            result.require(bundle_dir == expected_prefix, f"slide_jobs.json record {index} bundle_dir does not match slide_no")
            result.require(output_image == f"05_production/origin_image/slide_{slide_no:02d}.png", f"slide_jobs.json record {index} output_image does not match slide_no")
        prompt_path = safe_runtime_path(order_dir, prompt_file, result, f"slide_jobs.json record {index} prompt_file")
        input_path = safe_runtime_path(order_dir, input_images_dir, result, f"slide_jobs.json record {index} input_images_dir")
        job_path = safe_runtime_path(order_dir, job_file, result, f"slide_jobs.json record {index} job_file")
        bundle_path = safe_runtime_path(order_dir, bundle_dir, result, f"slide_jobs.json record {index} bundle_dir")
        safe_runtime_path(order_dir, finalization_file, result, f"slide_jobs.json record {index} finalization_file")
        safe_runtime_path(order_dir, output_image, result, f"slide_jobs.json record {index} output_image")
        if prompt_path is not None:
            result.require(exists_nonempty(prompt_path), f"slide_jobs.json record {index} missing prompt_file")
        if input_path is not None:
            result.require(input_path.is_dir(), f"slide_jobs.json record {index} missing input_images_dir")
        if isinstance(job_id, str) and isinstance(slide_no, int) and job_path is not None and bundle_path is not None:
            check_slide_job_payload(order_dir, job_path, result, job_id, slide_no, bundle_path)


def check_slide_attempt_history(
    slide: dict[str, Any],
    index: int,
    result: ValidationResult,
    current_attempt: Any,
    max_attempts: Any,
    accepted_attempt: Any,
) -> None:
    attempts = slide.get("attempts")
    result.require(isinstance(attempts, list) and bool(attempts), f"slide_run_state slide {index} attempts must not be empty")
    if not isinstance(attempts, list):
        return

    records = [attempt for attempt in attempts if isinstance(attempt, dict)]
    result.require(len(records) == len(attempts), f"slide_run_state slide {index} attempt records must be objects")
    attempt_numbers = [attempt.get("attempt") for attempt in records]
    result.require(len(attempt_numbers) == len(set(attempt_numbers)), f"slide_run_state slide {index} has duplicate attempts")

    if isinstance(current_attempt, int):
        result.require(current_attempt in attempt_numbers, f"slide_run_state slide {index} current_attempt missing from history")
        result.require(set(attempt_numbers) == set(range(1, current_attempt + 1)), f"slide_run_state slide {index} attempt history must be contiguous")
    if isinstance(max_attempts, int):
        result.require(len(records) <= max_attempts, f"slide_run_state slide {index} has more records than max_attempts")

    for attempt in records:
        attempt_no = attempt.get("attempt")
        result.require(isinstance(attempt_no, int), f"slide_run_state slide {index} attempt number is invalid")
        result.require(not is_empty_value(attempt.get("job_snapshot_file")), f"slide_run_state slide {index} attempt {attempt_no} missing job snapshot")
        if attempt.get("status") == "accepted":
            result.require(not is_empty_value(attempt.get("render_result_file")), f"slide_run_state slide {index} accepted attempt missing render result")
            result.require(not is_empty_value(attempt.get("output_image")), f"slide_run_state slide {index} accepted attempt missing output")
        if attempt.get("status") == "rejected":
            result.require(attempt.get("failure_class") not in {None, "none"}, f"slide_run_state slide {index} rejected attempt missing failure class")
            result.require(not is_empty_value(attempt.get("repair_instructions")), f"slide_run_state slide {index} rejected attempt missing repair instructions")

    accepted = [attempt for attempt in records if attempt.get("attempt") == accepted_attempt]
    result.require(bool(accepted) and accepted[0].get("status") == "accepted", f"slide_run_state slide {index} accepted attempt is not recorded")


def check_slide_run_state(order_dir: Path, result: ValidationResult) -> None:
    run_state = load_json(order_dir / "05_production" / "slide_run_state.json", result, "05_production/slide_run_state.json")
    if not run_state:
        return
    slides = run_state.get("slides")
    result.require(isinstance(slides, list) and bool(slides), "slide_run_state.json slides must not be empty")
    if not isinstance(slides, list):
        return
    jobs_payload = load_slide_jobs(order_dir, result)
    jobs_by_id = {
        job.get("job_id"): job
        for job in (jobs_payload or {}).get("jobs", [])
        if isinstance(job, dict) and isinstance(job.get("job_id"), str)
    }
    for index, slide in enumerate(slides, start=1):
        result.require(isinstance(slide, dict), f"slide_run_state slide {index} must be an object")
        if not isinstance(slide, dict):
            continue
        status = slide.get("status")
        result.require(status == "accepted", f"slide_run_state slide {index} status must be accepted before visual QA")
        result.require(not is_empty_value(slide.get("job_id")), f"slide_run_state slide {index} missing job_id")
        current_attempt = slide.get("current_attempt")
        max_attempts = slide.get("max_attempts")
        accepted_attempt = slide.get("accepted_attempt")
        result.require(isinstance(current_attempt, int) and current_attempt >= 1, f"slide_run_state slide {index} current_attempt is invalid")
        result.require(isinstance(max_attempts, int) and 1 <= max_attempts <= 3, f"slide_run_state slide {index} max_attempts must be 1-3")
        if isinstance(current_attempt, int) and isinstance(max_attempts, int):
            result.require(current_attempt <= max_attempts, f"slide_run_state slide {index} exceeded max_attempts")
        result.require(isinstance(accepted_attempt, int), f"slide_run_state slide {index} accepted_attempt is required")
        check_slide_attempt_history(slide, index, result, current_attempt, max_attempts, accepted_attempt)
        result.require(not slide.get("blockers"), f"slide_run_state slide {index} has blockers")
        result.require(not is_empty_value(slide.get("render_result_file")), f"slide_run_state slide {index} missing render_result_file")
        result.require(not is_empty_value(slide.get("finalization_file")), f"slide_run_state slide {index} missing finalization_file")
        result.require(not is_empty_value(slide.get("selected_source")), f"slide_run_state slide {index} missing selected_source")
        result.require(not is_empty_value(slide.get("final_output_image")), f"slide_run_state slide {index} missing final_output_image")
        result.require(is_nonempty_collection(slide.get("input_images_seen")), f"slide_run_state slide {index} missing input_images_seen")
        job_record = jobs_by_id.get(slide.get("job_id"))
        result.require(isinstance(job_record, dict), f"slide_run_state slide {index} job_id is not in slide_jobs.json")
        if isinstance(job_record, dict):
            result.require(slide.get("render_result_file") == job_record.get("render_result_file"), f"slide_run_state slide {index} render_result_file mismatch")
            result.require(slide.get("finalization_file") == job_record.get("finalization_file"), f"slide_run_state slide {index} finalization_file mismatch")
            result.require(slide.get("final_output_image") == job_record.get("output_image"), f"slide_run_state slide {index} final_output_image mismatch")
            result.require(slide.get("selected_source") == job_record.get("output_image"), f"slide_run_state slide {index} selected_source must be canonical final output")


def check_editable_artifacts(
    order_dir: Path,
    artifacts: Any,
    result: ValidationResult,
    label: str,
    required: bool,
) -> None:
    result.require(isinstance(artifacts, list), f"{label} editable_artifacts must be a list")
    if not isinstance(artifacts, list):
        return
    if required:
        result.require(bool(artifacts), f"{label} requires editable_artifacts for this output mode")
    for index, artifact in enumerate(artifacts, start=1):
        result.require(isinstance(artifact, dict), f"{label} editable artifact {index} must be an object")
        if not isinstance(artifact, dict):
            continue
        path = safe_runtime_path(order_dir, artifact.get("path"), result, f"{label} editable artifact {index} path")
        expected_sha = artifact.get("sha256")
        result.require(
            isinstance(expected_sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", expected_sha),
            f"{label} editable artifact {index} sha256 is invalid",
        )
        if path is not None:
            result.require(path.exists(), f"{label} editable artifact {index} does not exist")
            if path.exists() and isinstance(expected_sha, str):
                result.require(sha256_file(path) == expected_sha, f"{label} editable artifact {index} sha256 mismatch")


def check_render_results(order_dir: Path, result: ValidationResult) -> None:
    jobs_payload = load_slide_jobs(order_dir, result)
    if not jobs_payload:
        return
    jobs = jobs_payload.get("jobs")
    if not isinstance(jobs, list):
        return
    for index, job_record in enumerate(jobs, start=1):
        if not isinstance(job_record, dict):
            continue
        slide_no = job_record.get("slide_no", index)
        job_id = job_record.get("job_id")
        result_file = job_record.get("render_result_file")
        output_image = job_record.get("output_image")
        job_path = safe_runtime_path(order_dir, job_record.get("job_file"), result, f"slide {slide_no} job_file")
        job = load_json(job_path, result, str(job_record.get("job_file"))) if job_path is not None else None
        result.require(isinstance(result_file, str), f"slide {slide_no} missing render_result_file")
        if not isinstance(result_file, str) or not job:
            continue
        render_path = safe_runtime_path(order_dir, result_file, result, f"slide {slide_no} render_result_file")
        if render_path is None:
            continue
        render = load_json(render_path, result, result_file)
        if not render:
            continue
        result.require(render.get("job_id") == job_id, f"{result_file} job_id mismatch")
        result.require(isinstance(render.get("attempt"), int) and 1 <= render["attempt"] <= 3, f"{result_file} attempt is invalid")
        result.require(render.get("slide_no") == slide_no, f"{result_file} slide_no mismatch")
        output_mode = render.get("output_mode")
        result.require(output_mode == job.get("output_mode"), f"{result_file} output_mode differs from slide job")
        check_editable_artifacts(
            order_dir,
            render.get("editable_artifacts", []),
            result,
            result_file,
            output_mode != "image_first",
        )
        result.require(render.get("status") == "success", f"{result_file} status must be success")
        result.require(not render.get("blockers"), f"{result_file} blockers must be empty")
        raw_output = render.get("output_image")
        attempt = render.get("attempt")
        bundle_dir = job_record.get("bundle_dir")
        expected_raw_output = (
            f"{bundle_dir}/attempts/attempt_{attempt:02d}/output.png"
            if isinstance(bundle_dir, str) and isinstance(attempt, int)
            else None
        )
        result.require(raw_output == expected_raw_output, f"{result_file} output_image must stay in its own attempt directory")
        output_path = safe_runtime_path(order_dir, raw_output, result, f"slide {slide_no} raw output_image")
        result.require(output_path is not None and output_path.exists(), f"slide {slide_no} raw output image missing")
        result.require(raw_output != output_image, f"{result_file} must preserve raw output separately from final output")
        result.require(is_nonempty_collection(render.get("input_images_seen")), f"{result_file} input_images_seen must not be empty")
        for fidelity in render.get("asset_fidelity", []):
            if not isinstance(fidelity, dict):
                result.errors.append(f"{result_file} asset_fidelity record must be an object")
                continue
            result.require(fidelity.get("status") in {"pass", "not_applicable"}, f"{result_file} asset fidelity must pass")
        result.require(render.get("style_match") != "fail", f"{result_file} style_match must not fail")
        result.require(render.get("text_readability") == "pass", f"{result_file} text_readability must pass")


def check_finalizations(order_dir: Path, result: ValidationResult) -> None:
    jobs_payload = load_slide_jobs(order_dir, result)
    if not jobs_payload:
        return
    jobs = jobs_payload.get("jobs")
    if not isinstance(jobs, list):
        return
    run_state = load_json(order_dir / "05_production" / "slide_run_state.json", result, "05_production/slide_run_state.json")
    run_slides_by_job = {
        slide.get("job_id"): slide
        for slide in (run_state or {}).get("slides", [])
        if isinstance(slide, dict) and isinstance(slide.get("job_id"), str)
    }
    for index, job_record in enumerate(jobs, start=1):
        if not isinstance(job_record, dict):
            continue
        slide_no = job_record.get("slide_no", index)
        job_id = job_record.get("job_id")
        bundle_dir = job_record.get("bundle_dir")
        job_file = safe_runtime_path(order_dir, job_record.get("job_file"), result, f"slide {slide_no} job_file")
        render_file = safe_runtime_path(order_dir, job_record.get("render_result_file"), result, f"slide {slide_no} render_result_file")
        finalization_path = safe_runtime_path(order_dir, job_record.get("finalization_file"), result, f"slide {slide_no} finalization_file")
        if job_file is None or render_file is None or finalization_path is None:
            continue
        job = load_json(job_file, result, str(job_record.get("job_file")))
        render = load_json(render_file, result, str(job_record.get("render_result_file")))
        finalization = load_json(finalization_path, result, str(job_record.get("finalization_file")))
        if not job or not render or not finalization:
            continue
        result.require(finalization.get("job_id") == job_id, f"slide {slide_no} finalization job_id mismatch")
        result.require(finalization.get("slide_no") == slide_no, f"slide {slide_no} finalization slide_no mismatch")
        output_mode = job.get("output_mode")
        result.require(finalization.get("output_mode") == output_mode, f"slide {slide_no} finalization output_mode mismatch")
        check_editable_artifacts(
            order_dir,
            finalization.get("editable_artifacts", []),
            result,
            f"slide {slide_no} finalization",
            output_mode != "image_first",
        )
        result.require(finalization.get("accepted_attempt") == render.get("attempt"), f"slide {slide_no} finalization attempt mismatch")
        run_slide = run_slides_by_job.get(job_id)
        result.require(isinstance(run_slide, dict), f"slide {slide_no} finalization has no slide_run_state record")
        if isinstance(run_slide, dict):
            result.require(finalization.get("accepted_attempt") == run_slide.get("accepted_attempt"), f"slide {slide_no} finalization does not match accepted attempt")
            accepted_records = [
                attempt
                for attempt in run_slide.get("attempts", [])
                if isinstance(attempt, dict) and attempt.get("attempt") == run_slide.get("accepted_attempt")
            ]
            result.require(len(accepted_records) == 1, f"slide {slide_no} accepted attempt record is not unique")
            if len(accepted_records) == 1:
                result.require(accepted_records[0].get("output_image") == render.get("output_image"), f"slide {slide_no} accepted attempt output differs from render result")
        result.require(finalization.get("status") == "pass", f"slide {slide_no} finalization must pass")
        result.require(finalization.get("raw_output_image") == render.get("output_image"), f"slide {slide_no} finalization raw output mismatch")
        raw_output_path = safe_runtime_path(order_dir, render.get("output_image"), result, f"slide {slide_no} finalized raw output")
        if raw_output_path is not None and raw_output_path.exists():
            result.require(finalization.get("raw_output_sha256") == sha256_file(raw_output_path), f"slide {slide_no} raw output sha256 mismatch")
        final_output = finalization.get("final_output_image")
        result.require(final_output == job_record.get("output_image"), f"slide {slide_no} final output must match slide_jobs.json")
        final_output_path = safe_runtime_path(order_dir, final_output, result, f"slide {slide_no} final output")
        result.require(final_output_path is not None and final_output_path.exists(), f"slide {slide_no} final output image missing")
        if final_output_path is not None and final_output_path.exists():
            result.require(finalization.get("final_output_sha256") == sha256_file(final_output_path), f"slide {slide_no} final output sha256 mismatch")

        locked_chrome = job.get("visual_constraints", {}).get("locked_chrome")
        finalized_chrome = finalization.get("locked_chrome")
        result.require(isinstance(locked_chrome, dict), f"slide {slide_no} job locked_chrome is invalid")
        result.require(isinstance(finalized_chrome, dict), f"slide {slide_no} finalization locked_chrome is invalid")
        if not isinstance(locked_chrome, dict) or not isinstance(finalized_chrome, dict):
            continue
        chrome_mode = locked_chrome.get("mode")
        result.require(finalized_chrome.get("mode") == chrome_mode, f"slide {slide_no} locked chrome mode mismatch")
        if chrome_mode == "post_generation_composite":
            expected_overlay = f"{bundle_dir}/{locked_chrome.get('overlay_bundle_path')}"
            result.require(finalized_chrome.get("variant_id") == locked_chrome.get("variant_id"), f"slide {slide_no} locked chrome variant mismatch")
            result.require(finalized_chrome.get("active_navigation_section") == locked_chrome.get("active_navigation_section"), f"slide {slide_no} active navigation section mismatch")
            result.require(finalized_chrome.get("overlay_path") == expected_overlay, f"slide {slide_no} locked chrome overlay path mismatch")
            result.require(finalized_chrome.get("overlay_sha256") == locked_chrome.get("overlay_sha256"), f"slide {slide_no} locked chrome sha256 mismatch")
            result.require(finalized_chrome.get("applied") is True, f"slide {slide_no} locked chrome was not applied")
            result.require(finalized_chrome.get("pixel_match") is True, f"slide {slide_no} locked chrome pixels do not match")
            result.require(finalized_chrome.get("content_safe_zone_clear") is True, f"slide {slide_no} locked chrome overlaps content safe zone")
        else:
            result.require(finalized_chrome.get("applied") is False, f"slide {slide_no} chrome applied when mode is none")
            result.require(finalized_chrome.get("variant_id") is None, f"slide {slide_no} chrome variant must be null when mode is none")


def check_visual_qa(order_dir: Path, result: ValidationResult) -> None:
    check_slide_jobs(order_dir, result)
    check_slide_run_state(order_dir, result)
    check_render_results(order_dir, result)
    check_finalizations(order_dir, result)
    visual = load_json(order_dir / "05_production" / "visual_qa_result.json", result, "05_production/visual_qa_result.json")
    if not visual:
        return
    result.require(visual.get("status") == "pass", "visual_qa_result.json status must be pass")
    result.require(not visual.get("blockers"), "visual_qa_result.json blockers must be empty")

    asset_fidelity = visual.get("asset_fidelity", {})
    result.require(isinstance(asset_fidelity, dict), "visual_qa_result.json asset_fidelity must be an object")
    if isinstance(asset_fidelity, dict):
        for slide_id, slide_result in asset_fidelity.items():
            required_assets = slide_result.get("required_assets") if isinstance(slide_result, dict) else None
            result.require(isinstance(required_assets, list), f"asset_fidelity {slide_id} required_assets must be a list")
            if not isinstance(required_assets, list):
                continue
            for asset in required_assets:
                if not isinstance(asset, dict):
                    result.errors.append(f"asset_fidelity {slide_id} asset record must be an object")
                    continue
                result.require(asset.get("visible_in_output") is True, f"asset_fidelity {slide_id} asset not visible")
                result.require(asset.get("fidelity_status") == "pass", f"asset_fidelity {slide_id} fidelity_status must be pass")

    jobs_payload = load_slide_jobs(order_dir, result)
    expected_navigation_slides: set[int] = set()
    for job_record in (jobs_payload or {}).get("jobs", []):
        if not isinstance(job_record, dict):
            continue
        job_path = resolve_within(order_dir, job_record.get("job_file"))
        if job_path is None or not job_path.exists():
            continue
        try:
            job = json.loads(job_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if job.get("visual_constraints", {}).get("use_navigation_bar") is True and isinstance(job_record.get("slide_no"), int):
            expected_navigation_slides.add(job_record["slide_no"])

    for report_name, fail_fields in [
        ("style_drift", ["palette_match", "typography_match", "background_match", "layout_family_match"]),
        ("navigation_consistency", ["geometry_match"]),
        ("text_readability", ["status"]),
    ]:
        records = visual.get(report_name, [])
        result.require(isinstance(records, list), f"visual_qa_result.json {report_name} must be a list")
        if not isinstance(records, list):
            continue
        if report_name == "navigation_consistency":
            reported_slides = [record.get("slide_no") for record in records if isinstance(record, dict)]
            result.require(len(reported_slides) == len(set(reported_slides)), "navigation_consistency contains duplicate slide records")
            result.require(set(reported_slides) == expected_navigation_slides, "navigation_consistency must cover every and only navigation slide")
        for record in records:
            if not isinstance(record, dict):
                result.errors.append(f"visual_qa_result.json {report_name} record must be an object")
                continue
            for field in fail_fields:
                value = record.get(field)
                if field == "status":
                    result.require(value == "pass", f"{report_name} slide {record.get('slide_no')} status must be pass")
                elif report_name == "navigation_consistency":
                    result.require(value == "pass", f"navigation slide {record.get('slide_no')} {field} must be pass")
                else:
                    result.require(value != "fail", f"{report_name} slide {record.get('slide_no')} {field} must not fail")
            if report_name == "navigation_consistency":
                result.require(record.get("nav_present") is True, f"navigation slide {record.get('slide_no')} navigation is missing")
                result.require(record.get("active_section_correct") is True, f"navigation slide {record.get('slide_no')} active section is incorrect")
                result.require(record.get("needs_regeneration") is False, f"navigation slide {record.get('slide_no')} needs regeneration")


def qa_status_from_markdown(path: Path) -> str | None:
    if not exists_nonempty(path):
        return None
    content = path.read_text(encoding="utf-8")
    match = re.search(r"Status:\s*(pass|blocked|failed)", content, re.IGNORECASE)
    return match.group(1).lower() if match else None


def check_qa(order_dir: Path, result: ValidationResult) -> None:
    check_visual_qa(order_dir, result)
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


def check_send_manifest(
    order_dir: Path,
    result: ValidationResult,
    path: Path,
    label: str,
    expected_purpose: str,
    expected_action: str,
) -> dict[str, Any] | None:
    payload = load_json(path, result, label)
    if not payload:
        return None
    order_id = order_id_from_state(order_dir, result)
    result.require(payload.get("order_id") == order_id, f"{label} order_id must match state.json")
    result.require(payload.get("purpose") == expected_purpose, f"{label} purpose must be {expected_purpose}")

    message_path = safe_runtime_path(order_dir, payload.get("message_path"), result, f"{label} message_path")
    message_sha = payload.get("message_sha256")
    result.require(
        isinstance(message_sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", message_sha),
        f"{label} message_sha256 is invalid",
    )
    if message_path is not None:
        result.require(exists_nonempty(message_path), f"{label} message_path does not exist")
        if message_path.exists() and isinstance(message_sha, str):
            result.require(sha256_file(message_path) == message_sha, f"{label} message_sha256 mismatch")

    approval_id = payload.get("approval_id")
    contact_id = payload.get("contact_id")
    matches = [
        record
        for record in approved_records(order_dir, result)
        if record.get("approval_id") == approval_id
        and record.get("action_type") == expected_action
        and record.get("contact_id") == contact_id
        and record.get("draft_sha256") == message_sha
    ]
    result.require(bool(matches), f"{label} has no matching {expected_action} approval")
    check_file_manifest(order_dir, result, path, label)
    return payload


def check_sample_delivery(order_dir: Path, result: ValidationResult) -> None:
    check_decision(order_dir, result)
    sample_dir = order_dir / "04_sample"
    result.require(exists_nonempty(sample_dir / "sample_contract.json"), "missing or empty 04_sample/sample_contract.json")
    result.require(exists_nonempty(sample_dir / "sample_qa.md"), "missing or empty 04_sample/sample_qa.md")
    result.require(qa_status_from_markdown(sample_dir / "sample_qa.md") == "pass", "sample_qa.md Status must be pass")
    result.require(exists_nonempty(sample_dir / "sample_delivery_message.md"), "missing or empty 04_sample/sample_delivery_message.md")
    check_send_manifest(
        order_dir,
        result,
        sample_dir / "sample_send_manifest.json",
        "04_sample/sample_send_manifest.json",
        "sample",
        "send_sample",
    )


def check_sample_feedback(order_dir: Path, result: ValidationResult) -> None:
    check_sample_delivery(order_dir, result)
    sample_dir = order_dir / "04_sample"
    receipt = load_json(sample_dir / "sample_send_receipt.json", result, "04_sample/sample_send_receipt.json")
    manifest = load_json(sample_dir / "sample_send_manifest.json", result, "04_sample/sample_send_manifest.json")
    if receipt:
        order_id = order_id_from_state(order_dir, result)
        result.require(receipt.get("order_id") == order_id, "sample send receipt order_id must match state.json")
        if manifest:
            result.require(receipt.get("manifest_id") == manifest.get("manifest_id"), "sample send receipt manifest_id mismatch")
            result.require(receipt.get("message_sha256") == manifest.get("message_sha256"), "sample send receipt message hash mismatch")
        check_file_manifest(order_dir, result, sample_dir / "sample_send_receipt.json", "04_sample/sample_send_receipt.json")
        screenshot = safe_runtime_path(
            order_dir,
            receipt.get("post_send_screenshot"),
            result,
            "04_sample/sample_send_receipt.json post_send_screenshot",
        )
        if screenshot is not None:
            result.require(screenshot.exists(), "sample send receipt post_send_screenshot does not exist")
    check_customer_sample_decision(order_dir, result)


def check_delivery(order_dir: Path, result: ValidationResult) -> None:
    check_qa(order_dir, result)
    delivery_dir = order_dir / "07_delivery"
    result.require(exists_nonempty(delivery_dir / "delivery_message.md"), "missing or empty 07_delivery/delivery_message.md")
    check_send_manifest(
        order_dir,
        result,
        delivery_dir / "final_send_manifest.json",
        "07_delivery/final_send_manifest.json",
        "final_delivery",
        "send_final_delivery",
    )


def check_owner_return_ready(order_dir: Path, result: ValidationResult) -> None:
    check_qa(order_dir, result)
    result.require(execution_mode(order_dir, result) == "owner_direct", "owner return is only valid for owner_direct orders")
    state = load_order_state(order_dir, result)
    if state:
        result.require(state.get("delivery_target") == "owner_codex", "owner return requires delivery_target=owner_codex")
    manifest_path = order_dir / "07_delivery" / "owner_return_manifest.json"
    manifest = load_json(manifest_path, result, "07_delivery/owner_return_manifest.json")
    if not manifest:
        return
    result.require(manifest.get("order_id") == order_id_from_state(order_dir, result), "owner return order_id must match state.json")
    result.require(manifest.get("target") == "owner_codex", "owner return target must be owner_codex")
    for forbidden in ["contact_id", "approval_id", "message_path", "message_sha256"]:
        result.require(forbidden not in manifest, f"owner return manifest must not contain customer-send field: {forbidden}")
    qa_path = safe_runtime_path(order_dir, manifest.get("qa_result_path"), result, "owner return qa_result_path")
    result.require(manifest.get("qa_result_path") == "06_qa/qa_result.json", "owner return must reference 06_qa/qa_result.json")
    if qa_path is not None:
        result.require(qa_path.exists(), "owner return QA result does not exist")
        if qa_path.exists():
            result.require(manifest.get("qa_result_sha256") == sha256_file(qa_path), "owner return QA result hash mismatch")
    check_file_manifest(order_dir, result, manifest_path, "07_delivery/owner_return_manifest.json")


def check_owner_returned(order_dir: Path, result: ValidationResult) -> None:
    check_owner_return_ready(order_dir, result)
    manifest_path = order_dir / "07_delivery" / "owner_return_manifest.json"
    receipt_path = order_dir / "07_delivery" / "owner_return_receipt.json"
    manifest = load_json(manifest_path, result, "07_delivery/owner_return_manifest.json")
    receipt = load_json(receipt_path, result, "07_delivery/owner_return_receipt.json")
    if not manifest or not receipt:
        return
    result.require(receipt.get("order_id") == order_id_from_state(order_dir, result), "owner return receipt order_id mismatch")
    result.require(receipt.get("target") == "owner_codex", "owner return receipt target must be owner_codex")
    result.require(receipt.get("manifest_path") == "07_delivery/owner_return_manifest.json", "owner return receipt manifest path is invalid")
    result.require(receipt.get("manifest_sha256") == sha256_file(manifest_path), "owner return receipt manifest hash mismatch")
    result.require(receipt.get("files") == manifest.get("files"), "owner return receipt files differ from verified manifest")


def check_file_manifest(order_dir: Path, result: ValidationResult, path: Path, label: str) -> None:
    payload = load_json(path, result, label)
    if not payload:
        return
    files = payload.get("files")
    result.require(isinstance(files, list) and bool(files), f"{label} files must not be empty")
    if not isinstance(files, list):
        return
    for index, file_record in enumerate(files, start=1):
        result.require(isinstance(file_record, dict), f"{label} file {index} must be an object")
        if not isinstance(file_record, dict):
            continue
        rel_path = file_record.get("path")
        sha = file_record.get("sha256")
        result.require(isinstance(rel_path, str) and bool(rel_path), f"{label} file {index} missing path")
        result.require(isinstance(sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", sha), f"{label} file {index} invalid sha256")
        file_path = safe_runtime_path(order_dir, rel_path, result, f"{label} file {index} path")
        if file_path is not None:
            result.require(file_path.exists(), f"{label} file {index} path does not exist")
        if file_path is not None and file_path.exists() and isinstance(sha, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", sha):
            result.require(sha256_file(file_path) == sha, f"{label} file {index} sha256 mismatch")


def check_closeout(order_dir: Path, result: ValidationResult) -> None:
    check_delivery(order_dir, result)
    closeout_dir = order_dir / "08_closeout"
    result.require(exists_nonempty(closeout_dir / "order_summary.md"), "missing or empty 08_closeout/order_summary.md")
    result.require(exists_nonempty(closeout_dir / "revision_history.md"), "missing or empty 08_closeout/revision_history.md")
    result.require(exists_nonempty(closeout_dir / "closeout_checklist.md"), "missing or empty 08_closeout/closeout_checklist.md")
    check_file_manifest(order_dir, result, closeout_dir / "final_files_manifest.json", "08_closeout/final_files_manifest.json")
    check_file_manifest(order_dir, result, closeout_dir / "delivery_receipt.json", "08_closeout/delivery_receipt.json")
    payment = load_json(closeout_dir / "payment_status.json", result, "08_closeout/payment_status.json")
    if payment:
        result.require(payment.get("status") in {"unknown", "pending", "partial", "paid", "waived"}, "payment_status.json status is invalid")
    sent_records = load_jsonl(ledger_root(project_root()) / "sent_messages.jsonl", result, "ledgers/sent_messages.jsonl", False)
    result.require(bool(sent_records), "closeout requires sent message ledger record")


GATES: dict[str, Callable[[Path, ValidationResult], None]] = {
    "base": check_base,
    "chat_capture": check_chat_capture,
    "briefing": check_briefing,
    "contract_accuracy": check_contract_accuracy,
    "decision": check_decision,
    "production": check_production,
    "sample_accuracy": check_sample_accuracy,
    "sample_delivery": check_sample_delivery,
    "sample_feedback": check_sample_feedback,
    "slide_jobs": check_slide_jobs,
    "visual_qa": check_visual_qa,
    "qa": check_qa,
    "owner_return_ready": check_owner_return_ready,
    "owner_returned": check_owner_returned,
    "delivery": check_delivery,
    "closeout": check_closeout,
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
