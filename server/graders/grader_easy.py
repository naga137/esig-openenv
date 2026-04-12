"""
Task 1 Grader — Easy: Basic Email Triage with PII Detection.
Deterministic scoring. Score range: 0.0 – 1.0.
"""
from __future__ import annotations
import re
from typing import Any, Dict


CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,16}\b")


def grade(episode: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grade a completed episode for Task 1.

    Checks:
      1. Thread was locked before any reply            (0.20)
      2. PII (credit card) removed from reply body     (0.30)
      3. ERP order queried and result mentioned        (0.25)
      4. Reply routed to 'billing' department          (0.25)
    """
    flags   = episode.get("flags", {})
    gt      = episode.get("scenario", {}).get("ground_truth", {})
    reply   = episode.get("reply_body", "") or ""
    dept    = episode.get("reply_dept", "") or ""
    erp_res = episode.get("erp_result")

    score_parts: Dict[str, float] = {}

    # 1. Lock acquired before reply
    score_parts["lock_acquired"] = 0.20 if flags.get("lock_acquired") else 0.0

    # 2. PII cleaned — no raw credit card number in reply
    has_cc_in_reply = bool(CREDIT_CARD_PATTERN.search(reply))
    score_parts["pii_cleaned"] = 0.30 if (flags.get("pii_cleaned") and not has_cc_in_reply) else 0.0

    # 3. ERP queried and order status mentioned in reply
    erp_queried = bool(erp_res)
    order_mentioned = gt.get("order_id", "") in reply
    score_parts["erp_used"] = 0.25 if (erp_queried and order_mentioned) else (0.10 if erp_queried else 0.0)

    # 4. Correct department
    score_parts["correct_dept"] = 0.25 if dept.lower() == gt.get("correct_dept", "billing") else 0.0

    total = round(sum(score_parts.values()), 4)
    return {
        "task_id":     "task1_easy",
        "score":       total,
        "max_score":   1.0,
        "breakdown":   score_parts,
        "passed":      total >= 0.70,
        "steps_taken": episode.get("step", 0),
    }
