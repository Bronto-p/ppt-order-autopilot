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

    def valid_contract(self, exact_content: dict | None = None) -> dict:
        exact_content = exact_content if exact_content is not None else {
            "title": "测试 PPT",
            "bullets": ["第一点", "第二点"],
            "must_render_text": ["测试 PPT"],
        }
        return {
            "deck": {
                "deck_title": "测试 PPT",
                "page_count": 1,
                "aspect_ratio": "16:9",
                "deliverables": ["pptx", "pdf"],
                "language": "zh-CN",
                "requirements_source": "03_requirements/requirements.json",
            },
            "production_method": {
                "method": "image_model_full_slide_only",
                "backend": "same_as_sample",
                "same_backend_as_sample": True,
                "parent_may_generate_slides": False,
                "subagents_required": True,
                "default_worker_reasoning_level": "high",
                "forbidden_methods": ["html_css_render", "svg_render", "pillow_slide", "manual_overlay", "python_pptx_native_layout"],
            },
            "style_system": {
                "style_anchor_paths": ["04_sample/style_master/style_anchor.png"],
                "template_master_path": "04_sample/style_master/template_master.png",
                "navigation_bar_reference_path": "04_sample/style_master/navigation_bar_reference.png",
                "page_family_refs": {"content": "04_sample/style_master/content_reference.png"},
                "style_spec_path": "04_sample/style_master/style_spec.json",
                "locked_elements_path": "04_sample/style_master/locked_elements.json",
            },
            "asset_registry": [],
            "asset_allowlist": [
                "04_sample/style_master/style_anchor.png",
                "04_sample/style_master/template_master.png",
                "04_sample/style_master/content_reference.png",
            ],
            "forbidden_assets": [],
            "slides": [
                {
                    "slide_no": 1,
                    "title": "测试 PPT",
                    "page_type": "content",
                    "section": "正文",
                    "exact_content": exact_content,
                    "content_evidence": [{"source": "03_requirements/requirements.json", "field": "topic"}],
                    "input_images": [
                        {
                            "path": "04_sample/style_master/style_anchor.png",
                            "role": "style_anchor",
                            "fidelity_rule": "style reference only",
                            "required": True,
                        },
                        {
                            "path": "04_sample/style_master/template_master.png",
                            "role": "template_reference",
                            "fidelity_rule": "preserve layout system and spacing",
                            "required": True,
                        },
                        {
                            "path": "04_sample/style_master/content_reference.png",
                            "role": "page_family_reference",
                            "fidelity_rule": "style reference only",
                            "required": True,
                        },
                    ],
                    "layout_constraints": {"use_navigation_bar": False},
                    "must_preserve": ["exact title text"],
                    "forbidden_changes": ["do not change title"],
                    "worker": {"reasoning_level": "high", "job_file": "05_production/prompts/slide_01.json"},
                    "qa_requirements": ["text_readable", "style_matches_anchor"],
                }
            ],
            "coverage_matrix": [
                {"requirement": "topic", "source": "requirements.topic", "covered_by": ["slide_01"]},
                {"requirement": "sample_required", "source": "requirements.sample_required", "covered_by": ["production_method"]},
            ],
            "approval": {"approval_id": "appr_test", "approved_by": "owner", "approved_at": "2026-07-06T10:03:00+08:00"},
        }

    def add_style_master(self, order_dir: Path) -> None:
        style_dir = order_dir / "04_sample" / "style_master"
        style_dir.mkdir(parents=True, exist_ok=True)
        for image_name in ["style_anchor.png", "template_master.png", "content_reference.png"]:
            (style_dir / image_name).write_bytes(b"fake-image")
        write_json(
            order_dir / "04_sample" / "approved_sample_reference.json",
            {
                "approved_samples": [
                    {
                        "slide_no": 1,
                        "path": "04_sample/style_master/style_anchor.png",
                        "use_as": "style_anchor",
                        "page_family": "content",
                    }
                ],
                "style_system": {
                    "template_master": "04_sample/style_master/template_master.png",
                    "style_anchor": "04_sample/style_master/style_anchor.png",
                    "navigation_bar": None,
                    "color_behavior": "blue tech",
                    "typography_behavior": "clear hierarchy",
                    "image_treatment": "glass panels",
                },
                "must_match_in_production": ["palette", "title hierarchy"],
            },
        )
        write_json(style_dir / "style_spec.json", {"palette": {}, "typography": {}, "spacing": {}, "shape_language": "cards", "image_treatment": "clean", "background_treatment": "light"})
        write_json(style_dir / "locked_elements.json", {"coordinate_space": {"width": 1920, "height": 1080}, "elements": []})

    def add_slide_jobs(self, order_dir: Path, reasoning_level: str = "high") -> None:
        prompts_dir = order_dir / "05_production" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            order_dir / "05_production" / "slide_jobs.json",
            {
                "contract_path": "03_requirements/production_contract.json",
                "jobs": [
                    {
                        "slide_no": 1,
                        "job_file": "05_production/prompts/slide_01.json",
                        "output_image": "05_production/origin_image/slide_01.png",
                    }
                ],
            },
        )
        write_json(
            prompts_dir / "slide_01.json",
            {
                "slide_id": "slide_01",
                "slide_no": 1,
                "title": "测试 PPT",
                "page_type": "content",
                "deck_context": {"deck_theme": "测试", "confirmed_style": "blue tech", "canonical_terms": ["测试"]},
                "local_context": {"what_this_slide_must_say": "测试内容"},
                "exact_content": {"title": "测试 PPT", "bullets": ["第一点"]},
                "input_images": [
                    {"path": "04_sample/style_master/style_anchor.png", "role": "style_anchor", "required": True, "fidelity_rule": "style reference only"},
                    {"path": "04_sample/style_master/template_master.png", "role": "template_reference", "required": True, "fidelity_rule": "preserve layout system and spacing"},
                    {"path": "04_sample/style_master/content_reference.png", "role": "page_family_reference", "required": True, "fidelity_rule": "style reference only"},
                ],
                "visual_constraints": {"template": "match"},
                "backend": {"selected_backend": "same_as_sample", "requires_image_inputs": True},
                "worker_policy": {
                    "reasoning_level": reasoning_level,
                    "must_return_blocker_if_image_not_visible": True,
                    "must_not_use_text_only_fallback": True,
                },
                "qa_requirements": ["text_readable"],
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

    def test_contract_accuracy_rejects_empty_exact_content(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract(exact_content={}))

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "contract_accuracy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("slide 1 exact_content is empty", result.stdout)

    def test_slide_jobs_reject_low_reasoning(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        self.add_style_master(order_dir)
        self.add_slide_jobs(order_dir, reasoning_level="low")

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "slide_jobs")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("worker reasoning must be medium/high", result.stdout)

    def test_visual_qa_rejects_invisible_required_asset(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        self.add_style_master(order_dir)
        self.add_slide_jobs(order_dir)
        write_json(
            order_dir / "05_production" / "slide_run_state.json",
            {
                "status": "complete",
                "slides": [
                    {
                        "slide_no": 1,
                        "job_file": "05_production/prompts/slide_01.json",
                        "status": "accepted",
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
