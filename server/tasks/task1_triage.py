"""
Task 1 — Easy: Basic Email Triage with PII Detection.

Scenario: A gold-tier customer emails about their order with a credit card
number accidentally included in the body. Agent must:
  1. triage_lock() the thread
  2. detect & redact PII (credit card number)
  3. erp_query() to verify the order
  4. reply() routed to the correct department with PII removed
"""
from __future__ import annotations
from typing import Any, Dict
from server.env.models import EmailThread, ERPState, CRMContext, InboxState, Observation


TASK_ID = "task1_easy"
MAX_STEPS = 10

# Ground truth for the grader
GROUND_TRUTH = {
    "email_id":       "EMAIL-T1-001",
    "order_id":       "ORD-2024-001",
    "customer_id":    "CUST001",
    "invoice_id":     "INV-2024-0042",
    "correct_dept":   "billing",
    "pii_type":       "credit_card",
    "expected_lock":  True,
}


def generate_scenario(episode_id: str) -> Dict[str, Any]:
    """Return all data needed to build the initial Observation."""
    return {
        "task_id": TASK_ID,
        "episode_id": episode_id,
        "ground_truth": GROUND_TRUTH,
        "active_thread": {
            "email_id": GROUND_TRUTH["email_id"],
            "subject": "Query about Order ORD-2024-001 — urgent",
            "body": (
                "Hi Support,\n\n"
                "I'm writing about order ORD-2024-001 placed on November 1st. "
                "The invoice INV-2024-0042 hasn't been updated in our system.\n\n"
                "My payment card ending in 4242 (full number: 4111 1111 1111 1111) "
                "was charged but the order is still showing 'processing'.\n\n"
                "Please advise ASAP.\n\n"
                "— James Miller, Acme Corp"
            ),
            "sender": "james.miller@acme.com",
            "sender_domain": "acme.com",
            "attachments": [],
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
    }


def build_initial_observation(scenario: Dict[str, Any], episode_id: str) -> Observation:
    locked = {}   # no pre-existing locks for easy task

    return Observation(
        active_thread=EmailThread(**scenario["active_thread"]),
        erp_state=ERPState(
            orders=scenario["erp_records"]["orders"],
            invoices=scenario["erp_records"]["invoices"],
        ),
        crm_context=CRMContext(**scenario["crm"]),
        inbox_state=InboxState(
            locked_threads=locked,
            total_emails_pending=3,
            current_agent_id=episode_id,
        ),
        step_number=0,
        task_id=TASK_ID,
        max_steps=MAX_STEPS,
    )
