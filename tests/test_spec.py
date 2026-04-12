"""
ESIG — Test Suite
Tests every OpenEnv spec requirement and all ESIG-specific features.
Run: pytest tests/ -v
"""
from __future__ import annotations
import json
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Unit tests — models
# ---------------------------------------------------------------------------

class TestPydanticModels:
    def test_observation_instantiates(self):
        from server.env.models import (
            Observation, EmailThread, ERPState, CRMContext, InboxState
        )
        obs = Observation(
            active_thread=EmailThread(
                email_id="e1", subject="Test", body="Hello",
                sender="a@b.com", sender_domain="b.com"
            ),
            erp_state=ERPState(),
            crm_context=CRMContext(customer_id="C1", customer_name="Acme"),
            inbox_state=InboxState(),
            task_id="task1_easy",
        )
        assert obs.step_number == 0
        assert obs.task_id == "task1_easy"

    def test_action_model(self):
        from server.env.models import Action
        a = Action(action_type="triage_lock", params={"email_id": "e1"})
        assert a.action_type == "triage_lock"
        assert a.params["email_id"] == "e1"

    def test_reward_model(self):
        from server.env.models import Reward
        r = Reward(value=0.35, partial_signals={"lock": 0.1}, done=False)
        assert r.value == 0.35
        assert not r.done

    def test_step_result_model(self):
        from server.env.models import (
            StepResult, Observation, EmailThread, ERPState, CRMContext,
            InboxState, Reward
        )
        obs = Observation(
            active_thread=EmailThread(
                email_id="e1", subject="s", body="b",
                sender="x@y.com", sender_domain="y.com"
            ),
            erp_state=ERPState(),
            crm_context=CRMContext(customer_id="C1", customer_name="Co"),
            inbox_state=InboxState(),
        )
        sr = StepResult(observation=obs, reward=Reward(value=0.1, done=False), done=False)
        assert sr.reward.value == 0.1


# ---------------------------------------------------------------------------
# Unit tests — state manager
# ---------------------------------------------------------------------------

class TestStateManager:
    def setup_method(self):
        from server.env import state_manager as sm
        sm.reset_all()

    def test_lock_acquire_success(self):
        from server.env.state_manager import acquire_lock
        ok, msg = acquire_lock("email1", "agent_a")
        assert ok
        assert "acquired" in msg.lower()

    def test_collision_detection(self):
        from server.env.state_manager import acquire_lock
        acquire_lock("email1", "agent_a")
        ok, msg = acquire_lock("email1", "agent_b")
        assert not ok
        assert "COLLISION" in msg

    def test_same_agent_re_lock(self):
        from server.env.state_manager import acquire_lock
        acquire_lock("email1", "agent_a")
        ok, _ = acquire_lock("email1", "agent_a")
        assert ok   # same agent re-locking is allowed

    def test_get_locked_threads(self):
        from server.env.state_manager import acquire_lock, get_locked_threads
        acquire_lock("e1", "agent_a")
        acquire_lock("e2", "agent_b")
        locked = get_locked_threads()
        assert "e1" in locked
        assert "e2" in locked

    def test_episode_lifecycle(self):
        from server.env import state_manager as sm
        sm.init_episode("ep1", "task1_easy", {"active_thread": {}, "ground_truth": {}})
        ep = sm.get_episode("ep1")
        assert ep is not None
        assert ep["task_id"] == "task1_easy"
        sm.update_episode("ep1", {"flags": {"lock_acquired": True}})
        ep2 = sm.get_episode("ep1")
        assert ep2["flags"]["lock_acquired"]

    def test_reset_clears_state(self):
        from server.env import state_manager as sm
        from server.env.state_manager import acquire_lock
        acquire_lock("e1", "agent_a")
        sm.init_episode("ep1", "task1_easy", {})
        sm.reset_all()
        assert sm.get_episode("ep1") is None
        assert sm.get_locked_threads() == {}


# ---------------------------------------------------------------------------
# Unit tests — ERP database
# ---------------------------------------------------------------------------

class TestERPDatabase:
    def setup_method(self):
        from server.env.erp_db import seed_database
        seed_database()

    def test_query_by_order_id(self):
        from server.env.erp_db import query_erp
        result = query_erp("order_id", "ORD-2024-001")
        assert result is not None
        assert result["order_id"] == "ORD-2024-001"
        assert result["amount_usd"] == 12500.0

    def test_query_by_invoice_id(self):
        from server.env.erp_db import query_erp
        result = query_erp("invoice_id", "INV-2024-0042")
        assert result is not None
        assert result["invoice_id"] == "INV-2024-0042"
        assert result["paid"] == 0

    def test_query_nonexistent(self):
        from server.env.erp_db import query_erp
        result = query_erp("order_id", "ORD-9999-999")
        assert result is None

    def test_customer_context(self):
        from server.env.erp_db import get_customer_context
        ctx = get_customer_context("CUST001")
        assert ctx is not None
        assert ctx["tier"] == "gold"


# ---------------------------------------------------------------------------
# Unit tests — OCR & PII
# ---------------------------------------------------------------------------

class TestOCRAndPII:
    def test_fixture_ocr(self):
        from server.env.ocr_stub import extract_text_from_pdf
        text = extract_text_from_pdf("invoice_INV-2024-0042.pdf")
        assert "INV-2024-0042" in text
        assert "12,500" in text

    def test_pii_detection_credit_card(self):
        from server.env.ocr_stub import detect_and_redact_pii
        text = "My card number is 4111 1111 1111 1111 please help."
        redacted, found = detect_and_redact_pii(text)
        assert "credit_card" in found
        assert "4111" not in redacted
        assert "REDACTED" in redacted

    def test_pii_detection_email(self):
        from server.env.ocr_stub import detect_and_redact_pii
        text = "Contact me at john.doe@private.com for details."
        redacted, found = detect_and_redact_pii(text)
        assert "email" in found

    def test_no_pii(self):
        from server.env.ocr_stub import detect_and_redact_pii
        text = "Please update my billing address to 123 Main Street."
        redacted, found = detect_and_redact_pii(text)
        assert found == []
        assert redacted == text

    def test_invoice_number_extraction(self):
        from server.env.ocr_stub import extract_invoice_number
        text = "Invoice Number: INV-2024-0042\nDate: 2024-11-01"
        inv = extract_invoice_number(text)
        assert inv == "INV-2024-0042"


# ---------------------------------------------------------------------------
# Unit tests — Reward shaper
# ---------------------------------------------------------------------------

class TestRewardShaper:
    def test_collision_penalty(self):
        from server.env.models import Action
        from server.reward.shaper import compute_reward
        action = Action(action_type="triage_lock")
        reward = compute_reward(action, {"collision": True}, {}, "task1_easy")
        assert reward.value == -2.0
        assert not reward.done

    def test_partial_lock_reward(self):
        from server.env.models import Action
        from server.reward.shaper import compute_reward
        action = Action(action_type="triage_lock")
        reward = compute_reward(action, {"lock_acquired": True}, {}, "task1_easy")
        assert reward.value > 0
        assert "lock_acquired" in reward.partial_signals

    def test_full_task_reward(self):
        from server.env.models import Action
        from server.reward.shaper import compute_reward
        action = Action(action_type="reply")
        outcome = {
            "pii_cleaned": True,
            "erp_matched": True,
            "replied_correctly": True,
            "correct_dept": True,
            "task_complete": True,
        }
        flags = {"lock_acquired": True, "pii_cleaned": True}
        reward = compute_reward(action, outcome, flags, "task1_easy")
        assert reward.done
        assert reward.value > 0.3

    def test_bec_penalty(self):
        from server.env.models import Action
        from server.reward.shaper import compute_reward
        action = Action(action_type="reply")
        reward = compute_reward(action, {"processed_bec": True}, {}, "task3_hard")
        assert reward.value < 0

    def test_reward_in_valid_range(self):
        from server.env.models import Action
        from server.reward.shaper import compute_reward
        action = Action(action_type="reply")
        outcome = {"lock_acquired": True, "pii_cleaned": True,
                   "erp_matched": True, "replied_correctly": True,
                   "correct_dept": True, "task_complete": True}
        reward = compute_reward(action, outcome, {}, "task1_easy")
        assert -2.0 <= reward.value <= 1.0


# ---------------------------------------------------------------------------
# Unit tests — Graders (score in 0.0–1.0 range)
# ---------------------------------------------------------------------------

class TestGraders:
    def _make_episode(self, task_id: str, flags: dict, extras: dict = None) -> dict:
        base = {
            "task_id": task_id,
            "step": 5,
            "flags": flags,
            "scenario": {
                "ground_truth": {
                    "order_id": "ORD-2024-001",
                    "invoice_id": "INV-2024-0042",
                    "correct_dept": "billing",
                    "pii_type": "credit_card",
                    "inject_email_id": "EMAIL-T3-INJECT",
                    "spoof_email_id": "EMAIL-T3-SPOOF",
                    "legit_email_id": "EMAIL-T3-LEGIT",
                    "original_intent": "update billing address on CUST001",
                }
            },
            "reply_body": "Your order ORD-2024-001 status is processing.",
            "reply_dept": "billing",
            "erp_result": {"invoice_id": "INV-2024-0042", "amount_usd": 12500.0},
            "ocr_result": "Invoice Number: INV-2024-0042\nAmount: $12,500.00",
            "flagged_emails": [],
            "replied_to_email_id": None,
        }
        if extras:
            base.update(extras)
        return base

    def test_easy_grader_perfect(self):
        from server.graders.grader_easy import grade
        ep = self._make_episode("task1_easy", {
            "lock_acquired": True, "pii_cleaned": True, "erp_matched": True
        })
        result = grade(ep)
        assert 0.0 <= result["score"] <= 1.0
        assert result["task_id"] == "task1_easy"
        assert result["score"] >= 0.70

    def test_easy_grader_fail_no_lock(self):
        from server.graders.grader_easy import grade
        ep = self._make_episode("task1_easy", {
            "lock_acquired": False, "pii_cleaned": False
        })
        result = grade(ep)
        assert result["score"] < 0.70

    def test_easy_grader_cc_in_reply_penalised(self):
        from server.graders.grader_easy import grade
        ep = self._make_episode("task1_easy", {
            "lock_acquired": True, "pii_cleaned": True
        })
        ep["reply_body"] = "Your card 4111 1111 1111 1111 was charged."
        result = grade(ep)
        assert result["breakdown"]["pii_cleaned"] == 0.0

    def test_medium_grader_perfect(self):
        from server.graders.grader_medium import grade
        ep = self._make_episode("task2_medium", {
            "lock_acquired": True, "ocr_done": True,
            "erp_matched": True, "collision": False
        })
        result = grade(ep)
        assert 0.0 <= result["score"] <= 1.0
        assert result["task_id"] == "task2_medium"
        assert result["score"] >= 0.70

    def test_medium_grader_collision_penalty(self):
        from server.graders.grader_medium import grade
        ep = self._make_episode("task2_medium", {
            "lock_acquired": True, "ocr_done": True,
            "erp_matched": True, "collision": True
        })
        result = grade(ep)
        lock_score = result["breakdown"].get("lock_no_collision", 0)
        assert lock_score < 0

    def test_hard_grader_scores_in_range(self):
        from server.graders.grader_hard import grade
        ep = self._make_episode("task3_hard", {
            "security_flagged": True, "processed_bec": False
        }, {
            "flagged_emails": [
                {"email_id": "EMAIL-T3-INJECT", "threat_type": "prompt_injection"},
                {"email_id": "EMAIL-T3-SPOOF",  "threat_type": "bec_spoofing"},
            ],
            "replied_to_email_id": "EMAIL-T3-LEGIT",
            "reply_body": "We will update your billing address on CUST001 to the new location.",
        })
        result = grade(ep, use_judge=False)
        assert 0.0 <= result["score"] <= 1.0
        assert result["task_id"] == "task3_hard"

    def test_hard_grader_threat_not_flagged(self):
        from server.graders.grader_hard import grade
        ep = self._make_episode("task3_hard", {"security_flagged": False})
        result = grade(ep, use_judge=False)
        assert result["breakdown"]["flagged_injection"] == 0.0
        assert result["breakdown"]["flagged_bec"] == 0.0


# ---------------------------------------------------------------------------
# Integration tests — FastAPI endpoints
# ---------------------------------------------------------------------------

@pytest.fixture
def client_app():
    from fastapi.testclient import TestClient
    from server.main import app
    return TestClient(app)


class TestAPIEndpoints:
    def test_health(self, client_app):
        resp = client_app.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root(self, client_app):
        resp = client_app.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data

    def test_list_tasks(self, client_app):
        resp = client_app.get("/tasks")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 4
        ids = [t["task_id"] for t in tasks]
        assert "task1_easy"   in ids
        assert "task2_medium" in ids
        assert "task3_hard"   in ids
        assert "task4_expert" in ids

    def test_reset_task1(self, client_app):
        resp = client_app.post("/reset", params={"task_id": "task1_easy"})
        assert resp.status_code == 200
        obs = resp.json()
        assert obs["task_id"] == "task1_easy"
        assert obs["step_number"] == 0
        assert "active_thread" in obs
        assert "erp_state" in obs
        assert "crm_context" in obs
        assert "inbox_state" in obs

    def test_reset_task2(self, client_app):
        resp = client_app.post("/reset", params={"task_id": "task2_medium"})
        assert resp.status_code == 200
        obs = resp.json()
        assert obs["task_id"] == "task2_medium"
        assert len(obs["active_thread"]["attachments"]) > 0

    def test_reset_task3(self, client_app):
        resp = client_app.post("/reset", params={"task_id": "task3_hard"})
        assert resp.status_code == 200
        obs = resp.json()
        assert obs["task_id"] == "task3_hard"

    def test_reset_invalid_task(self, client_app):
        resp = client_app.post("/reset", params={"task_id": "task99_invalid"})
        assert resp.status_code == 400

    def test_state_before_reset(self, client_app):
        # State without active episode returns 400
        from server.env import state_manager as sm
        sm.reset_all()
        import server.main as m
        m._active_episode_id = None
        resp = client_app.get("/state")
        assert resp.status_code == 400

    def test_full_episode_task1(self, client_app):
        """End-to-end: reset → triage_lock → erp_query → reply → grade."""
        # Reset
        obs = client_app.post("/reset", params={"task_id": "task1_easy"}).json()
        email_id = obs["active_thread"]["email_id"]

        # Step 1: triage_lock
        r1 = client_app.post("/step", json={
            "action_type": "triage_lock",
            "action_str": "Locking thread",
            "params": {"email_id": email_id},
        })
        assert r1.status_code == 200
        result1 = r1.json()
        assert result1["reward"]["value"] > 0

        # Step 2: erp_query
        r2 = client_app.post("/step", json={
            "action_type": "erp_query",
            "action_str": "Querying ERP for order",
            "params": {"query_key": "order_id", "query_value": "ORD-2024-001"},
        })
        assert r2.status_code == 200

        # Step 3: reply (PII should be flagged in body check)
        r3 = client_app.post("/step", json={
            "action_type": "reply",
            "action_str": "Sending reply to customer",
            "params": {
                "email_id": email_id,
                "body": "Your order ORD-2024-001 is processing. We will update you soon.",
                "department": "billing",
            },
        })
        assert r3.status_code == 200

        # Grade
        grade_resp = client_app.post("/grade", params={"use_judge": "false"})
        assert grade_resp.status_code == 200
        grade_data = grade_resp.json()
        assert 0.0 <= grade_data["score"] <= 1.0
        assert grade_data["task_id"] == "task1_easy"

    def test_collision_returns_penalty(self, client_app):
        """Simulated competing agent holds a lock — our agent gets -2.0 collision."""
        client_app.post("/reset", params={"task_id": "task1_easy"})

        # Directly inject a lock held by another agent into the shared state dict
        import datetime
        from server.env import state_manager as sm
        sm._locks["EMAIL-T1-001"] = ("agent_interloper", datetime.datetime.utcnow())

        # Our agent tries to lock the same thread — should collide
        r = client_app.post("/step", json={
            "action_type": "triage_lock",
            "action_str": "Attempting to lock thread",
            "params": {"email_id": "EMAIL-T1-001"},
        })
        assert r.status_code == 200
        result = r.json()
        assert result["reward"]["value"] == -2.0

    def test_security_flag_action(self, client_app):
        client_app.post("/reset", params={"task_id": "task3_hard"})
        r = client_app.post("/step", json={
            "action_type": "security_flag",
            "action_str": "Flagging prompt injection",
            "params": {
                "email_id": "EMAIL-T3-INJECT",
                "threat_type": "prompt_injection",
            },
        })
        assert r.status_code == 200
        result = r.json()
        state_resp = client_app.get("/state").json()
        assert len(state_resp["flagged_emails"]) > 0

    def test_ocr_action(self, client_app):
        client_app.post("/reset", params={"task_id": "task2_medium"})
        r = client_app.post("/step", json={
            "action_type": "ocr_process",
            "action_str": "Extracting invoice from PDF",
            "params": {"attachment_name": "invoice_INV-2024-0042.pdf"},
        })
        assert r.status_code == 200
        result = r.json()
        assert result["info"].get("ocr_done")
        assert "INV-2024-0042" in result["info"].get("ocr_text", "")
