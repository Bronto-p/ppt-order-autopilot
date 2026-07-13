#!/usr/bin/env python3
"""Initialize global runtime state and append-only ledgers without overwriting data."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


JSONL_LEDGER_FILES = [
    "inquiries.jsonl",
    "orders.jsonl",
    "sent_messages.jsonl",
    "ui_actions.jsonl",
    "approvals.jsonl",
]


def bootstrap_runtime(project_root: Path) -> Path:
    project_root = project_root.resolve()
    ledgers_root = project_root / "ledgers"
    ledgers_root.mkdir(parents=True, exist_ok=True)
    for name in JSONL_LEDGER_FILES:
        (ledgers_root / name).touch(exist_ok=True)

    state_path = ledgers_root / "automation_state.json"
    if not state_path.exists():
        template = project_root / "templates" / "inquiry" / "automation_state.template.json"
        if not template.is_file():
            raise SystemExit(f"missing automation state template: {template}")
        temp_path = state_path.with_name(f".{state_path.name}.tmp")
        shutil.copyfile(template, temp_path)
        temp_path.replace(state_path)
    return state_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize PPT Order Autopilot runtime ledgers.")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    state_path = bootstrap_runtime(Path(args.project_root))
    print(state_path)


if __name__ == "__main__":
    main()
