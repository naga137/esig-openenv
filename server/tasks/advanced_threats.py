"""
Advanced Threat Types for ESIG — beyond basic BEC/prompt injection.

Threat Types:
  1. Credential Theft — phishing for account credentials
  2. Invoice Fraud — fraudulent invoice with payment misdirection
  3. CEO Fraud (Sophisticated) — social engineering with domain research
  4. Credential Harvesting — multi-step attack with fake login links
  5. Deepfake Scenario — audio/video deepfake impersonation claims
  6. Vendor Impersonation — sophisticated vendor account takeover
  7. Compliance Violation — requests that break regulatory requirements
"""
from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass
import re


@dataclass
class ThreatCharacteristics:
    """Common indicators of a specific threat."""
    keywords: List[str]
    sender_patterns: List[str]
    domain_patterns: List[str]
    urgency_level: str  # "low", "medium", "high", "critical"
    sophistication: str  # "basic", "intermediate", "advanced", "expert"
    detection_difficulty: str  # "trivial", "easy", "medium", "hard"


# ===========================================================================
# Threat Type Registry
# ===========================================================================

THREAT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "credential_theft": {
        "name": "Credential Theft (Phishing)",
        "description": "Attacker requests user credentials via fake login portal or social engineering.",
        "difficulty_level": "medium",
        "characteristics": ThreatCharacteristics(
            keywords=["verify account", "confirm identity", "update credentials", "reset password", "security alert"],
            sender_patterns=["noreply@", "support@", "security@", "no-reply@"],
            domain_patterns=["domain-lookalike.com", "domains with typo", "free email provider pretending to be corporate"],
            urgency_level="high",
            sophistication="intermediate",
            detection_difficulty="easy",
        ),
        "email_templates": [
            {
                "subject": "URGENT: Verify Your Account - Security Alert",
                "body_template": "Your account has been flagged for suspicious activity. Please verify your credentials at: [FAKE_LINK] within 24 hours to avoid account suspension.",
                "threat_indicators": ["fake_link", "urgency", "account_verification"],
            },
            {
                "subject": "Action Required: Confirm Your Identity",
                "body_template": "Click here to confirm your email and password: [FAKE_PORTAL]. This is required for corporate compliance.",
                "threat_indicators": ["fake_portal", "compliance_claim"],
            },
        ],
    },

    "invoice_fraud": {
        "name": "Invoice Fraud (Payment Misdirection)",
        "description": "Fraudulent invoice with subtle differences directing payment to attacker's account.",
        "difficulty_level": "medium",
        "characteristics": ThreatCharacteristics(
            keywords=["invoice", "payment", "wire transfer", "remittance", "account details", "banking information"],
            sender_patterns=["accounts@", "billing@", "finance@", "vendor-related"],
            domain_patterns=["legitimate-vendor.com vs legitim ate-vendor.com", "vendor.co vs vendor.com"],
            urgency_level="high",
            sophistication="intermediate",
            detection_difficulty="medium",
        ),
        "email_templates": [
            {
                "subject": "Invoice #INV-2024-5432 - Payment Required",
                "body_template": "Please remit payment of $15,000 to our NEW banking details: [ATTACKER_ACCOUNT]. This invoice is for [PRODUCT/SERVICE].",
                "threat_indicators": ["payment_redirect", "account_change", "invoice_spoofing"],
            },
        ],
    },

    "ceo_fraud_sophisticated": {
        "name": "CEO Fraud (Sophisticated/Spear Phishing)",
        "description": "Highly researched CEO/executive impersonation with company context, urgency, and emotional manipulation.",
        "difficulty_level": "hard",
        "characteristics": ThreatCharacteristics(
            keywords=["urgent", "confidential", "wire transfer", "ACH", "immediate action", "CEO", "CFO"],
            sender_patterns=["ceo@", "cfo@", "executive@", "look-alike domain", "typosquatted domain"],
            domain_patterns=["g00gle.com vs google.com", "gmai1.com vs gmail.com", "acmee.com vs acme.com"],
            urgency_level="critical",
            sophistication="advanced",
            detection_difficulty="hard",
        ),
        "email_templates": [
            {
                "subject": "URGENT - Confidential Wire Transfer Required",
                "body_template": """
Hi [RECIPIENT],

I need you to process a confidential wire transfer immediately for a deal we're closing today.

Wire $250,000 to: [ATTACKER_ACCOUNT]
Account Name: [FAKE_VENDOR_NAME]
Bank: [BANK_DETAILS]

This is time-sensitive and confidential. Do not discuss with anyone else.

Best,
[CEO_NAME]
                """,
                "threat_indicators": ["massive_urgency", "confidentiality_claim", "no_verification", "large_amount"],
            },
        ],
    },

    "credential_harvesting_multi_step": {
        "name": "Credential Harvesting (Multi-Step Attack)",
        "description": "Multi-step social engineering: initial contact → fake portal → secondary verification → data theft.",
        "difficulty_level": "hard",
        "characteristics": ThreatCharacteristics(
            keywords=["verify", "confirm", "authenticate", "login", "MFA", "two-factor"],
            sender_patterns=["it-support@", "admin@", "security@"],
            domain_patterns=["fake_domain_variation"],
            urgency_level="high",
            sophistication="advanced",
            detection_difficulty="hard",
        ),
        "email_templates": [
            {
                "subject": "Required: Update Your MFA Settings",
                "body_template": "Please update your multi-factor authentication settings by [DATE]. Click [LINK] and enter your credentials to proceed.",
                "threat_indicators": ["mfa_pretext", "fake_link", "credential_request"],
            },
        ],
    },

    "deepfake_impersonation": {
        "name": "Deepfake Impersonation (Video/Audio Claim)",
        "description": "Attacker claims to have deepfake videos/audio of executive and demands payment or action.",
        "difficulty_level": "hard",
        "characteristics": ThreatCharacteristics(
            keywords=["deepfake", "video", "audio", "compromised", "blackmail", "extortion", "reputational damage"],
            sender_patterns=["anonymous-remailer", "protonmail", "encrypted"],
            domain_patterns=["anonymous_services"],
            urgency_level="critical",
            sophistication="advanced",
            detection_difficulty="hard",
        ),
        "email_templates": [
            {
                "subject": "CONFIDENTIAL: Compromising Material - Action Required",
                "body_template": "We have deepfake video of [EXECUTIVE] in compromising situation. Wire $50,000 to [ACCOUNT] by [DATE] or we release it to media.",
                "threat_indicators": ["extortion", "deepfake_claim", "reputational_threat"],
            },
        ],
    },

    "vendor_account_takeover": {
        "name": "Vendor Account Takeover (Supply Chain Attack)",
        "description": "Compromised vendor account sending fraudulent invoices/requests through legitimate vendor infrastructure.",
        "difficulty_level": "hard",
        "characteristics": ThreatCharacteristics(
            keywords=["invoice", "order", "shipment", "delivery", "purchase order", "account"],
            sender_patterns=["legitimate-vendor@legitimatedomain.com but from attacker IP"],
            domain_patterns=["legitimate_domain_but_compromised"],
            urgency_level="medium",
            sophistication="expert",
            detection_difficulty="hard",
        ),
        "email_templates": [
            {
                "subject": "Invoice for Shipment #SHIP-12345",
                "body_template": "Your recent order has shipped. Please process payment of $45,000 to our NEW account: [ATTACKER_ACCOUNT]. Reference PO: [PO].",
                "threat_indicators": ["account_change", "legitimate_pretext", "supply_chain_attack"],
            },
        ],
    },

    "compliance_violation_request": {
        "name": "Compliance Violation (Regulatory Breach Request)",
        "description": "Request to process transactions or access data in violation of GDPR, PCI-DSS, or other compliance standards.",
        "difficulty_level": "medium",
        "characteristics": ThreatCharacteristics(
            keywords=["bypass", "override", "exception", "compliance", "audit", "exception request"],
            sender_patterns=["internal-sounding", "manager@", "director@"],
            domain_patterns=["internal_or_spoofed"],
            urgency_level="high",
            sophistication="intermediate",
            detection_difficulty="medium",
        ),
        "email_templates": [
            {
                "subject": "Exception Request: PCI-DSS Override for Customer XYZ",
                "body_template": "We need to process credit cards directly in this system for customer XYZ, bypassing the secure vault. This is a special request from management.",
                "threat_indicators": ["compliance_bypass", "security_override"],
            },
        ],
    },
}


def get_threat_by_type(threat_type: str) -> Dict[str, Any]:
    """Retrieve threat definition by type."""
    return THREAT_REGISTRY.get(threat_type, {})


def detect_threat(email_body: str, sender_domain: str, subject: str) -> List[Dict[str, Any]]:
    """
    Heuristic threat detection (simplified signature matching).
    Returns list of detected threats with confidence scores.
    
    In production, this would use ML classification.
    """
    detected = []

    # Normalize
    body_lower = email_body.lower()
    domain_lower = sender_domain.lower()
    subject_lower = subject.lower()

    for threat_type, threat_data in THREAT_REGISTRY.items():
        characteristics = threat_data["characteristics"]
        score = 0.0

        # Keyword matching
        keyword_matches = sum(1 for kw in characteristics.keywords if kw in body_lower or kw in subject_lower)
        score += min(keyword_matches * 0.15, 0.40)

        # Sender pattern matching
        if any(pattern in sender_domain for pattern in ["noreply", "no-reply", "support"]):
            if threat_type in ["credential_theft", "phishing"]:
                score += 0.20

        # Domain spoofing detection (simple Levenshtein-like check)
        if _looks_like_spoofed_domain(domain_lower):
            score += 0.30

        # Urgency markers
        urgency_markers = ["urgent", "immediately", "within 24 hours", "asap", "critical"]
        if any(marker in body_lower for marker in urgency_markers):
            if characteristics.urgency_level in ["high", "critical"]:
                score += 0.15

        if score >= 0.40:  # Threshold for detection
            detected.append({
                "threat_type": threat_type,
                "threat_name": threat_data["name"],
                "confidence_score": min(score, 1.0),
                "difficulty": threat_data["difficulty_level"],
            })

    return detected


def _looks_like_spoofed_domain(domain: str) -> bool:
    """Simple heuristic to detect domain spoofing (typosquatting, lookalike)."""
    # Common typosquats: g00gle (zero), gmai1 (one), acmee (double e)
    suspicious_patterns = [
        r'\d' in domain and 'gmail' in domain,  # gmai1.com
        r'0' in domain and 'google' in domain,  # g00gle.com
        domain.count('e') > 2,  # acmee.com vs acme.com
        domain.count('o') > 2,
        len(domain) > 30,  # unusually long
    ]
    return any(suspicious_patterns)


def get_threat_difficulty_score(threat_type: str) -> float:
    """Get normalized difficulty score (0.0 = trivial, 1.0 = expert)."""
    difficulty_map = {
        "trivial": 0.1,
        "easy": 0.3,
        "medium": 0.5,
        "hard": 0.8,
    }
    threat = get_threat_by_type(threat_type)
    return difficulty_map.get(threat.get("characteristics", {}).difficulty, 0.5)


def generate_threat_scenario(threat_type: str, customer_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a realistic threat scenario given a threat type and customer context.
    Used for task generation.
    """
    threat = get_threat_by_type(threat_type)
    if not threat:
        return {}

    templates = threat.get("email_templates", [])
    if not templates:
        return {}

    template = templates[0]  # Use first template for now (could randomize)

    return {
        "threat_type": threat_type,
        "threat_name": threat["name"],
        "subject": template["subject"],
        "body_template": template["body_template"],
        "threat_indicators": template.get("threat_indicators", []),
        "difficulty": threat["difficulty_level"],
        "sophistication": threat["characteristics"].sophistication,
    }
