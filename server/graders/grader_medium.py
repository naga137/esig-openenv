"""
Task 2 Grader — Medium: Multi-Step ERP Lookup with OCR and Collision Avoidance.
Deterministic scoring. Score range: 0.0 – 1.0.
"""
from __future__ import annotations
from typing import Any, Dict


def grade(episode: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grade a completed episode for Task 2.

    Checks:
      1. Lock acquired (and no collision triggered)    (0.15)
      2. OCR performed on correct attachment           (0.20)
      3. Invoice number extracted correctly            (0.20)
      4. ERP queried with correct invoice_id           (0.20)
      5. Reply includes correct amount & due_date      (0.25)
    """
    flags   = episode.get("flags", {})
    gt      = episode.get("scenario", {}).get("ground_truth", {})
    reply   = episode.get("reply_body", "") or ""
    dept    = episode.get("reply_dept", "") or ""
    erp_res = episode.get("erp_result") or {}
    ocr_res = episode.get("ocr_result", "") or ""

    score_parts: Dict[str, float] = {}

    # 1. Lock acquired, no collision
    if flags.get("lock_acquired") and not flags.get("collision"):
        score_parts["lock_no_collision"] = 0.15
    elif flags.get("collision"):
        score_parts["lock_no_collision"] = -0.10   # penalty for collision
    else:
        score_parts["lock_no_collision"] = 0.0

    # 2. OCR performed
    score_parts["ocr_done"] = 0.20 if flags.get("ocr_done") else 0.0

    # 3. Invoice number extracted from OCR
    expected_inv = gt.get("invoice_id", "INV-2024-0042")
    inv_in_ocr = expected_inv in ocr_res
    score_parts["invoice_extracted"] = 0.20 if inv_in_ocr else 0.0

    # 4. ERP queried correctly
    erp_matched = (
        erp_res.get("invoice_id") == expected_inv
        or flags.get("erp_matched")
    )
    score_parts["erp_queried"] = 0.20 if erp_matched else 0.0

    # 5. Reply contains correct financial data
    reply_lower = reply.lower()
    amount_ok   = "12,500" in reply or "12500" in reply
    due_ok      = "2024-12-01" in reply or "december 1" in reply_lower
    dept_ok     = dept.lower() == gt.get("correct_dept", "billing")
    score_parts["reply_correct"] = (
        0.25 if (amount_ok and due_ok and dept_ok)
        else 0.15 if (amount_ok or due_ok) and dept_ok
        else 0.0
    )

    total = round(max(0.0, sum(score_parts.values())), 4)
    return {
        "task_id":     "task2_medium",
        "score":       total,
        "max_score":   1.0,
        "breakdown":   score_parts,
        "passed":      total >= 0.60,
        "steps_taken": episode.get("step", 0),
    }
