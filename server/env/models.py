"""
ESIG — Pydantic typed models for Observation, Action, and Reward.
Fully compliant with the OpenEnv specification.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models that compose the Observation
# ---------------------------------------------------------------------------

class EmailThread(BaseModel):
    """Full email thread history to eliminate the Toggle Tax."""
    email_id: str
    subject: str
    body: str
    sender: str
    sender_domain: str
    attachments: List[str] = Field(default_factory=list)
    history: List[Dict[str, str]] = Field(default_factory=list)
    is_adversarial: bool = False
    threat_type: Optional[str] = None   # "bec" | "prompt_injection" | None


class ERPState(BaseModel):
    """Snapshot of the simulated Enterprise Resource Planning system."""
    orders: List[Dict[str, Any]] = Field(default_factory=list)
    invoices: List[Dict[str, Any]] = Field(default_factory=list)
    last_query_result: Optional[Dict[str, Any]] = None


class CRMContext(BaseModel):
    """Customer Relationship Management context for the email sender."""
    customer_id: str
    customer_name: str
    customer_tier: str = "silver"   # "gold" | "silver" | "at-risk"
    open_tickets: int = 0
    sentiment_score: float = 0.5    # 0.0 (very negative) – 1.0 (very positive)
    account_value_usd: float = 0.0


class InboxState(BaseModel):
    """Meta-data showing which threads are locked by other simulated agents."""
    locked_threads: Dict[str, str] = Field(default_factory=dict)   # email_id → agent_id
    total_emails_pending: int = 0
    current_agent_id: str = "agent_primary"


# ---------------------------------------------------------------------------
# Top-level Observation — unified view eliminates the Toggle Tax
# ---------------------------------------------------------------------------

class Observation(BaseModel):
    """
    Unified observation eliminating the Toggle Tax.
    The agent sees the full enterprise state in one object.
    """
    active_thread: EmailThread
    erp_state: ERPState
    crm_context: CRMContext
    inbox_state: InboxState
    step_number: int = 0
    task_id: str = "task1_easy"
    max_steps: int = 15
    last_action_error: Optional[str] = None
    deterministic_tools_used: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Action — the agent's toolset
# ---------------------------------------------------------------------------

class Action(BaseModel):
    """
    Agent action. action_type must be one of the five ESIG tools or 'reply'.
    params carries tool-specific arguments.

    action_type options:
      triage_lock        — Lock a thread to prevent collision. params: {email_id}
      ocr_process        — Extract text from a PDF attachment. params: {attachment_name}
      erp_query          — Query ERP for order/invoice. params: {query_key, query_value}
      security_flag      — Flag a BEC or prompt-injection threat. params: {email_id, threat_type}
      mcp_external_call  — MCP tool call (calendar, slack). params: {tool, payload}
      reply              — Send a reply. params: {email_id, body, department}
    """
    action_type: str
    action_str: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reward — meaningful, partial-progress signal
# ---------------------------------------------------------------------------

class Reward(BaseModel):
    """
    Shaped reward with partial-progress signals.
    value range: -2.0 (hard collision penalty) to 1.0 (full task completion).
    """
    value: float
    partial_signals: Dict[str, float] = Field(default_factory=dict)
    done: bool = False
    info: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Step result returned by /step
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)
