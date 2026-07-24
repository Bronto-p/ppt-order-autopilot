from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ORDERS_ROOT = PROJECT_ROOT / "tmp" / "test-suite-orders"
LEDGERS_ROOT = PROJECT_ROOT / "tmp" / "test-suite-ledgers"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PPT_AUTOPILOT_LEDGER_ROOT"] = str(LEDGERS_ROOT)
    return subprocess.run(
        ["python3", *args],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


class ValidateOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(PROJECT_ROOT / "tmp", ignore_errors=True)

    def tearDown(self) -> None:
        shutil.rmtree(PROJECT_ROOT / "tmp", ignore_errors=True)

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
        order_id = json.loads((order_dir / "00_state" / "state.json").read_text(encoding="utf-8"))["order_id"]
        draft_message = "我接这个单"
        draft_sha256 = sha256_text(draft_message)
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
                "order_id": order_id,
                "contact_id": "cs_a",
                "draft_message": draft_message,
                "draft_sha256": draft_sha256,
                "created_at": "2026-07-06T10:02:00+08:00",
                "status": "approved",
            },
        )
        (order_dir / "00_state" / "approvals.jsonl").write_text(
            json.dumps(
                {
                    "approval_id": "appr_test",
                    "order_id": order_id,
                    "action_type": "accept_order",
                    "contact_id": "cs_a",
                    "draft_sha256": draft_sha256,
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
            "output_mode": "image_first",
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
                "production_mode": "image_first",
                "subagents_required": True,
                "default_reasoning_level": "high",
                "same_backend_as_sample": True,
                "forbidden_methods": ["html_css_render", "svg_render", "pillow_slide", "manual_overlay", "python_pptx_native_layout"],
            },
            "style_kit": {
                "required": True,
                "path": "04_sample/style_kit/style_kit.json",
                "source_type": "approved_style_brief",
            },
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
                "source": {
                    "source_type": "approved_style_brief",
                    "source_paths": ["03_requirements/requirements.json"],
                    "approval_id": "appr_test",
                },
                "approved_sample_paths": [],
                "style_anchor": "04_sample/style_kit/style_anchor.png",
                "template_master": "04_sample/style_kit/template_master.png",
                "navigation_bar": None,
                "page_family_refs": {"cover": "04_sample/style_kit/style_anchor.png", "content": "04_sample/style_kit/content_ref.png"},
                "locked_elements": "04_sample/style_kit/locked_elements.json",
                "must_match": ["color palette", "title hierarchy"],
            },
        )
        write_json(
            style_dir / "locked_elements.json",
            {"canvas": {"width": 1920, "height": 1080}, "render_strategy": "reference_only"},
        )

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
                        "finalization_file": "05_production/slide_jobs/slide_01/finalization.json",
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
                "output_mode": "image_first",
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
                "visual_constraints": {
                    "must_match_style_anchor": True,
                    "use_navigation_bar": False,
                    "locked_elements": "use style kit rules if provided",
                    "locked_chrome": {
                        "mode": "none",
                        "variant_id": None,
                        "active_navigation_section": None,
                        "page_number_text": None,
                        "style_variant_path": None,
                        "style_variant_sha256": None,
                        "overlay_bundle_path": None,
                        "overlay_sha256": None,
                        "content_safe_box": None,
                    },
                },
                "backend": {
                    "selected_backend": "test-image-backend",
                    "mode": "image_edit",
                    "requires_image_inputs": True,
                },
                "qa_requirements": ["exact_content", "text_readability", "asset_fidelity", "style_match"],
                "worker_policy": {
                    "reasoning_level": reasoning_level,
                    "one_slide_only": True,
                    "uses_image_generation": True,
                    "image_generation_only": True,
                    "must_generate_complete_slide": True,
                    "must_render_all_visible_content": True,
                    "forbid_background_only": True,
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

    def test_order_initialization_bootstraps_global_runtime(self) -> None:
        self.create_order()
        for name in ["inquiries.jsonl", "orders.jsonl", "sent_messages.jsonl", "ui_actions.jsonl", "approvals.jsonl"]:
            self.assertTrue((LEDGERS_ROOT / name).exists(), name)
        automation_state = json.loads((LEDGERS_ROOT / "automation_state.json").read_text(encoding="utf-8"))
        self.assertEqual(automation_state["state"], "IDLE")
        self.assertIn("automation_binding", automation_state)

    def test_owner_direct_defaults_to_complete_slide_sample(self) -> None:
        result = run_tool(
            "tools/init_order.py",
            "--title", "owner sample",
            "--execution-mode", "owner_direct",
            "--intake-source", "workspace_file",
            "--orders-root", "tmp/test-suite-orders",
            "--with-templates",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        order_dir = Path(result.stdout.strip())
        requirements = json.loads((order_dir / "03_requirements" / "requirements.json").read_text(encoding="utf-8"))
        self.assertIs(requirements["sample_required"]["value"], True)
        self.assertEqual(requirements["sample_scope"]["value"], "one complete representative slide with real content")
        self.assertEqual(requirements["output_mode"]["value"], "image_first")

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

    def test_codex_attachment_intake_does_not_require_fake_screenshots(self) -> None:
        order_dir = self.create_order()
        attachment = order_dir / "02_attachments_raw" / "from_codex" / "brief.pdf"
        attachment.parent.mkdir(parents=True, exist_ok=True)
        attachment.write_bytes(b"customer-brief")
        write_json(
            order_dir / "01_chat" / "coverage_result.json",
            {
                "source_type": "codex_attachment",
                "status": "success",
                "screens_captured": 0,
                "top_anchor": None,
                "bottom_anchor": None,
                "adjacent_overlap_checks": {"passed": 0, "total": 0, "failed_screen_pairs": []},
                "attachments_found": 1,
                "attachments_downloaded": 1,
                "attachments_failed": 0,
                "source_attachment_paths": ["02_attachments_raw/from_codex/brief.pdf"],
                "suspected_conflicts": 0,
                "blocking_issues": [],
            },
        )
        (order_dir / "01_chat" / "chat_coverage_report.md").write_text(
            "Source: codex_attachment\nStatus: complete\n",
            encoding="utf-8",
        )
        (order_dir / "01_chat" / "message_index.jsonl").write_text(
            json.dumps(
                {
                    "message_id": "codex_prompt_001",
                    "screen_ids": [],
                    "sender": "owner",
                    "sent_at": "2026-07-06T10:00:00+08:00",
                    "text": "把附件当作一个 PPT 订单",
                    "attachments": ["att_codex_001"],
                    "ocr_confidence": "high",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (order_dir / "02_attachments_raw" / "attachment_index.jsonl").write_text(
            json.dumps(
                {
                    "attachment_id": "att_codex_001",
                    "saved_path": "02_attachments_raw/from_codex/brief.pdf",
                    "source_message_id": "codex_prompt_001",
                    "sha256": sha256_file(attachment),
                    "download_status": "success",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "chat_capture")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_required_empty_collection_fails_briefing(self) -> None:
        order_dir = self.prepare_order_through_production()
        requirements_path = order_dir / "03_requirements" / "requirements.json"
        requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
        requirements["content_materials"] = {
            "value": [],
            "evidence": "客户说稍后提供材料",
            "confidence": "high",
            "required": True,
        }
        write_json(requirements_path, requirements)

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "briefing")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("content_materials is required but value is empty", result.stdout)

    def test_pending_approval_hash_must_match_message(self) -> None:
        order_dir = self.prepare_order_through_production()
        pending_path = order_dir / "03_requirements" / "pending_approval.json"
        pending = json.loads(pending_path.read_text(encoding="utf-8"))
        pending["draft_sha256"] = "sha256:" + "b" * 64
        write_json(pending_path, pending)

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "decision")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("draft_sha256 does not match draft_message", result.stdout)

    def test_approval_from_another_order_cannot_authorize_production(self) -> None:
        order_dir = self.prepare_order_through_production()
        approvals_path = order_dir / "00_state" / "approvals.jsonl"
        approval = json.loads(approvals_path.read_text(encoding="utf-8"))
        approval["order_id"] = "2026-07-06_999"
        approvals_path.write_text(json.dumps(approval, ensure_ascii=False) + "\n", encoding="utf-8")
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "production")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("production approval_id not approved for production", result.stdout)

    def test_attachment_path_cannot_escape_order_folder(self) -> None:
        order_dir = self.prepare_order_through_production()
        attachment = {
            "attachment_id": "att_escape",
            "saved_path": "../../outside.png",
            "source_message_id": "msg_001",
            "sha256": "sha256:" + "a" * 64,
            "download_status": "success",
        }
        (order_dir / "02_attachments_raw" / "attachment_index.jsonl").write_text(
            json.dumps(attachment, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "chat_capture")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("saved_path must stay inside", result.stdout)

    def test_contract_accuracy_rejects_missing_job_path(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract(include_job_path=False))

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "contract_accuracy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("slide 1 missing job_path", result.stdout)

    def test_direct_production_accepts_approved_style_brief(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        self.add_style_kit(order_dir)

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "sample_accuracy")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_sample_required_rejects_non_sample_style_source(self) -> None:
        order_dir = self.prepare_order_through_production()
        requirements_path = order_dir / "03_requirements" / "requirements.json"
        requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
        requirements["sample_required"]["value"] = True
        write_json(requirements_path, requirements)
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        write_json(order_dir / "04_sample" / "sample_contract.json", {})
        self.add_style_kit(order_dir)

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "sample_accuracy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sample-required order must use approved_sample style source", result.stdout)

    def test_sample_state_machine_waits_for_customer_feedback(self) -> None:
        machine = json.loads((PROJECT_ROOT / "configs" / "state_machine.json").read_text(encoding="utf-8"))
        states = machine["states"]

        self.assertEqual(states["SAMPLE_QA"]["allowed_next"], ["WAITING_OWNER_SAMPLE_SEND_CONFIRMATION", "FAILED_BLOCKED"])
        self.assertNotIn("FULL_PRODUCTION", states["WAITING_OWNER_SAMPLE_SEND_CONFIRMATION"]["allowed_next"])
        self.assertEqual(states["WAITING_OWNER_SAMPLE_SEND_CONFIRMATION"]["allowed_next"], ["SAMPLE_SENT", "FAILED_BLOCKED"])
        self.assertIn("WAITING_CLIENT_SAMPLE_FEEDBACK", states["SAMPLE_SENT"]["allowed_next"])
        self.assertIn("SAMPLE_APPROVED", states["WAITING_CLIENT_SAMPLE_FEEDBACK"]["allowed_next"])
        self.assertIn("FULL_PRODUCTION", states["SAMPLE_APPROVED"]["allowed_next"])
        self.assertIn("OWNER_SAMPLE_PRODUCTION", states["DIRECT_PRODUCTION_ALLOWED"]["allowed_next"])
        self.assertEqual(states["OWNER_SAMPLE_PRODUCTION"]["allowed_next"], ["OWNER_SAMPLE_REVIEW", "FAILED_BLOCKED"])
        self.assertTrue(states["OWNER_SAMPLE_REVIEW"]["requires_owner_approval"])

    def test_owner_sample_rejects_background_only_manifest(self) -> None:
        order_dir = self.prepare_order_through_production()
        state_path = order_dir / "00_state" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.update({"execution_mode": "owner_direct", "delivery_target": "owner_codex"})
        write_json(state_path, state)
        requirements_path = order_dir / "03_requirements" / "requirements.json"
        requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
        requirements["sample_required"]["value"] = True
        write_json(requirements_path, requirements)
        with (order_dir / "00_state" / "approvals.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps({
                "approval_id": "owner_instruction_test",
                "order_id": state["order_id"],
                "action_type": "owner_direct_instruction",
                "status": "approved",
            }) + "\n")
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        sample_dir = order_dir / "04_sample"
        write_json(sample_dir / "sample_contract.json", {
            "sample_page_count": 1,
            "sample_slide_no": 1,
            "sample_goal": "both",
            "use_real_content": True,
            "output_mode": "image_first",
            "generation_scope": "complete_slide",
            "reference_files": [],
            "approval_id": "owner_instruction_test",
            "backend": {
                "selected_backend": "imagegen",
                "requires_image_inputs": False,
                "uses_image_generation": True,
                "image_generation_only": True,
            },
        })
        (sample_dir / "sample_prompt.md").write_text("Generate a background plate with no text.\n", encoding="utf-8")
        (sample_dir / "sample_qa.md").write_text("Status: pass\n", encoding="utf-8")
        preview = sample_dir / "sample_preview_images" / "sample_01.png"
        preview.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1600, 900), (10, 20, 40)).save(preview)
        write_json(sample_dir / "owner_sample_manifest.json", {
            "manifest_id": "owner_sample_1",
            "order_id": state["order_id"],
            "sample_slide_no": 1,
            "page_type": "content",
            "prompt_path": "04_sample/sample_prompt.md",
            "preview_path": "04_sample/sample_preview_images/sample_01.png",
            "preview_sha256": sha256_file(preview),
            "output_mode": "image_first",
            "generation_scope": "background_only",
            "contains_real_content": True,
            "qa_checks": {
                "full_slide_composition": False,
                "all_required_text_visible": False,
                "not_background_only": False,
                "text_readability": True,
            },
            "backend": {
                "selected_backend": "imagegen",
                "uses_image_generation": True,
                "image_generation_only": True,
            },
            "created_at": "2026-07-22T13:00:00+08:00",
        })

        checked = run_tool("tools/validate_order.py", str(order_dir), "--gate", "owner_sample_ready")
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("complete slide, not a background plate", checked.stdout)
        self.assertIn("prompt requests a background/visual layer", checked.stdout)

    def test_sample_delivery_manifest_requires_matching_send_approval(self) -> None:
        order_dir = self.prepare_order_through_production()
        order_id = json.loads((order_dir / "00_state" / "state.json").read_text(encoding="utf-8"))["order_id"]
        sample_dir = order_dir / "04_sample"
        write_json(sample_dir / "sample_contract.json", {"sample_slides": [1]})
        (sample_dir / "sample_qa.md").write_text("Status: pass\n", encoding="utf-8")
        message = "这是样稿，请查收。"
        (sample_dir / "sample_delivery_message.md").write_text(message, encoding="utf-8")
        (sample_dir / "sample_deck.pdf").write_bytes(b"sample-pdf")
        message_sha = sha256_text(message)
        approval = {
            "approval_id": "appr_send_sample",
            "order_id": order_id,
            "action_type": "send_sample",
            "contact_id": "cs_a",
            "draft_sha256": message_sha,
            "status": "approved",
            "created_at": "2026-07-06T10:04:00+08:00",
            "approved_at": "2026-07-06T10:05:00+08:00",
        }
        approvals_path = order_dir / "00_state" / "approvals.jsonl"
        with approvals_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(approval, ensure_ascii=False) + "\n")
        write_json(
            sample_dir / "sample_send_manifest.json",
            {
                "manifest_id": "manifest_sample_1",
                "order_id": order_id,
                "purpose": "sample",
                "contact_id": "cs_a",
                "approval_id": "appr_send_sample",
                "message_path": "04_sample/sample_delivery_message.md",
                "message_sha256": message_sha,
                "files": [
                    {
                        "path": "04_sample/sample_deck.pdf",
                        "sha256": sha256_file(sample_dir / "sample_deck.pdf"),
                        "type": "pdf",
                    }
                ],
                "created_at": "2026-07-06T10:05:00+08:00",
            },
        )

        passed = run_tool("tools/validate_order.py", str(order_dir), "--gate", "sample_delivery")
        self.assertEqual(passed.returncode, 0, passed.stdout)

        approval["action_type"] = "send_final_delivery"
        approvals_path.write_text(
            json.dumps(json.loads(approvals_path.read_text(encoding="utf-8").splitlines()[0]), ensure_ascii=False)
            + "\n"
            + json.dumps(approval, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        failed = run_tool("tools/validate_order.py", str(order_dir), "--gate", "sample_delivery")
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("has no matching send_sample approval", failed.stdout)

    def test_customer_approved_sample_can_authorize_style_kit(self) -> None:
        order_dir = self.prepare_order_through_production()
        order_id = json.loads((order_dir / "00_state" / "state.json").read_text(encoding="utf-8"))["order_id"]
        requirements_path = order_dir / "03_requirements" / "requirements.json"
        requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
        requirements["sample_required"]["value"] = True
        write_json(requirements_path, requirements)
        contract = self.valid_contract()
        contract["style_kit"]["source_type"] = "approved_sample"
        write_json(order_dir / "03_requirements" / "production_contract.json", contract)
        sample_dir = order_dir / "04_sample"
        write_json(sample_dir / "sample_contract.json", {"sample_slides": [1]})
        preview = sample_dir / "sample_preview_images" / "sample_01.png"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"sample-image")
        write_json(
            sample_dir / "customer_sample_decision.json",
            {
                "decision_id": "sample_decision_1",
                "order_id": order_id,
                "status": "approved",
                "source_message_ids": ["msg_customer_approved"],
                "evidence_text": "客户：可以，按这个做。",
                "confidence": "high",
                "captured_at": "2026-07-06T10:20:00+08:00",
            },
        )
        write_json(
            sample_dir / "approved_sample_reference.json",
            {
                "customer_decision_path": "04_sample/customer_sample_decision.json",
                "approved_samples": [
                    {
                        "slide_no": 1,
                        "path": "04_sample/sample_preview_images/sample_01.png",
                        "use_as": "content_page_reference",
                        "page_family": "content",
                    }
                ],
                "style_kit": {
                    "template_master": "04_sample/style_kit/template_master.png",
                    "style_anchor": "04_sample/style_kit/style_anchor.png",
                    "navigation_bar": None,
                    "color_behavior": "match sample",
                    "typography_behavior": "match sample",
                    "image_treatment": "match sample",
                },
                "must_match_in_production": ["palette", "title hierarchy"],
            },
        )
        style_dir = sample_dir / "style_kit"
        style_dir.mkdir(parents=True, exist_ok=True)
        for image_name in ["style_anchor.png", "template_master.png", "content_ref.png"]:
            (style_dir / image_name).write_bytes(b"fake-image")
        write_json(
            style_dir / "style_kit.json",
            {
                "source": {
                    "source_type": "approved_sample",
                    "source_paths": ["04_sample/sample_preview_images/sample_01.png"],
                    "customer_decision_path": "04_sample/customer_sample_decision.json",
                },
                "approved_sample_paths": ["04_sample/sample_preview_images/sample_01.png"],
                "style_anchor": "04_sample/style_kit/style_anchor.png",
                "template_master": "04_sample/style_kit/template_master.png",
                "navigation_bar": None,
                "page_family_refs": {"cover": "04_sample/style_kit/style_anchor.png", "content": "04_sample/style_kit/content_ref.png"},
                "locked_elements": "04_sample/style_kit/locked_elements.json",
                "must_match": ["color palette", "title hierarchy"],
            },
        )
        write_json(
            style_dir / "locked_elements.json",
            {"canvas": {"width": 1920, "height": 1080}, "render_strategy": "reference_only"},
        )

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "sample_accuracy")
        self.assertEqual(result.returncode, 0, result.stdout)

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
            "output_mode": "image_first",
            "deck_context": {"deck_title": "测试 PPT"},
            "local_context": {"slide_purpose": "测试"},
            "exact_content": {},
            "input_images": [
                {"image_id": "style_anchor", "bundle_path": "input_images/style_anchor.png", "role": "style_anchor", "required": True, "fidelity_rule": "style reference only", "if_missing": "block"},
                {"image_id": "template_master", "bundle_path": "input_images/template_master.png", "role": "template_reference", "required": True, "fidelity_rule": "preserve layout system and spacing", "if_missing": "block"},
                {"image_id": "page_family", "bundle_path": "input_images/page_family_ref.png", "role": "page_family_reference", "required": True, "fidelity_rule": "style reference only", "if_missing": "block"},
            ],
            "visual_constraints": {
                "must_match_style_anchor": True,
                "use_navigation_bar": False,
                "locked_chrome": {
                    "mode": "none",
                    "variant_id": None,
                    "active_navigation_section": None,
                    "page_number_text": None,
                    "style_variant_path": None,
                    "style_variant_sha256": None,
                    "overlay_bundle_path": None,
                    "overlay_sha256": None,
                    "content_safe_box": None,
                },
            },
            "backend": {"selected_backend": "test-image-backend", "mode": "image_edit", "requires_image_inputs": True},
            "qa_requirements": ["exact_content", "text_readability", "style_match"],
            "worker_policy": {"reasoning_level": "high", "one_slide_only": True, "uses_image_generation": True, "image_generation_only": True, "must_generate_complete_slide": True, "must_render_all_visible_content": True, "forbid_background_only": True, "must_not_use_text_only_fallback": True, "if_required_image_missing": "block"},
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

    def test_navigation_requires_locked_chrome_composite(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        self.add_style_kit(order_dir)
        self.add_slide_jobs(order_dir)
        job_path = order_dir / "05_production" / "slide_jobs" / "slide_01" / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["visual_constraints"]["use_navigation_bar"] = True
        write_json(job_path, job)

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "slide_jobs")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("navigation requires locked chrome composite", result.stdout)

    def test_navigation_locked_chrome_bundle_passes_slide_job_gate(self) -> None:
        order_dir = self.prepare_order_through_production()
        write_json(order_dir / "03_requirements" / "production_contract.json", self.valid_contract())
        self.add_style_kit(order_dir)
        style_dir = order_dir / "04_sample" / "style_kit"
        skeleton_path = style_dir / "locked_chrome_skeleton.png"
        style_overlay = style_dir / "locked_chrome_section_test.png"
        skeleton = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
        ImageDraw.Draw(skeleton).rectangle((0, 0, 99, 9), fill=(20, 40, 80, 255))
        skeleton.save(skeleton_path)
        variant = skeleton.copy()
        variant_draw = ImageDraw.Draw(variant)
        variant_draw.rectangle((0, 0, 19, 9), fill=(240, 80, 20, 255))
        variant_draw.rectangle((90, 0, 99, 9), fill=(0, 0, 0, 255))
        variant.save(style_overlay)
        write_json(
            style_dir / "locked_elements.json",
            {
                "canvas": {"width": 100, "height": 60},
                "render_strategy": "post_generation_composite",
                "content_safe_box": {"x": 0, "y": 10, "w": 100, "h": 50},
                "navigation_bar": {"x": 0, "y": 0, "w": 80, "h": 10, "rule": "pixel locked"},
                "page_number": {"x": 90, "y": 0, "w": 10, "h": 10, "rule": "pixel locked"},
                "invariant_skeleton": {
                    "source_path": "04_sample/style_kit/locked_chrome_skeleton.png",
                    "sha256": sha256_file(skeleton_path),
                },
                "dynamic_regions": [
                    {"region_id": "highlight_test", "role": "active_highlight", "x": 0, "y": 0, "w": 20, "h": 10},
                    {"region_id": "page_number", "role": "page_number", "x": 90, "y": 0, "w": 10, "h": 10},
                ],
                "page_number_policy": {"mode": "plain", "total_slides": None, "custom_values": None},
                "overlay_variants": [
                    {
                        "variant_id": "section_test",
                        "slide_no": 1,
                        "page_number_text": "1",
                        "dynamic_region_ids": ["highlight_test", "page_number"],
                        "source_path": "04_sample/style_kit/locked_chrome_section_test.png",
                        "sha256": sha256_file(style_overlay),
                        "active_navigation_section": "测试",
                    }
                ],
            },
        )
        self.add_slide_jobs(order_dir)
        bundle_dir = order_dir / "05_production" / "slide_jobs" / "slide_01"
        overlay_path = bundle_dir / "input_images" / "locked_chrome.png"
        overlay_path.write_bytes(style_overlay.read_bytes())
        job_path = bundle_dir / "job.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        job["input_images"].append(
            {
                "image_id": "locked_chrome",
                "bundle_path": "input_images/locked_chrome.png",
                "role": "locked_chrome_reference",
                "required": True,
                "fidelity_rule": "reserve chrome pixels; do not redraw",
                "sha256": sha256_file(overlay_path),
                "if_missing": "block",
            }
        )
        job["visual_constraints"]["use_navigation_bar"] = True
        job["visual_constraints"]["active_navigation_section"] = "测试"
        job["visual_constraints"]["locked_chrome"] = {
            "mode": "post_generation_composite",
            "variant_id": "section_test",
            "active_navigation_section": "测试",
            "page_number_text": "1",
            "style_variant_path": "04_sample/style_kit/locked_chrome_section_test.png",
            "style_variant_sha256": sha256_file(style_overlay),
            "overlay_bundle_path": "input_images/locked_chrome.png",
            "overlay_sha256": sha256_file(overlay_path),
            "content_safe_box": {"x": 0, "y": 10, "w": 100, "h": 50},
        }
        write_json(job_path, job)

        result = run_tool("tools/validate_order.py", str(order_dir), "--gate", "slide_jobs")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_locked_chrome_compositor_preserves_exact_pixels(self) -> None:
        order_dir = self.create_order()
        raw_path = order_dir / "05_production" / "slide_jobs" / "slide_01" / "attempts" / "attempt_01" / "output.png"
        overlay_path = order_dir / "05_production" / "slide_jobs" / "slide_01" / "input_images" / "locked_chrome.png"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        overlay_path.parent.mkdir(parents=True, exist_ok=True)

        Image.new("RGBA", (100, 60), (25, 40, 60, 255)).save(raw_path)
        overlay = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rectangle((0, 0, 99, 9), fill=(240, 80, 20, 255))
        overlay.save(overlay_path)
        output_rel = "05_production/origin_image/slide_01.png"
        receipt_rel = "05_production/slide_jobs/slide_01/finalization.json"

        result = run_tool(
            "tools/composite_locked_chrome.py",
            "--order-dir",
            str(order_dir),
            "--job-id",
            "test-order:slide_01",
            "--slide-no",
            "1",
            "--accepted-attempt",
            "1",
            "--variant-id",
            "section_test",
            "--active-navigation-section",
            "测试",
            "--raw-image",
            str(raw_path.relative_to(order_dir)),
            "--overlay-image",
            str(overlay_path.relative_to(order_dir)),
            "--expected-overlay-sha256",
            sha256_file(overlay_path),
            "--output-image",
            output_rel,
            "--receipt",
            receipt_rel,
            "--safe-box",
            "0",
            "10",
            "100",
            "50",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        final_image = Image.open(order_dir / output_rel).convert("RGBA")
        self.assertEqual(final_image.getpixel((5, 5)), (240, 80, 20, 255))
        self.assertEqual(final_image.getpixel((5, 20)), (25, 40, 60, 255))
        receipt = json.loads((order_dir / receipt_rel).read_text(encoding="utf-8"))
        self.assertTrue(receipt["locked_chrome"]["pixel_match"])
        self.assertEqual(receipt["final_output_sha256"], sha256_file(order_dir / output_rel))

        editable_path = order_dir / "05_production" / "slide_jobs" / "slide_01" / "editable-layer.json"
        editable_path.write_text("{}\n", encoding="utf-8")
        manifest_path = editable_path.with_name("editable-artifacts.json")
        write_json(
            manifest_path,
            [{"path": str(editable_path.relative_to(order_dir)), "role": "editable_layer_spec"}],
        )
        hybrid = run_tool(
            "tools/composite_locked_chrome.py",
            "--order-dir", str(order_dir),
            "--job-id", "test-order:slide_01",
            "--slide-no", "1",
            "--accepted-attempt", "1",
            "--variant-id", "section_test",
            "--raw-image", str(raw_path.relative_to(order_dir)),
            "--overlay-image", str(overlay_path.relative_to(order_dir)),
            "--expected-overlay-sha256", sha256_file(overlay_path),
            "--output-image", output_rel,
            "--receipt", receipt_rel,
            "--output-mode", "hybrid",
            "--editable-artifacts-json", str(manifest_path.relative_to(order_dir)),
            "--safe-box", "0", "10", "100", "50",
        )
        self.assertEqual(hybrid.returncode, 0, hybrid.stdout)
        hybrid_receipt = json.loads((order_dir / receipt_rel).read_text(encoding="utf-8"))
        self.assertEqual(hybrid_receipt["editable_artifacts"][0]["sha256"], sha256_file(editable_path))

        semitransparent = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
        ImageDraw.Draw(semitransparent).rectangle((0, 0, 99, 9), fill=(240, 80, 20, 128))
        semitransparent.save(overlay_path)
        rejected = run_tool(
            "tools/composite_locked_chrome.py",
            "--order-dir", str(order_dir),
            "--job-id", "test-order:slide_01",
            "--slide-no", "1",
            "--accepted-attempt", "1",
            "--variant-id", "section_test",
            "--raw-image", str(raw_path.relative_to(order_dir)),
            "--overlay-image", str(overlay_path.relative_to(order_dir)),
            "--expected-overlay-sha256", sha256_file(overlay_path),
            "--output-image", output_rel,
            "--receipt", receipt_rel,
            "--safe-box", "0", "10", "100", "50",
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("alpha must be binary", rejected.stdout)

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
        (order_dir / "05_production" / "origin_image" / "slide_01.png").write_bytes(b"fake-final-output")
        raw_output = order_dir / "05_production" / "slide_jobs" / "slide_01" / "attempts" / "attempt_01" / "output.png"
        raw_output.parent.mkdir(parents=True, exist_ok=True)
        raw_output.write_bytes(b"fake-raw-output")
        write_json(
            order_dir / "05_production" / "slide_jobs" / "slide_01" / "render_result.json",
            {
                "job_id": "test-order:slide_01",
                "attempt": 1,
                "slide_no": 1,
                "output_mode": "image_first",
                "status": "success",
                "output_image": "05_production/slide_jobs/slide_01/attempts/attempt_01/output.png",
                "input_images_seen": ["style_anchor.png"],
                "asset_fidelity": [],
                "style_match": "pass",
                "text_readability": "pass",
                "editable_artifacts": [],
                "blockers": [],
            },
        )
        write_json(
            order_dir / "05_production" / "slide_jobs" / "slide_01" / "finalization.json",
            {
                "job_id": "test-order:slide_01",
                "slide_no": 1,
                "output_mode": "image_first",
                "accepted_attempt": 1,
                "status": "pass",
                "raw_output_image": "05_production/slide_jobs/slide_01/attempts/attempt_01/output.png",
                "raw_output_sha256": sha256_file(raw_output),
                "final_output_image": "05_production/origin_image/slide_01.png",
                "final_output_sha256": sha256_file(order_dir / "05_production" / "origin_image" / "slide_01.png"),
                "editable_artifacts": [],
                "locked_chrome": {
                    "mode": "none",
                    "variant_id": None,
                    "active_navigation_section": None,
                    "overlay_path": None,
                    "overlay_sha256": None,
                    "applied": False,
                    "pixel_match": True,
                    "content_safe_zone_clear": True,
                },
                "finalized_at": "2026-07-06T10:30:00+08:00",
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
                        "finalization_file": "05_production/slide_jobs/slide_01/finalization.json",
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
                                "output_image": "05_production/slide_jobs/slide_01/attempts/attempt_01/output.png",
                                "failure_class": "none",
                                "repair_instructions": None,
                            }
                        ],
                        "selected_source": "05_production/origin_image/slide_01.png",
                        "final_output_image": "05_production/origin_image/slide_01.png",
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
