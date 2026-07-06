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
ALLOWED_WORKER_REASONING = {"medium", "high"}
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


def rel_path_exists(order_dir: Path, rel_path: Any) -> bool:
    return isinstance(rel_path, str) and (order_dir / rel_path).exists()


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
            result.require(str(approval_id) in approval_ids(order_dir, result), f"production approval_id not approved: {approval_id}")
    return normalized


def check_production(order_dir: Path, result: ValidationResult) -> None:
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


def slide_has_role(slide: dict[str, Any], roles: set[str]) -> bool:
    return any(isinstance(image, dict) and image.get("role") in roles for image in slide.get("input_images", []))


def slide_input_paths(slide: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for image in slide.get("input_images", []):
        if isinstance(image, dict) and isinstance(image.get("path"), str):
            paths.add(image["path"])
    return paths


def check_exact_content(label: str, exact_content: Any, result: ValidationResult) -> None:
    result.require(isinstance(exact_content, dict), f"{label} exact_content must be an object")
    if not isinstance(exact_content, dict):
        return
    result.require(has_deep_content(exact_content), f"{label} exact_content is empty")
    result.require(set(exact_content.keys()) - {"topic", "purpose"}, f"{label} exact_content cannot only contain topic/purpose")


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

    method = contract.get("production_method")
    result.require(isinstance(method, dict), "production_contract.production_method must be an object")
    if isinstance(method, dict):
        result.require(method.get("method") == "image_model_full_slide_only", "production method must be image_model_full_slide_only")
        result.require(method.get("parent_may_generate_slides") is False, "parent_may_generate_slides must be false")
        result.require(method.get("subagents_required") is True, "subagents_required must be true")
        result.require(method.get("default_worker_reasoning_level") in ALLOWED_WORKER_REASONING, "default worker reasoning must be medium/high")

    style_system = contract.get("style_system")
    result.require(isinstance(style_system, dict), "production_contract.style_system must be an object")
    if isinstance(style_system, dict):
        result.require(bool(path_list(style_system.get("style_anchor_paths"))), "style_system.style_anchor_paths must not be empty")
        for key in ["template_master_path", "style_spec_path", "locked_elements_path"]:
            result.require(not is_empty_value(style_system.get(key)), f"style_system.{key} is required")
        result.require(isinstance(style_system.get("page_family_refs"), dict) and bool(style_system.get("page_family_refs")), "style_system.page_family_refs must not be empty")

    asset_registry = contract.get("asset_registry")
    result.require(isinstance(asset_registry, list), "production_contract.asset_registry must be a list")
    registered_paths: set[str] = set()
    if isinstance(asset_registry, list):
        for index, asset in enumerate(asset_registry, start=1):
            result.require(isinstance(asset, dict), f"asset_registry record {index} must be an object")
            if not isinstance(asset, dict):
                continue
            for key in ["asset_id", "path", "type", "allowed_use", "fidelity_rule"]:
                result.require(not is_empty_value(asset.get(key)), f"asset_registry record {index} missing {key}")
            if isinstance(asset.get("path"), str):
                registered_paths.add(asset["path"])

    asset_allowlist = set(path_list(contract.get("asset_allowlist", [])))
    forbidden_assets = set(path_list(contract.get("forbidden_assets", [])))
    result.require(asset_allowlist, "production_contract.asset_allowlist must not be empty")

    slides = contract.get("slides")
    result.require(isinstance(slides, list), "production_contract.slides must be a list")
    if not isinstance(slides, list):
        return
    if isinstance(page_count, int):
        result.require(len(slides) == page_count, "production_contract.slides count must equal deck.page_count")

    seen_slide_numbers: set[int] = set()
    all_input_paths: set[str] = set()
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
        for key in ["title", "page_type", "section"]:
            result.require(not is_empty_value(slide.get(key)), f"{label} missing {key}")
        check_exact_content(label, slide.get("exact_content"), result)
        result.require(is_nonempty_collection(slide.get("content_evidence")), f"{label} content_evidence must not be empty")
        input_images = slide.get("input_images")
        result.require(isinstance(input_images, list) and bool(input_images), f"{label} input_images must not be empty")
        if isinstance(input_images, list):
            for image_index, image in enumerate(input_images, start=1):
                result.require(isinstance(image, dict), f"{label} input image {image_index} must be an object")
                if not isinstance(image, dict):
                    continue
                for key in ["path", "role", "fidelity_rule", "required"]:
                    result.require(key in image and not is_empty_value(image.get(key)), f"{label} input image {image_index} missing {key}")
                if isinstance(image.get("path"), str):
                    all_input_paths.add(image["path"])
                if image.get("required") is True:
                    result.require(not is_empty_value(image.get("fidelity_rule")), f"{label} required image {image_index} missing fidelity_rule")
        result.require(slide_has_role(slide, STYLE_ANCHOR_ROLES), f"{label} missing approved sample/style anchor input image")
        result.require(slide_has_role(slide, TEMPLATE_ROLES), f"{label} missing template reference input image")
        result.require(slide_has_role(slide, PAGE_FAMILY_ROLES), f"{label} missing page family reference input image")
        layout = slide.get("layout_constraints", {})
        if isinstance(layout, dict) and layout.get("use_navigation_bar") is True:
            result.require(slide_has_role(slide, NAVIGATION_ROLES), f"{label} uses navigation but missing navigation reference")
        worker = slide.get("worker")
        result.require(isinstance(worker, dict), f"{label} worker must be an object")
        if isinstance(worker, dict):
            result.require(worker.get("reasoning_level") in ALLOWED_WORKER_REASONING, f"{label} worker reasoning_level must be medium/high")
            result.require(worker.get("reasoning_level") != "low", f"{label} worker reasoning_level cannot be low")
            result.require(not is_empty_value(worker.get("job_file")), f"{label} worker.job_file is required")
        result.require(is_nonempty_collection(slide.get("qa_requirements")), f"{label} qa_requirements must not be empty")

    result.require(all_input_paths <= asset_allowlist, "all slide input_images paths must be in asset_allowlist")
    result.require(not (all_input_paths & forbidden_assets), "forbidden_assets must not be referenced by slides")
    strict_input_paths = {path for path in all_input_paths if path in registered_paths}
    result.require(strict_input_paths <= asset_allowlist, "registered input assets must be allowlisted")

    coverage = contract.get("coverage_matrix")
    result.require(isinstance(coverage, list) and bool(coverage), "coverage_matrix must not be empty")
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


def check_sample_accuracy(order_dir: Path, result: ValidationResult) -> None:
    check_contract_accuracy(order_dir, result)
    sample_dir = order_dir / "04_sample"
    style_master = sample_dir / "style_master"
    result.require(exists_nonempty(sample_dir / "sample_contract.json") or not is_sample_required(order_dir, result), "sample_required=true requires 04_sample/sample_contract.json")
    approved = load_json(sample_dir / "approved_sample_reference.json", result, "04_sample/approved_sample_reference.json")
    if approved:
        result.require(is_nonempty_collection(approved.get("approved_samples")), "approved_sample_reference.json approved_samples must not be empty")
        style_system = approved.get("style_system")
        result.require(isinstance(style_system, dict), "approved_sample_reference.json style_system must be an object")
    for rel_path in [
        "style_anchor.png",
        "template_master.png",
        "style_spec.json",
        "locked_elements.json",
    ]:
        result.require((style_master / rel_path).exists(), f"missing style master artifact: 04_sample/style_master/{rel_path}")
    load_json(style_master / "style_spec.json", result, "04_sample/style_master/style_spec.json")
    load_json(style_master / "locked_elements.json", result, "04_sample/style_master/locked_elements.json")


def load_slide_jobs(order_dir: Path, result: ValidationResult) -> dict[str, Any] | None:
    return load_json(order_dir / "05_production" / "slide_jobs.json", result, "05_production/slide_jobs.json")


def check_slide_job_payload(order_dir: Path, job_path: Path, result: ValidationResult, expected_slide_no: int) -> None:
    rel_label = str(job_path.relative_to(order_dir))
    job = load_json(job_path, result, rel_label)
    if not job:
        return
    result.require(job.get("slide_no") == expected_slide_no, f"{rel_label} slide_no does not match slide_jobs.json")
    check_exact_content(rel_label, job.get("exact_content"), result)
    for key in ["deck_context", "local_context", "visual_constraints", "backend", "worker_policy"]:
        result.require(isinstance(job.get(key), dict) and bool(job.get(key)), f"{rel_label} {key} must be a non-empty object")
    input_images = job.get("input_images")
    result.require(isinstance(input_images, list) and bool(input_images), f"{rel_label} input_images must not be empty")
    roles = {image.get("role") for image in input_images if isinstance(image, dict)}
    result.require(roles & STYLE_ANCHOR_ROLES, f"{rel_label} missing style anchor input")
    result.require(roles & TEMPLATE_ROLES, f"{rel_label} missing template reference input")
    result.require(roles & PAGE_FAMILY_ROLES, f"{rel_label} missing page family reference input")
    if isinstance(input_images, list):
        for image_index, image in enumerate(input_images, start=1):
            if not isinstance(image, dict):
                result.errors.append(f"{rel_label} input image {image_index} must be an object")
                continue
            if image.get("required") is True:
                result.require(not is_empty_value(image.get("fidelity_rule")), f"{rel_label} required input image {image_index} missing fidelity_rule")
    backend = job.get("backend")
    if isinstance(backend, dict):
        result.require(backend.get("requires_image_inputs") is True, f"{rel_label} backend.requires_image_inputs must be true")
    worker = job.get("worker_policy")
    if isinstance(worker, dict):
        result.require(worker.get("reasoning_level") in ALLOWED_WORKER_REASONING, f"{rel_label} worker reasoning must be medium/high")
        result.require(worker.get("reasoning_level") != "low", f"{rel_label} worker reasoning cannot be low")
        result.require(worker.get("must_return_blocker_if_image_not_visible") is True, f"{rel_label} must return blocker if image not visible")
        result.require(worker.get("must_not_use_text_only_fallback") is True, f"{rel_label} must not use text-only fallback")


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
    for index, job_record in enumerate(jobs, start=1):
        result.require(isinstance(job_record, dict), f"slide_jobs.json record {index} must be an object")
        if not isinstance(job_record, dict):
            continue
        slide_no = job_record.get("slide_no")
        job_file = job_record.get("job_file")
        output_image = job_record.get("output_image")
        result.require(isinstance(slide_no, int), f"slide_jobs.json record {index} missing slide_no")
        result.require(isinstance(job_file, str) and job_file.startswith("05_production/prompts/"), f"slide_jobs.json record {index} invalid job_file")
        result.require(isinstance(output_image, str) and output_image.startswith("05_production/origin_image/"), f"slide_jobs.json record {index} invalid output_image")
        if isinstance(slide_no, int) and isinstance(job_file, str):
            check_slide_job_payload(order_dir, order_dir / job_file, result, slide_no)


def check_slide_run_state(order_dir: Path, result: ValidationResult) -> None:
    run_state = load_json(order_dir / "05_production" / "slide_run_state.json", result, "05_production/slide_run_state.json")
    if not run_state:
        return
    slides = run_state.get("slides")
    result.require(isinstance(slides, list) and bool(slides), "slide_run_state.json slides must not be empty")
    if not isinstance(slides, list):
        return
    for index, slide in enumerate(slides, start=1):
        result.require(isinstance(slide, dict), f"slide_run_state slide {index} must be an object")
        if not isinstance(slide, dict):
            continue
        status = slide.get("status")
        result.require(status in {"recorded", "accepted"}, f"slide_run_state slide {index} status must be recorded/accepted")
        result.require(not slide.get("blockers"), f"slide_run_state slide {index} has blockers")
        result.require(not is_empty_value(slide.get("selected_source")), f"slide_run_state slide {index} missing selected_source")
        result.require(is_nonempty_collection(slide.get("input_images_seen")), f"slide_run_state slide {index} missing input_images_seen")


def check_visual_qa(order_dir: Path, result: ValidationResult) -> None:
    check_slide_jobs(order_dir, result)
    check_slide_run_state(order_dir, result)
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

    for report_name, fail_fields in [
        ("style_drift", ["palette_match", "typography_match", "background_match", "layout_family_match"]),
        ("navigation_consistency", ["geometry_match"]),
        ("text_readability", ["status"]),
    ]:
        records = visual.get(report_name, [])
        result.require(isinstance(records, list), f"visual_qa_result.json {report_name} must be a list")
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                result.errors.append(f"visual_qa_result.json {report_name} record must be an object")
                continue
            for field in fail_fields:
                value = record.get(field)
                if field == "status":
                    result.require(value == "pass", f"{report_name} slide {record.get('slide_no')} status must be pass")
                else:
                    result.require(value != "fail", f"{report_name} slide {record.get('slide_no')} {field} must not fail")
            if report_name == "navigation_consistency":
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


def check_delivery(order_dir: Path, result: ValidationResult) -> None:
    check_qa(order_dir, result)
    result.require(exists_nonempty(order_dir / "07_delivery" / "delivery_message.md"), "missing or empty 07_delivery/delivery_message.md")
    result.require(approval_ids(order_dir, result), "missing approved approval record before delivery")


GATES: dict[str, Callable[[Path, ValidationResult], None]] = {
    "base": check_base,
    "chat_capture": check_chat_capture,
    "briefing": check_briefing,
    "contract_accuracy": check_contract_accuracy,
    "decision": check_decision,
    "production": check_production,
    "sample_accuracy": check_sample_accuracy,
    "slide_jobs": check_slide_jobs,
    "visual_qa": check_visual_qa,
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
