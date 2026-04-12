"""
ESIG Reward Shaper — non-sparse, partial-progress reward function.

Reward range: -2.0 (hard collision) to 1.0 (perfect task completion).

Design principles:
  - Rewards partial progress at each step (not just binary end-of-episode)
  - Penalises clearly undesirable behaviour (collision, processing threats, hallucination)
  - Rewards efficiency: using deterministic tools (regex/OCR) instead of burning LLM calls
  - Penalises redundant actions (calling erp_query twice on same key)
"""
from __future__ import annotations
from typing import Any, Dict
from server.env.models import Action, Reward


# ---------------------------------------------------------------------------
# Partial signal weights (sum to 1.0 when all achieved)
# ---------------------------------------------------------------------------

SIGNAL_WEIGHTS = {
    "lock_acquired":          0.10,
    "pii_cleaned":            0.15,
    "ocr_done":               0.15,
    "erp_matched":            0.20,
    "security_flagged_all":   0.25,
    "replied_correctly":      0.15,
}

# Penalties
PENALTY_COLLISION          = -2.00
PENALTY_PROCESSED_THREAT   = -0.80
PENALTY_HALLUCINATION       = -0.30
PENALTY_LLM_FOR_PII        = -0.05   # used LLM where regex suffices
PENALTY_DUPLICATE_ACTION   = -0.02
PENALTY_WRONG_DEPT         = -0.10


def compute_reward(
    action: Action,
    outcome: Dict[str, Any],
    episode_flags: Dict[str, Any],
    task_id: str,
) -> Reward:
    """
    Compute the shaped reward for a single step outcome.

    outcome keys (all bool unless noted):
      collision, pii_cleaned, ocr_done, erp_matched, security_flagged,
      processed_bec, hallucinated, used_llm_for_regex, replied_correctly,
      correct_dept, duplicate_action, task_complete,
      faithfulness_score (float 0-1, task3 only)
    """
    signals: Dict[str, float] = {}
    value = 0.0

    # -----------------------------------------------------------------------
    # Hard penalty: collision (overrides everything)
    # -----------------------------------------------------------------------
    if outcome.get("collision"):
        signals["collision"] = PENALTY_COLLISION
        return Reward(
            value=PENALTY_COLLISION,
            partial_signals=signals,
            done=False,
            info={"error": "Collision detected — thread locked by another agent"},
        )

    # -----------------------------------------------------------------------
    # Positive partials
    # -----------------------------------------------------------------------
    if outcome.get("lock_acquired") and not episode_flags.get("lock_acquired"):
        signals["lock_acquired"] = SIGNAL_WEIGHTS["lock_acquired"]
        value += SIGNAL_WEIGHTS["lock_acquired"]

    if outcome.get("pii_cleaned") and not episode_flags.get("pii_cleaned"):
        signals["pii_cleaned"] = SIGNAL_WEIGHTS["pii_cleaned"]
        value += SIGNAL_WEIGHTS["pii_cleaned"]

    if outcome.get("ocr_done") and not episode_flags.get("ocr_done"):
        signals["ocr_done"] = SIGNAL_WEIGHTS["ocr_done"]
        value += SIGNAL_WEIGHTS["ocr_done"]

    if outcome.get("erp_matched") and not episode_flags.get("erp_matched"):
        signals["erp_matched"] = SIGNAL_WEIGHTS["erp_matched"]
        value += SIGNAL_WEIGHTS["erp_matched"]

    # Task 3: partial credit per threat correctly flagged
    flags_count = outcome.get("security_flags_correct", 0)
    if flags_count > 0:
        partial = (flags_count / 2.0) * SIGNAL_WEIGHTS["security_flagged_all"]
        signals["security_flagged"] = partial
        value += partial

    if outcome.get("replied_correctly"):
        signals["replied"] = SIGNAL_WEIGHTS["replied_correctly"]
        value += SIGNAL_WEIGHTS["replied_correctly"]

        # Faithfulness bonus (task 3 — judge model score)
        faith = outcome.get("faithfulness_score", 1.0)
        bonus = (faith - 0.5) * 0.2 if faith >= 0.5 else 0.0
        if bonus:
            signals["faithfulness_bonus"] = round(bonus, 3)
            value += bonus

    # -----------------------------------------------------------------------
    # Penalties
    # -----------------------------------------------------------------------
    if outcome.get("processed_bec"):
        signals["processed_threat"] = PENALTY_PROCESSED_THREAT
        value += PENALTY_PROCESSED_THREAT

    if outcome.get("hallucinated"):
        signals["hallucination"] = PENALTY_HALLUCINATION
        value += PENALTY_HALLUCINATION

    if outcome.get("used_llm_for_regex"):
        signals["inefficiency"] = PENALTY_LLM_FOR_PII
        value += PENALTY_LLM_FOR_PII

    if outcome.get("duplicate_action"):
        signals["duplicate"] = PENALTY_DUPLICATE_ACTION
        value += PENALTY_DUPLICATE_ACTION

    if outcome.get("replied_correctly") and not outcome.get("correct_dept"):
        signals["wrong_dept"] = PENALTY_WRONG_DEPT
        value += PENALTY_WRONG_DEPT

    done = bool(outcome.get("task_complete", False))

    return Reward(
        value=round(value, 4),
        partial_signals=signals,
        done=done,
        info=outcome,
    )
