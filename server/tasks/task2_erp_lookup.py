"""
Task 2 — Medium: Multi-Step ERP Lookup with OCR and Collision Avoidance.

Scenario: A customer emails with a PDF invoice. A second simulated agent
has pre-locked a DIFFERENT thread to create inbox noise. The agent must:
  1. Check state() — see the existing lock belongs to another thread (not this one)
  2. triage_lock() the correct thread
  3. ocr_process() the PDF attachment → extract invoice number
  4. erp_query() with extracted invoice number → verify payment status
  5. reply() with the verified ERP data, routed to billing
"""
from __future__ import annotations
from typing import Any, Dict
from server.env.models import EmailThread, ERPState, CRMContext, InboxState, Observation

TASK_ID = "task2_medium"
MAX_STEPS = 12

GROUND_TRUTH = {
    "email_id":          "EMAIL-T2-001",
    "attachment":        "invoice_INV-2024-0042.pdf",
    "invoice_id":        "INV-2024-0042",
    "order_id":          "ORD-2024-001",
    "customer_id":       "CUST001",
    "expected_lock":     True,
    "expected_ocr":      True,
    "expected_erp":      True,
    "correct_dept":      "billing",
    "invoice_amount":    12500.0,
    "invoice_paid":      False,
}


def generate_scenario(episode_id: str) -> Dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "episode_id": episode_id,
        "ground_truth": GROUND_TRUTH,
        "active_thread": {
            "email_id": GROUND_TRUTH["email_id"],
            "subject": "Invoice INV-2024-0042 — payment confirmation needed",
            "body": (
                "Dear Billing Team,\n\n"
                "Please find attached our invoice INV-2024-0042 for the Enterprise SaaS Plan. "
                "We need confirmation that this invoice has been received and when payment "
                "will be processed.\n\n"
                "Please see the attached PDF for full details.\n\n"
                "Best regards,\nJames Miller\nAccounts Payable, Acme Corp"
            ),
            "sender": "james.miller@acme.com",
            "sender_domain": "acme.com",
            "attachments": ["invoice_INV-2024-0042.pdf"],
            "history": [],
            "is_adversarial": False,
        },
        "erp_records": {
            "orders": [
                {"order_id": "ORD-2024-001", "customer_id": "CUST001",
                 "product": "Enterprise SaaS Plan", "amount_usd": 12500.0,
                 "status": "processing", "created_date": "2024-11-01"}
            ],
            "invoices": [
                {"invoice_id": "INV-2024-0042", "customer_id": "CUST001",
                 "order_id": "ORD-2024-001", "amount_usd": 12500.0,
                 "due_date": "2024-12-01", "paid": 0}
            ],
        },
        "crm": {
            "customer_id": "CUST001",
            "customer_name": "Acme Corp",
            "customer_tier": "gold",
            "open_tickets": 0,
            "sentiment_score": 0.85,
            "account_value_usd": 150000.0,
        },
        # Pre-existing lock on a DIFFERENT thread — inbox noise
        "pre_existing_locks": {
            "EMAIL-OTHER-099": "agent_secondary",
        },
    }


def build_initial_observation(scenario: Dict[str, Any], episode_id: str) -> Observation:
    locked = dict(scenario.get("pre_existing_locks", {}))

    return Observation(
        active_thread=EmailThread(**scenario["active_thread"]),
        erp_state=ERPState(
            orders=scenario["erp_records"]["orders"],
            invoices=scenario["erp_records"]["invoices"],
        ),
        crm_context=CRMContext(**scenario["crm"]),
        inbox_state=InboxState(
            locked_threads=locked,
            total_emails_pending=5,
            current_agent_id=episode_id,
        ),
        step_number=0,
        task_id=TASK_ID,
        max_steps=MAX_STEPS,
    )
