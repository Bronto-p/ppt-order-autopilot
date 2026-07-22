#!/usr/bin/env python3
"""Guard PPT Order Autopilot state transitions and owner returns.

The AI remains the orchestrator. This tool only makes the durable protocol
explicit: inspect the current step, validate a completed step, and verify an
owner-facing return before the Agent may claim completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_order import GATES, ValidationResult, sha256_file


OWNER_ONLY_STATES = {"OWNER_RETURN_READY", "OWNER_RETURNED"}
OWNER_DIRECT_FORBIDDEN_STATES = {
    "SCHEDULED_ASK",
    "ASK_SENT",
    "WAITING_REPLY_2M",
    "WAITING_REPLY_5M",
    "WAITING_REPLY_10M",
    "WAITING_REPLY_30M",
    "WAITING_REPLY_1H",
    "WAITING_REPLY_2H",
    "NO_REPLY_STOPPED",
    "REPLY_DETECTED",
    "OPENING_CHAT_RECORD",
    "CAPTURING_CHAT_FROM_TOP",
    "CAPTURE_GAP_DETECTED",
    "SAVING_ATTACHMENTS",
    "SAMPLE_REQUIRED",
    "SAMPLE_PRODUCTION",
    "SAMPLE_QA",
    "WAITING_OWNER_SAMPLE_SEND_CONFIRMATION",
    "SAMPLE_SENT",
    "WAITING_CLIENT_SAMPLE_FEEDBACK",
    "SAMPLE_FEEDBACK_AMBIGUOUS",
    "SAMPLE_REVISION_REQUESTED",
    "SAMPLE_APPROVED",
    "DELIVERY_READY",
    "WAITING_OWNER_DELIVERY_CONFIRMATION",
    "DELIVERY_SENT",
    "WAITING_CLIENT_FEEDBACK",
    "CLIENT_ACCEPTED",
    "ORDER_CLOSED",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def resolve_order_dir(value: str) -> Path:
    path = Path(value).resolve()
    root = project_root().resolve()
    try:
        path.relative_to(root / "orders")
    except ValueError as exc:
        raise SystemExit(f"order_dir must stay under {root / 'orders'}") from exc
    if not path.is_dir():
        raise SystemExit(f"order_dir does not exist: {path}")
    return path


def state_machine() -> dict[str, Any]:
    return read_json(project_root() / "configs" / "state_machine.json")


def state_path(order_dir: Path) -> Path:
    return order_dir / "00_state" / "state.json"


def validate_gate(order_dir: Path, gate: str) -> None:
    validator = GATES.get(gate)
    if validator is None:
        raise SystemExit(f"unknown validation gate: {gate}")
    result = ValidationResult()
    validator(order_dir, result)
    if result.warnings:
        for warning in result.warnings:
            print(f"WARN: {warning}")
    if result.errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in result.errors))


def validate_required_artifacts(order_dir: Path, definition: dict[str, Any], state_name: str) -> None:
    missing: list[str] = []
    for value in definition.get("required_artifacts", []):
        if not isinstance(value, str) or value.startswith("ledgers/"):
            continue
        candidate = (order_dir / value).resolve()
        try:
            candidate.relative_to(order_dir.resolve())
        except ValueError:
            raise SystemExit(f"state artifact escapes order directory: {value}")
        if not candidate.exists():
            missing.append(value)
    if missing:
        raise SystemExit(f"{state_name} is missing required artifacts: {', '.join(missing)}")


def filtered_next_states(mode: str, allowed: list[Any]) -> list[str]:
    states = [value for value in allowed if isinstance(value, str)]
    if mode == "owner_direct":
        return [value for value in states if value not in OWNER_DIRECT_FORBIDDEN_STATES]
    return [value for value in states if value not in OWNER_ONLY_STATES]


def next_step(order_dir: Path) -> None:
    state = read_json(state_path(order_dir))
    machine = state_machine()
    current = state.get("state")
    definition = machine.get("states", {}).get(current)
    if not isinstance(definition, dict):
        raise SystemExit(f"state is not defined: {current}")
    gate = definition.get("validation_gate", state.get("current_gate", "base"))
    if isinstance(gate, str):
        validate_gate(order_dir, gate)
    validate_required_artifacts(order_dir, definition, str(current))
    mode = state.get("execution_mode", "customer_order")
    allowed = filtered_next_states(mode, definition.get("allowed_next", []))
    payload = {
        "order_id": state.get("order_id"),
        "execution_mode": mode,
        "intake_source": state.get("intake_source"),
        "delivery_target": state.get("delivery_target"),
        "state": current,
        "validated_gate": gate,
        "required_skill": definition.get("required_skill"),
        "allowed_next": allowed,
        "requires_owner_approval": definition.get("requires_owner_approval", False),
        "completion_rule": (
            "Run `python3 tools/autopilot.py finish <order_dir> --target owner` and cite its receipt_id."
            if mode == "owner_direct"
            else "Customer send requires an approved immutable send manifest and receipt."
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def commit(order_dir: Path, target: str, actor: str) -> None:
    path = state_path(order_dir)
    state = read_json(path)
    machine = state_machine()
    definitions = machine.get("states", {})
    current = state.get("state")
    current_definition = definitions.get(current)
    target_definition = definitions.get(target)
    if not isinstance(current_definition, dict) or not isinstance(target_definition, dict):
        raise SystemExit(f"undefined transition: {current} -> {target}")
    allowed = filtered_next_states(state.get("execution_mode", "customer_order"), current_definition.get("allowed_next", []))
    if target not in allowed:
        raise SystemExit(f"transition not allowed for this execution profile: {current} -> {target}")
    gate = target_definition.get("validation_gate", "base")
    if not isinstance(gate, str):
        gate = "base"
    validate_gate(order_dir, gate)
    validate_required_artifacts(order_dir, target_definition, target)

    now = datetime.now(timezone.utc).isoformat()
    updated = dict(state)
    updated.update(
        {
            "previous_state": current,
            "state": target,
            "current_gate": gate,
            "last_action": f"commit:{target}",
            "next_action": target_definition.get("required_skill", "run_autopilot_next"),
            "last_validated_at": now,
            "updated_at": now,
            "requires_owner_approval": target_definition.get("requires_owner_approval", False),
        }
    )
    atomic_write_json(path, updated)
    append_jsonl(
        order_dir / "00_state" / "events.jsonl",
        {
            "event": "state_committed",
            "order_id": state.get("order_id"),
            "from_state": current,
            "to_state": target,
            "validation_gate": gate,
            "actor": actor,
            "timestamp": now,
        },
    )
    print(json.dumps({"status": "committed", "from": current, "to": target, "gate": gate}, ensure_ascii=False))


def finish_owner_return(order_dir: Path) -> None:
    state = read_json(state_path(order_dir))
    if state.get("execution_mode") != "owner_direct":
        raise SystemExit("--target owner is only valid for owner_direct orders")
    if state.get("state") != "OWNER_RETURN_READY":
        raise SystemExit("owner return can finish only from OWNER_RETURN_READY")
    validate_gate(order_dir, "owner_return_ready")

    manifest_path = order_dir / "07_delivery" / "owner_return_manifest.json"
    manifest = read_json(manifest_path)
    manifest_sha = sha256_file(manifest_path)
    receipt_id = "owner_return_" + hashlib.sha256(manifest_sha.encode("utf-8")).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()
    receipt = {
        "receipt_id": receipt_id,
        "order_id": state.get("order_id"),
        "target": "owner_codex",
        "manifest_path": "07_delivery/owner_return_manifest.json",
        "manifest_sha256": manifest_sha,
        "files": manifest.get("files", []),
        "verified_at": now,
    }
    atomic_write_json(order_dir / "07_delivery" / "owner_return_receipt.json", receipt)
    validate_gate(order_dir, "owner_returned")
    commit(order_dir, "OWNER_RETURNED", "autopilot.finish")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect, commit, or finish a PPT Order Autopilot run.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    next_parser = subparsers.add_parser("next", help="Validate current state and print the next legal actions.")
    next_parser.add_argument("order_dir")

    commit_parser = subparsers.add_parser("commit", help="Validate artifacts and atomically commit a state transition.")
    commit_parser.add_argument("order_dir")
    commit_parser.add_argument("--to", required=True, dest="target")
    commit_parser.add_argument("--actor", default="codex-agent")

    finish_parser = subparsers.add_parser("finish", help="Verify a completed owner return and issue its receipt.")
    finish_parser.add_argument("order_dir")
    finish_parser.add_argument("--target", choices=["owner"], required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    order_dir = resolve_order_dir(args.order_dir)
    if args.command == "next":
        next_step(order_dir)
    elif args.command == "commit":
        commit(order_dir, args.target, args.actor)
    else:
        finish_owner_return(order_dir)


if __name__ == "__main__":
    main()
