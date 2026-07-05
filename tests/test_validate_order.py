from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ORDERS_ROOT = PROJECT_ROOT / "tmp" / "test-suite-orders"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", *args],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ValidateOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(PROJECT_ROOT / "tmp", ignore_errors=True)
        for name in ["orders.jsonl", "sent_messages.jsonl", "ui_actions.jsonl", "approvals.jsonl"]:
            (PROJECT_ROOT / "ledgers" / name).unlink(missing_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(PROJECT_ROOT / "tmp", ignore_errors=True)
        for name in ["orders.jsonl", "sent_messages.jsonl", "ui_actions.jsonl", "approvals.jsonl"]:
            (PROJECT_ROOT / "ledgers" / name).unlink(missing_ok=True)

    def create_order(self) -> Path:
        result = run_tool(
            "tools/init_order.py",
            "--title",
            "测试订单",
            "--contact",
            "客服A",
            "--orders-root",
            "tmp/test-suite-orders",
            "--with-templates",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        return Path(result.stdout.strip())

    def test_invalid_order_id_is_rejected(self) -> None:
        result = run_tool(
            "tools/init_order.py",
            "--title",
            "bad",
            "--order-id",
            "../bad",
            "--orders-root",
            "tmp/test-suite-orders",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid order_id", result.stdout)

    def test_template_order_passes_base_but_blocks_chat_capture(self) -> None:
        order_dir = self.create_order()

        base = run_tool("tools/validate_order.py", str(order_dir), "--gate", "base")
        self.assertEqual(base.returncode, 0, base.stdout)

        chat = run_tool("tools/validate_order.py", str(order_dir), "--gate", "chat_capture")
        self.assertNotEqual(chat.returncode, 0)
        self.assertIn("coverage_result.json status must be success", chat.stdout)

    def test_required_requirement_without_evidence_fails_briefing(self) -> None:
        order_dir = self.create_order()
        write_json(
            order_dir / "01_chat" / "coverage_result.json",
            {
                "status": "success",
                "screens_captured": 1,
                "top_anchor": "客户 10:00: 做 PPT",
                "bottom_anchor": "客服 10:01: 收到",
                "adjacent_overlap_checks": {"passed": 0, "total": 0, "failed_screen_pairs": []},
                "attachments_found": 0,
                "attachments_downloaded": 0,
                "attachments_failed": 0,
                "suspected_conflicts": 0,
                "blocking_issues": [],
            },
        )
        (order_dir / "01_chat" / "message_index.jsonl").write_text(
            json.dumps(
                {
                    "message_id": "msg_001",
                    "screen_ids": ["screen_001"],
                    "sender": "客户",
                    "sent_at": "2026-07-06T10:00:00+08:00",
                    "text": "做 PPT",
                    "attachments": [],
                    "ocr_confidence": "high",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (order_dir / "02_attachments_raw" / "attachment_index.jsonl").write_text("", encoding="utf-8")
        (order_dir / "03_requirements" / "order_brief.md").write_text("# Order Brief\n", encoding="utf-8")
        write_json(
            order_dir / "03_requirements" / "requirements.json",
            {
                "topic": {
                    "value": "测试 PPT",
                    "evidence": None,
                    "confidence": "high",
                    "required": True,
                }
            },
        )

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "briefing")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("topic is required but evidence is empty", result.stdout)


if __name__ == "__main__":
    unittest.main()

