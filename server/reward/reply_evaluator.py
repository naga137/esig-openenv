"""
Reply Quality Evaluator — uses OpenAI to assess reply faithfulness and quality.

Metrics:
  - Faithfulness (0.0-1.0): Does reply accurately reflect customer intent?
  - Hallucination (0.0-1.0): Does reply invent facts not in ERP/context?
  - Tone appropriateness (0.0-1.0): Is tone professional/correct for tier?
  - Completeness (0.0-1.0): Does reply address all customer concerns?
  - Security posture (0.0-1.0): Does reply avoid revealing sensitive info?
"""
from __future__ import annotations
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass
import json

# Only import if available
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


@dataclass
class ReplyQualityScore:
    """Structured reply quality evaluation."""
    faithfulness: float  # 0.0-1.0 (does it match original intent?)
    hallucination: float  # 0.0-1.0 (invents facts?)
    tone_appropriateness: float  # 0.0-1.0
    completeness: float  # 0.0-1.0 (addresses all concerns?)
    security_posture: float  # 0.0-1.0 (no data leaks?)
    overall_score: float  # 0.0-1.0 (weighted average)
    reasoning: str
    flags: list[str]  # ["hallucination", "data_leak", "tone_mismatch", etc]


def evaluate_reply_with_llm(
    original_email: str,
    agent_reply: str,
    erp_context: Dict[str, Any],
    crm_context: Dict[str, Any],
    ground_truth: Dict[str, Any],
    task_id: str = "task1_easy",
) -> ReplyQualityScore:
    """
    Use OpenAI GPT-4 to evaluate reply quality.

    Args:
        original_email: Customer's original email body
        agent_reply: Agent's reply
        erp_context: ERP state (orders, invoices)
        crm_context: Customer info (tier, sentiment, etc)
        ground_truth: Expected/desired answer
        task_id: Task context for scoring

    Returns:
        ReplyQualityScore with detailed breakdown
    """
    if not HAS_OPENAI:
        # Fallback to heuristic evaluation
        return _evaluate_reply_heuristic(
            original_email, agent_reply, erp_context, crm_context, ground_truth
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _evaluate_reply_heuristic(
            original_email, agent_reply, erp_context, crm_context, ground_truth
        )

    client = openai.OpenAI(api_key=api_key)

    # Construct evaluation prompt
    evaluation_prompt = f"""
You are an expert evaluator of customer support replies in an enterprise email system.

TASK: Evaluate the quality and faithfulness of a support reply.

ORIGINAL CUSTOMER EMAIL:
{original_email}

AGENT'S REPLY:
{agent_reply}

AVAILABLE CONTEXT:
ERP (Orders/Invoices): {json.dumps(erp_context, default=str)}
Customer Info: {json.dumps(crm_context, default=str)}
Ground Truth (Ideal Response): {ground_truth}

EVALUATE on these metrics (0.0 = poor, 1.0 = excellent):

1. **Faithfulness (0.0-1.0)**: Does the reply accurately reflect the original customer intent and problem?
   - 1.0: Directly addresses core issue with accurate understanding
   - 0.5: Partially addresses the intent but misses key elements
   - 0.0: Completely misunderstands or ignores the customer's request

2. **Hallucination (0.0-1.0)**: Does the reply invent facts not supported by ERP or context?
   - 1.0: All facts are verifiable from provided context
   - 0.5: Minor unsupported claims (order numbers, dates, etc.)
   - 0.0: Extensive fabrication of information

3. **Tone Appropriateness (0.0-1.0)**: Is the tone suitable for the customer tier and context?
   - 1.0: Professional, empathetic, tier-appropriate
   - 0.5: Generally professional but slightly off-tone
   - 0.0: Inappropriate, dismissive, or hostile

4. **Completeness (0.0-1.0)**: Does the reply address ALL customer concerns?
   - 1.0: All issues addressed with solutions
   - 0.5: Addresses main issue but misses secondary concerns
   - 0.0: Ignores most customer concerns

5. **Security Posture (0.0-1.0)**: Does the reply avoid revealing sensitive information?
   - 1.0: No sensitive data (PII, card numbers, credentials) exposed
   - 0.5: Minor exposure of non-critical info
   - 0.0: Major data leaks (full card numbers, passwords, etc.)

RESPOND in JSON format ONLY:
{{
    "faithfulness": 0.85,
    "hallucination": 0.9,
    "tone_appropriateness": 0.8,
    "completeness": 0.75,
    "security_posture": 1.0,
    "overall_score": 0.86,
    "reasoning": "Reply accurately addresses the customer's concern about invoice status...",
    "flags": ["minor_tone_issue"],
    "suggestions": "Consider mentioning timeline for resolution..."
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert evaluator of customer support quality. Always respond in valid JSON.",
                },
                {"role": "user", "content": evaluation_prompt},
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)

        return ReplyQualityScore(
            faithfulness=float(result_json.get("faithfulness", 0.5)),
            hallucination=float(result_json.get("hallucination", 0.5)),
            tone_appropriateness=float(result_json.get("tone_appropriateness", 0.5)),
            completeness=float(result_json.get("completeness", 0.5)),
            security_posture=float(result_json.get("security_posture", 0.5)),
            overall_score=float(result_json.get("overall_score", 0.5)),
            reasoning=result_json.get("reasoning", ""),
            flags=result_json.get("flags", []),
        )

    except Exception as e:
        print(f"LLM evaluation error: {e}")
        return _evaluate_reply_heuristic(
            original_email, agent_reply, erp_context, crm_context, ground_truth
        )


def _evaluate_reply_heuristic(
    original_email: str,
    agent_reply: str,
    erp_context: Dict[str, Any],
    crm_context: Dict[str, Any],
    ground_truth: Dict[str, Any],
) -> ReplyQualityScore:
    """
    Fallback heuristic evaluation (when OpenAI not available).
    Uses keyword matching, length, and simple rules.
    """
    flags = []
    scores = {}

    # 1. Faithfulness: check if reply addresses original concerns
    original_lower = original_email.lower()
    reply_lower = agent_reply.lower()

    # Extract key terms from original
    concern_keywords = []
    for keyword in ["order", "invoice", "payment", "status", "billing", "account"]:
        if keyword in original_lower:
            concern_keywords.append(keyword)

    matched_keywords = sum(1 for kw in concern_keywords if kw in reply_lower)
    scores["faithfulness"] = min(0.3 + (matched_keywords * 0.2), 1.0)

    # 2. Hallucination: check for fabricated data
    # Look for card numbers, suspicious patterns
    import re

    card_pattern = r"\b(?:\d[ -]?){13,16}\b"
    if re.search(card_pattern, agent_reply):
        scores["hallucination"] = 0.2
        flags.append("card_number_exposed")
    else:
        scores["hallucination"] = 0.9

    # 3. Tone appropriateness
    tone_score = 0.7  # Default neutral
    if "appreciate" in reply_lower or "thank" in reply_lower:
        tone_score = 0.85
    if "unfortunately" in reply_lower or "unfortunately" in reply_lower:
        tone_score = 0.8
    if any(w in reply_lower for w in ["idiot", "stupid", "wrong"]):
        tone_score = 0.2
        flags.append("inappropriate_tone")

    scores["tone_appropriateness"] = tone_score

    # 4. Completeness: check reply length and structure
    if len(agent_reply.split()) < 10:
        scores["completeness"] = 0.3
        flags.append("too_short")
    elif len(agent_reply.split()) > 100:
        scores["completeness"] = 0.8
    else:
        scores["completeness"] = 0.65

    # 5. Security posture: check for data leaks
    pii_patterns = {
        "ssn": r"\d{3}-\d{2}-\d{4}",
        "credit_card": r"\b(?:\d[ -]?){13,16}\b",
        "password": r"password\s*=|pwd\s*=",
    }

    security_score = 1.0
    for pii_type, pattern in pii_patterns.items():
        if re.search(pattern, agent_reply, re.IGNORECASE):
            security_score -= 0.3
            flags.append(f"pii_leak_{pii_type}")

    scores["security_posture"] = max(security_score, 0.1)

    # Overall score (weighted average)
    weights = {
        "faithfulness": 0.25,
        "hallucination": 0.20,
        "tone_appropriateness": 0.15,
        "completeness": 0.20,
        "security_posture": 0.20,
    }

    overall = sum(scores.get(k, 0.5) * v for k, v in weights.items())

    return ReplyQualityScore(
        faithfulness=scores.get("faithfulness", 0.5),
        hallucination=scores.get("hallucination", 0.5),
        tone_appropriateness=scores.get("tone_appropriateness", 0.5),
        completeness=scores.get("completeness", 0.5),
        security_posture=scores.get("security_posture", 0.5),
        overall_score=min(overall, 1.0),
        reasoning="Heuristic evaluation (OpenAI not available)",
        flags=flags,
    )


def evaluate_multiple_replies(
    original_email: str,
    candidate_replies: list[str],
    erp_context: Dict[str, Any],
    crm_context: Dict[str, Any],
    ground_truth: Dict[str, Any],
) -> list[ReplyQualityScore]:
    """Evaluate multiple candidate replies and rank them."""
    scores = []
    for reply in candidate_replies:
        score = evaluate_reply_with_llm(
            original_email, reply, erp_context, crm_context, ground_truth
        )
        scores.append(score)

    return sorted(scores, key=lambda x: x.overall_score, reverse=True)
