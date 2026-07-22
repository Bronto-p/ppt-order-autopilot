#!/usr/bin/env python3
"""Register Codex/workspace files as a complete owner-direct intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bootstrap_runtime import bootstrap_runtime, ledger_root


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return payload


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def append_once(path: Path, payload: dict[str, Any], identity: tuple[str, ...]) -> None:
    for existing in read_jsonl(path):
        if all(existing.get(key) == payload.get(key) for key in identity):
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def copy_verified(source: Path, target: Path, expected_sha: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and sha256_file(target) == expected_sha:
        return
    temp = target.with_name(f".{target.name}.tmp")
    shutil.copyfile(source, temp)
    if sha256_file(temp) != expected_sha:
        temp.unlink(missing_ok=True)
        raise SystemExit(f"hash mismatch while copying {source}")
    temp.replace(target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a complete owner-direct file intake.")
    parser.add_argument("order_dir")
    parser.add_argument("--source-type", choices=["codex_attachment", "workspace_file"], required=True)
    parser.add_argument("--prompt-file", required=True, help="UTF-8 file containing the exact owner prompt.")
    parser.add_argument("--file", action="append", dest="files", required=True, help="Source file; repeat for multiple files.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    bootstrap_runtime(root)
    ledgers = ledger_root(root)
    order_dir = Path(args.order_dir).resolve()
    try:
        order_dir.relative_to((root / "orders").resolve())
    except ValueError as exc:
        raise SystemExit("order_dir must stay under the plugin orders directory") from exc

    state_path = order_dir / "00_state" / "state.json"
    state = read_json(state_path)
    if state.get("execution_mode") != "owner_direct":
        raise SystemExit("register_direct_intake requires execution_mode=owner_direct")
    if state.get("state") != "IDLE":
        raise SystemExit("direct intake may only register while the order is IDLE")
    if state.get("intake_source") not in {None, args.source_type}:
        raise SystemExit("state intake_source conflicts with --source-type")

    prompt_path = Path(args.prompt_file).resolve()
    prompt = prompt_path.read_text(encoding="utf-8")
    if not prompt.strip():
        raise SystemExit("owner prompt must not be empty")
    source_files = sorted({Path(value).resolve() for value in args.files}, key=lambda path: path.name)
    for source in source_files:
        if not source.is_file():
            raise SystemExit(f"source file is not readable: {source}")

    source_records = [
        {
            "name": source.name,
            "sha256": sha256_file(source),
            "source_path": str(source),
        }
        for source in source_files
    ]
    digest_files = [
        {
            "name": item["name"],
            "sha256": item["sha256"],
            **({"source_path": item["source_path"]} if args.source_type == "workspace_file" else {}),
        }
        for item in source_records
    ]
    digest_payload = {
        "prompt": prompt,
        "source_type": args.source_type,
        "files": digest_files,
    }
    digest_bytes = json.dumps(digest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = sha256_bytes(digest_bytes)
    digest_hex = digest.removeprefix("sha256:")
    inquiry_id = f"direct_{digest_hex[:16]}"
    message_id = f"owner_prompt_{digest_hex[:12]}"
    approval_id = f"owner_instruction_{digest_hex[:16]}"
    now = datetime.now(timezone.utc).isoformat()
    inbox_dir = root / "inbox" / inquiry_id
    atomic_write(inbox_dir / "source_prompt.txt", prompt)

    destination_folder = "from_codex" if args.source_type == "codex_attachment" else "from_workspace"
    attachment_records: list[dict[str, Any]] = []
    source_attachment_paths: list[str] = []
    for source, source_record in zip(source_files, source_records, strict=True):
        inbox_target = inbox_dir / "downloads" / source.name
        order_target = order_dir / "02_attachments_raw" / destination_folder / source.name
        copy_verified(source, inbox_target, source_record["sha256"])
        copy_verified(source, order_target, source_record["sha256"])
        relative_order_path = order_target.relative_to(order_dir).as_posix()
        attachment_records.append(
            {
                "attachment_id": f"direct_att_{source_record['sha256'].removeprefix('sha256:')[:12]}",
                "name": source.name,
                "original_filename": source.name,
                "saved_path": relative_order_path,
                "original_path": str(source),
                "source_message_id": message_id,
                "source_message_time": now,
                "source_sender": "owner",
                "file_type": "client_content",
                "sha256": source_record["sha256"],
                "download_status": "success",
                "source_type": args.source_type,
            }
        )
        source_attachment_paths.append(relative_order_path)

    atomic_write(
        order_dir / "01_chat" / "message_index.jsonl",
        json.dumps(
            {
                "message_id": message_id,
                "screen_ids": [],
                "sender": "owner",
                "sent_at": now,
                "text": prompt,
                "attachments": [record["attachment_id"] for record in attachment_records],
                "ocr_confidence": "high",
                "source_type": args.source_type,
            },
            ensure_ascii=False,
        )
        + "\n",
    )
    atomic_write(
        order_dir / "02_attachments_raw" / "attachment_index.jsonl",
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in attachment_records),
    )
    coverage = {
        "source_type": args.source_type,
        "status": "success",
        "screens_captured": 0,
        "top_anchor": None,
        "bottom_anchor": None,
        "adjacent_overlap_checks": {"passed": 0, "total": 0, "failed_screen_pairs": []},
        "attachments_found": len(attachment_records),
        "attachments_downloaded": len(attachment_records),
        "attachments_failed": 0,
        "source_attachment_paths": source_attachment_paths,
        "suspected_conflicts": 0,
        "blocking_issues": [],
    }
    write_json(order_dir / "01_chat" / "coverage_result.json", coverage)
    atomic_write(
        order_dir / "01_chat" / "chat_coverage_report.md",
        "# Direct file coverage\n\n"
        f"- Source: {args.source_type}\n"
        f"- Prompt message: {message_id}\n"
        f"- Files verified: {len(attachment_records)}\n"
        "- Screenshots: not applicable\n",
    )
    atomic_write(order_dir / "01_chat" / "chat_transcript.md", f"# Owner instruction\n\n{prompt}\n")
    atomic_write(order_dir / "02_attachments_raw" / "failed_downloads.md", "# Failed downloads\n\nNone.\n")

    order_id = state.get("order_id")
    inquiry_state = {
        "state_version": 1,
        "inquiry_id": inquiry_id,
        "source_type": args.source_type,
        "contact_id": None,
        "state": "PROMOTED",
        "ask_message_hash": None,
        "source_digest": digest,
        "source_message_id": message_id,
        "source_prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "source_prompt_path": (inbox_dir / "source_prompt.txt").relative_to(root).as_posix(),
        "source_attachment_hashes": [{"name": item["name"], "sha256": item["sha256"]} for item in source_records],
        "promotion_intent": {"order_id": order_id, "title": order_dir.name, "status": "recorded"},
        "source_attachment_paths": [
            (inbox_dir / "downloads" / item["name"]).relative_to(root).as_posix() for item in source_records
        ],
        "sent_message_ledger_id": None,
        "sent_at": None,
        "completed_reply_checks_minutes": [],
        "next_reply_check_at": None,
        "reply_detected_at": None,
        "promoted_order_ids": [order_id],
        "updated_at": now,
        "blocked_reason": None,
    }
    write_json(inbox_dir / "inquiry_state.json", inquiry_state)

    approval = {
        "approval_id": approval_id,
        "order_id": order_id,
        "action_type": "owner_direct_instruction",
        "status": "approved",
        "approved_by": "owner",
        "source_message_id": message_id,
        "prompt_sha256": inquiry_state["source_prompt_sha256"],
        "scope": "internal_production_and_owner_codex_return",
        "timestamp": now,
    }
    append_once(order_dir / "00_state" / "approvals.jsonl", approval, ("approval_id", "order_id"))
    append_once(ledgers / "approvals.jsonl", approval, ("approval_id", "order_id"))
    inquiry_event = {
        "event": "promoted",
        "inquiry_id": inquiry_id,
        "source_type": args.source_type,
        "source_digest": digest,
        "source_message_id": message_id,
        "order_id": order_id,
        "order_path": order_dir.relative_to(root).as_posix(),
        "timestamp": now,
    }
    append_once(ledgers / "inquiries.jsonl", inquiry_event, ("event", "inquiry_id", "order_id"))

    automation_path = ledgers / "automation_state.json"
    automation = read_json(automation_path)
    active_order_id = automation.get("active_order_id")
    runnable = active_order_id in {None, order_id}
    if runnable:
        automation.update(
            {
                "active_inquiry_id": inquiry_id,
                "active_order_id": order_id,
                "state": "ORDER_ACTIVE",
                "updated_at": now,
                "blocked_reason": None,
            }
        )
    else:
        pending = [value for value in automation.get("pending_order_ids", []) if isinstance(value, str)]
        if order_id not in pending:
            pending.append(order_id)
        automation.update({"pending_order_ids": pending, "updated_at": now})
    write_json(automation_path, automation)
    state.update({"intake_source": args.source_type, "updated_at": now})
    write_json(state_path, state)
    print(
        json.dumps(
            {
                "status": "registered" if runnable else "queued",
                "inquiry_id": inquiry_id,
                "order_id": order_id,
                "approval_id": approval_id,
                "runnable": runnable,
                "next": (
                    f"python3 tools/autopilot.py commit {order_dir} --to DIRECT_INTAKE_STAGED"
                    if runnable
                    else f"wait until active_order_id={active_order_id} yields the global lock"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
