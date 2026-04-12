"""
ESIG OCR Module — extracts text from PDF attachments using pdfminer.six.
Falls back to a known fixture when the attachment name matches a scenario key.
This is the deterministic tool agents should prefer over LLM parsing.
"""
from __future__ import annotations
import io
import os
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Known fixture PDFs (base64-encoded tiny PDFs with embedded text)
# We use these so the environment works without real file uploads.
# ---------------------------------------------------------------------------

FIXTURE_TEXTS: dict[str, str] = {
    "invoice_INV-2024-0042.pdf": (
        "INVOICE\n"
        "Invoice Number: INV-2024-0042\n"
        "Date: 2024-11-01\n"
        "Bill To: Acme Corp\n"
        "Description: Enterprise SaaS Plan - Annual License\n"
        "Amount: $12,500.00\n"
        "Due Date: 2024-12-01\n"
        "Payment Terms: NET 30\n"
        "Please reference invoice number when making payment.\n"
    ),
    "invoice_INV-2024-0044.pdf": (
        "INVOICE\n"
        "Invoice Number: INV-2024-0044\n"
        "Date: 2024-11-05\n"
        "Bill To: Initech Ltd\n"
        "Description: Starter Pack - Monthly\n"
        "Amount: $450.00\n"
        "Due Date: 2024-11-20\n"
        "Payment Terms: NET 15\n"
    ),
}

# ---------------------------------------------------------------------------
# PII patterns — deterministic regex (agents rewarded for using these)
# ---------------------------------------------------------------------------

PII_PATTERNS = {
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "ssn":         re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email":       re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone":       re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
}


def extract_text_from_pdf(attachment_name: str, pdf_bytes: Optional[bytes] = None) -> str:
    """
    Extract plain text from a PDF.
    Priority: fixture lookup → pdfminer on real bytes → error string.
    """
    # 1. Fixture lookup (deterministic for test scenarios)
    if attachment_name in FIXTURE_TEXTS:
        return FIXTURE_TEXTS[attachment_name]

    # 2. Real PDF bytes via pdfminer
    if pdf_bytes:
        try:
            from pdfminer.high_level import extract_text as pm_extract
            return pm_extract(io.BytesIO(pdf_bytes))
        except Exception as exc:  # noqa: BLE001
            return f"OCR_ERROR: {exc}"

    return "OCR_ERROR: attachment not found and no bytes provided"


def detect_and_redact_pii(text: str) -> tuple[str, list[str]]:
    """
    Detect PII types and return (redacted_text, list_of_pii_types_found).
    Agents are rewarded for calling this instead of asking the LLM to spot PII.
    """
    found_types: list[str] = []
    redacted = text
    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(redacted)
        if matches:
            found_types.append(pii_type)
            redacted = pattern.sub(f"[REDACTED_{pii_type.upper()}]", redacted)
    return redacted, found_types


def extract_invoice_number(text: str) -> Optional[str]:
    """Deterministic invoice-number extraction — faster than LLM."""
    match = re.search(r"Invoice\s+Number[:\s]+([A-Z]{3}-\d{4}-\d{4})", text)
    return match.group(1) if match else None
