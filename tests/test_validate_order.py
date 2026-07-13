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

    def prepare_order_through_production(self) -> Path:
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
                    "text": "做测试 PPT",
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
                    "evidence": "客户 10:00: 做测试 PPT",
                    "confidence": "high",
                    "required": True,
                },
                "sample_required": {
                    "value": False,
                    "evidence": "owner confirmed direct production",
                    "confidence": "high",
                    "required": True,
                },
            },
        )
        write_json(
            order_dir / "03_requirements" / "pending_approval.json",
            {
                "approval_id": "appr_test",
                "action_type": "accept_order",
                "order_id": "2026-07-06_001",
                "contact_id": "cs_a",
                "draft_message": "我接这个单",
                "draft_sha256": "sha256:" + "a" * 64,
                "created_at": "2026-07-06T10:02:00+08:00",
                "status": "approved",
            },
        )
        (order_dir / "00_state" / "approvals.jsonl").write_text(
            json.dumps(
                {
                    "approval_id": "appr_test",
                    "order_id": "2026-07-06_001",
                    "action_type": "accept_order",
                    "contact_id": "cs_a",
                    "draft_sha256": "sha256:" + "a" * 64,
                    "status": "approved",
                    "created_at": "2026-07-06T10:02:00+08:00",
                    "approved_at": "2026-07-06T10:03:00+08:00",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return order_dir

    def valid_contract(self, include_job_path: bool = True) -> dict:
        slide = {
            "slide_no": 1,
            "title": "测试 PPT",
            "page_type": "content",
            "exact_content_source": "03_requirements/requirements.json",
            "required_asset_ids": ["style_anchor", "template_master", "page_family_content"],
        }
        if include_job_path:
            slide["job_path"] = "05_production/slide_jobs/slide_01/job.json"
        return {
            "deck": {
                "deck_title": "测试 PPT",
                "page_count": 1,
                "aspect_ratio": "16:9",
                "deliverables": ["pptx", "pdf"],
                "language": "zh-CN",
            },
            "method": {
                "production_mode": "image_model_full_slide",
                "subagents_required": True,
                "default_reasoning_level": "high",
                "same_backend_as_sample": True,
                "forbidden_methods": ["html_css_render", "svg_render", "pillow_slide", "manual_overlay", "python_pptx_native_layout"],
            },
            "style_kit": {"required": True, "path": "04_sample/style_kit/style_kit.json"},
            "asset_registry": [],
            "slides": [slide],
            "coverage_matrix": [
                {"requirement": "topic", "source": "requirements.topic", "covered_by": ["slide_01"]},
                {"requirement": "sample_required", "source": "requirements.sample_required", "covered_by": ["method"]},
            ],
            "approval": {"approval_id": "appr_test", "approved_by": "owner", "approved_at": "2026-07-06T10:03:00+08:00"},
        }

    def add_style_kit(self, order_dir: Path) -> None:
        style_dir = order_dir / "04_sample" / "style_kit"
        style_dir.mkdir(parents=True, exist_ok=True)
        for image_name in ["style_anchor.png", "template_master.png", "content_ref.png"]:
            (style_dir / image_name).write_bytes(b"fake-image")
        write_json(
            style_dir / "style_kit.json",
            {
                "approved_sample_paths": ["04_sample/sample_preview_images/sample_01.png"],
                "style_anchor": "04_sample/style_kit/style_anchor.png",
                "template_master": "04_sample/style_kit/template_master.png",
                "navigation_bar": None,
                "page_family_refs": {"cover": "04_sample/style_kit/style_anchor.png", "content": "04_sample/style_kit/content_ref.png"},
                "locked_elements": "04_sample/style_kit/locked_elements.json",
                "must_match": ["color palette", "title hierarchy"],
            },
        )
        write_json(style_dir / "locked_elements.json", {"canvas": {"width": 1920, "height": 1080}})

    def add_slide_jobs(self, order_dir: Path, reasoning_level: str = "high") -> None:
        bundle_dir = order_dir / "05_production" / "slide_jobs" / "slide_01"
        input_dir = bundle_dir / "input_images"
        input_dir.mkdir(parents=True, exist_ok=True)
        for image_name in ["style_anchor.png", "template_master.png", "page_family_ref.png"]:
            (input_dir / image_name).write_bytes(b"fake-image")
        (bundle_dir / "prompt.md").write_text("Generate slide 1.", encoding="utf-8")
        write_json(
            order_dir / "05_production" / "slide_jobs" / "slide_jobs.json",
            {
                "contract_path": "03_requirements/production_contract.json",
                "jobs": [
                    {
                        "job_id": "test-order:slide_01",
                        "slide_no": 1,
                        "bundle_dir": "05_production/slide_jobs/slide_01",
                        "job_file": "05_production/slide_jobs/slide_01/job.json",
                        "prompt_file": "05_production/slide_jobs/slide_01/prompt.md",
                        "input_images_dir": "05_production/slide_jobs/slide_01/input_images",
                        "render_result_file": "05_production/slide_jobs/slide_01/render_result.json",
                        "output_image": "05_production/origin_image/slide_01.png",
                    }
                ],
            },
        )
        write_json(
            bundle_dir / "job.json",
            {
                "job_id": "test-order:slide_01",
                "attempt": 1,
                "max_attempts": 3,
                "repair_of": None,
                "slide_no": 1,
                "page_type": "content",
                "title": "测试 PPT",
                "deck_context": {
                    "deck_title": "测试 PPT",
                    "goal": "验证自动化生产",
                    "audience": "测试用户",
                    "story_summary": "封面到内容结论",
                    "total_slides": 1,
                    "language": "zh-CN",
                },
                "local_context": {
                    "section": "测试",
                    "slide_purpose": "展示测试内容",
                    "previous_slide_summary": None,
                    "next_slide_summary": None,
                },
                "exact_content": {"title": "测试 PPT", "bullets": ["第一点"]},
                "input_images": [
                    {"image_id": "style_anchor", "bundle_path": "input_images/style_anchor.png", "role": "style_anchor", "required": True, "fidelity_rule": "style reference only", "if_missing": "block"},
                    {"image_id": "template_master", "bundle_path": "input_images/template_master.png", "role": "template_reference", "required": True, "fidelity_rule": "preserve layout system and spacing", "if_missing": "block"},
                    {"image_id": "page_family", "bundle_path": "input_images/page_family_ref.png", "role": "page_family_reference", "required": True, "fidelity_rule": "style reference only", "if_missing": "block"},
                ],
                "visual_constraints": {"must_match_style_anchor": True, "use_navigation_bar": False, "locked_elements": "use style kit rules if provided"},
                "backend": {
                    "selected_backend": "test-image-backend",
                    "mode": "image_edit",
                    "requires_image_inputs": True,
                },
                "qa_requirements": ["exact_content", "text_readability", "asset_fidelity", "style_match"],
                "worker_policy": {
                    "reasoning_level": reasoning_level,
                    "image_generation_only": True,
                    "must_not_use_text_only_fallback": True,
                    "if_required_image_missing": "block",
                },
            },
        )

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

    def test_contract_accuracy_rejects_missing_job_path(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract(include_job_path=False))

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "contract_accuracy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("slide 1 missing job_path", result.stdout)

    def test_slide_jobs_reject_empty_exact_content(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        self.add_style_kit(order_dir)
        self.add_slide_jobs(order_dir)
        write_json(order_dir / "05_production" / "slide_jobs" / "slide_01" / "job.json", {
            "job_id": "test-order:slide_01",
            "attempt": 1,
            "max_attempts": 3,
            "repair_of": None,
            "slide_no": 1,
            "page_type": "content",
            "title": "测试 PPT",
            "deck_context": {"deck_title": "测试 PPT"},
            "local_context": {"slide_purpose": "测试"},
            "exact_content": {},
            "input_images": [
                {"image_id": "style_anchor", "bundle_path": "input_images/style_anchor.png", "role": "style_anchor", "required": True, "fidelity_rule": "style reference only", "if_missing": "block"},
                {"image_id": "template_master", "bundle_path": "input_images/template_master.png", "role": "template_reference", "required": True, "fidelity_rule": "preserve layout system and spacing", "if_missing": "block"},
                {"image_id": "page_family", "bundle_path": "input_images/page_family_ref.png", "role": "page_family_reference", "required": True, "fidelity_rule": "style reference only", "if_missing": "block"},
            ],
            "visual_constraints": {"must_match_style_anchor": True, "use_navigation_bar": False},
            "backend": {"selected_backend": "test-image-backend", "mode": "image_edit", "requires_image_inputs": True},
            "qa_requirements": ["exact_content", "text_readability", "style_match"],
            "worker_policy": {"reasoning_level": "high", "image_generation_only": True, "must_not_use_text_only_fallback": True, "if_required_image_missing": "block"},
        })

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "slide_jobs")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact_content is empty", result.stdout)

    def test_slide_jobs_reject_low_reasoning(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        self.add_style_kit(order_dir)
        self.add_slide_jobs(order_dir, reasoning_level="low")

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "slide_jobs")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("worker reasoning must be medium/high", result.stdout)

    def test_slide_jobs_require_deck_and_local_context(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        self.add_style_kit(order_dir)
        self.add_slide_jobs(order_dir)
        job_path = order_dir / "05_production" / "slide_jobs" / "slide_01" / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job.pop("deck_context")
        job.pop("local_context")
        write_json(job_path, job)

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "slide_jobs")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deck_context must be a non-empty object", result.stdout)
        self.assertIn("local_context must be a non-empty object", result.stdout)

    def test_visual_qa_rejects_invisible_required_asset(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        self.add_style_kit(order_dir)
        self.add_slide_jobs(order_dir)
        (order_dir / "05_production" / "origin_image").mkdir(parents=True, exist_ok=True)
        (order_dir / "05_production" / "origin_image" / "slide_01.png").write_bytes(b"fake-output")
        write_json(
            order_dir / "05_production" / "slide_jobs" / "slide_01" / "render_result.json",
            {
                "job_id": "test-order:slide_01",
                "attempt": 1,
                "slide_no": 1,
                "status": "success",
                "output_image": "05_production/origin_image/slide_01.png",
                "input_images_seen": ["style_anchor.png"],
                "asset_fidelity": [],
                "style_match": "pass",
                "text_readability": "pass",
                "blockers": [],
            },
        )
        write_json(
            order_dir / "05_production" / "slide_run_state.json",
            {
                "status": "complete",
                "slides": [
                    {
                        "job_id": "test-order:slide_01",
                        "slide_no": 1,
                        "bundle_dir": "05_production/slide_jobs/slide_01",
                        "job_file": "05_production/slide_jobs/slide_01/job.json",
                        "render_result_file": "05_production/slide_jobs/slide_01/render_result.json",
                        "status": "accepted",
                        "current_attempt": 1,
                        "max_attempts": 3,
                        "accepted_attempt": 1,
                        "attempts": [
                            {
                                "attempt": 1,
                                "status": "accepted",
                                "job_snapshot_file": "05_production/slide_jobs/slide_01/job.json",
                                "render_result_file": "05_production/slide_jobs/slide_01/render_result.json",
                                "output_image": "05_production/origin_image/slide_01.png",
                                "failure_class": "none",
                                "repair_instructions": None,
                            }
                        ],
                        "selected_source": "05_production/origin_image/slide_01.png",
                        "backend_used": "same_as_sample",
                        "input_images_seen": ["style_anchor.png"],
                        "asset_fidelity_check": "ok",
                        "style_check": "ok",
                        "text_check": "ok",
                        "blockers": [],
                    }
                ],
            },
        )
        write_json(
            order_dir / "05_production" / "visual_qa_result.json",
            {
                "status": "pass",
                "asset_fidelity": {
                    "slide_01": {
                        "required_assets": [
                            {
                                "asset_id": "style_anchor",
                                "expected_role": "style_anchor",
                                "visible_in_output": False,
                                "fidelity_status": "fail",
                                "notes": "not visible",
                            }
                        ]
                    }
                },
                "style_drift": [],
                "navigation_consistency": [],
                "text_readability": [{"slide_no": 1, "status": "pass", "notes": None}],
                "blockers": [],
            },
        )

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "visual_qa")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("asset_fidelity slide_01 asset not visible", result.stdout)


if __name__ == "__main__":
    unittest.main()
