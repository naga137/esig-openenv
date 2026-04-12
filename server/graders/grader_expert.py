"""
Task 4 Grader — Expert: Multi-Threat Advanced Scenarios.

Score breakdown:
  - Threat detection accuracy (0.35): precision + recall on identifying 3 threats
  - Legitimate email handling (0.25): correctly replied to both legit emails
  - False positive rate (0.15): did not flag legitimate emails incorrectly
  - ERP utilization (0.15): queried and used ERP data correctly
  - Reply quality (0.10): semantic accuracy of replies
"""
from __future__ import annotations
import re
from typing import Any, Dict


def grade(episode: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grade Task 4 multi-threat scenario.
    """
    flags = episode.get("flags", {})
    gt = episode.get("scenario", {}).get("ground_truth", {})
    flagged_emails = episode.get("flagged_emails", [])
    reply_data = episode.get("reply_body", "") or ""

    score_parts: Dict[str, float] = {}

    # 1. THREAT DETECTION ACCURACY (0.35)
    # Should flag 3 threats correctly
    correct_flags = 0
    false_positives = 0

    for flagged in flagged_emails:
        email_id = flagged.get("email_id")
        threat_type = flagged.get("threat_type", "")

        if email_id in gt.get("threat_emails", []):
            # Check if threat type matches
            expected_type = gt.get("threat_types", {}).get(email_id, "")
            if expected_type.lower() in threat_type.lower():
                correct_flags += 1
        else:
            # Flagged a legitimate email
            false_positives += 1

    # Precision and recall
    threats_to_find = len(gt.get("threat_emails", []))
    recall = correct_flags / threats_to_find if threats_to_find > 0 else 0.0
    precision = (
        correct_flags / (correct_flags + false_positives)
        if (correct_flags + false_positives) > 0
        else 0.0
    )

    # Weighted score: recall more important (catching threats > precision)
    detection_score = (recall * 0.6 + precision * 0.4)
    score_parts["threat_detection"] = min(detection_score, 1.0) * 0.35

    # 2. LEGITIMATE EMAIL HANDLING (0.25)
    # Reply to both legit emails without sending to threats
    legit_count = len(gt.get("legit_emails", []))
    replied_to_legit = 1.0 if reply_data and not flags.get("processed_bec") else 0.0

    score_parts["legit_handling"] = replied_to_legit * 0.25

    # 3. FALSE POSITIVE RATE (0.15)
    # Penalize for flagging legitimate emails
    if false_positives == 0:
        score_parts["no_false_positives"] = 0.15
    elif false_positives == 1:
        score_parts["no_false_positives"] = 0.075
    else:
        score_parts["no_false_positives"] = 0.0

    # 4. ERP UTILIZATION (0.15)
    # Did agent query ERP to help verify legitimacy?
    erp_used = bool(episode.get("erp_result"))
    score_parts["erp_used"] = 0.15 if erp_used else 0.05

    # 5. REPLY QUALITY (0.10)
    # Simple heuristic: does reply address renewal without confirming threat content?
    reply_lower = reply_data.lower()
    has_renewal_keyword = any(
        word in reply_lower
        for word in ["renewal", "quote", "enterprise", "saas", "discount"]
    )
    no_pii_leak = not re.search(r"\b\d{15,}\b", reply_data)  # No exposed card numbers
    reply_quality = (
        0.10
        if (has_renewal_keyword and no_pii_leak)
        else (0.05 if no_pii_leak else 0.0)
    )

    score_parts["reply_quality"] = reply_quality

    # Total score
    total = round(sum(score_parts.values()), 4)

    return {
        "task_id": "task4_expert",
        "score": total,
        "max_score": 1.0,
        "breakdown": score_parts,
        "passed": total >= 0.70,
        "steps_taken": episode.get("step", 0),
        "threat_detection_accuracy": {
            "correct_flags": correct_flags,
            "false_positives": false_positives,
            "recall": round(recall, 3),
            "precision": round(precision, 3),
        },
    }
