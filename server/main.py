"""
ESIG — Enterprise Shared-Inbox Guardian
FastAPI server implementing the full OpenEnv specification.

Endpoints:
  POST /reset          → Observation
  POST /step           → StepResult
  GET  /state          → current episode state
  GET  /tasks          → list of available tasks
  POST /grade          → run grader on current episode
  GET  /health         → liveness probe (HF Space ping)
"""
from __future__ import annotations
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from server.env.models import Action, Observation, Reward, StepResult
from server.env import (
    acquire_lock, release_lock, get_locked_threads,
    query_erp, extract_text_from_pdf, detect_and_redact_pii,
)
from server.env import erp_db
from server.env import state_manager as sm
from server.tasks import TASK_REGISTRY
from server.graders import GRADER_REGISTRY
from server.reward import compute_reward

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Enterprise Shared-Inbox Guardian (ESIG)",
    description=(
        "A stateful OpenEnv training environment simulating enterprise email triage. "
        "Agents learn collision avoidance, ERP lookup, OCR processing, and adversarial "
        "BEC/prompt-injection detection."
    ),
    version="1.0.0",
    tags_metadata=[
        {"name": "openenv", "description": "Core OpenEnv spec endpoints"},
        {"name": "meta",    "description": "Metadata and health endpoints"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure DB is seeded at startup
erp_db.seed_database()

# In-memory active session (single-episode server for HF Spaces simplicity)
_active_episode_id: Optional[str] = None
_active_task_id:    Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_episode() -> str:
    if not _active_episode_id:
        raise HTTPException(400, "No active episode. Call /reset first.")
    return _active_episode_id


def _process_action(action: Action, episode_id: str) -> Dict[str, Any]:
    """
    Dispatch the action to the correct tool and return an outcome dict
    for the reward shaper.
    """
    episode  = sm.get_episode(episode_id)
    flags    = episode["flags"]
    scenario = episode["scenario"]
    gt       = scenario.get("ground_truth", {})
    outcome: Dict[str, Any] = {"task_complete": False}

    at = action.action_type.lower()

    # -----------------------------------------------------------------------
    # triage_lock
    # -----------------------------------------------------------------------
    if at == "triage_lock":
        email_id = action.params.get("email_id") or scenario["active_thread"]["email_id"]
        success, msg = acquire_lock(email_id, episode_id)
        if success:
            outcome["lock_acquired"] = True
            sm.update_episode(episode_id, {"flags": {"lock_acquired": True}})
        else:
            outcome["collision"] = True
            sm.update_episode(episode_id, {"flags": {"collision": True}})
        outcome["message"] = msg

    # -----------------------------------------------------------------------
    # ocr_process
    # -----------------------------------------------------------------------
    elif at == "ocr_process":
        attachment = action.params.get("attachment_name", "")
        result = extract_text_from_pdf(attachment)
        sm.update_episode(episode_id, {
            "ocr_result": result,
            "flags": {"ocr_done": True},
        })
        outcome["ocr_done"] = True
        outcome["ocr_text"] = result

    # -----------------------------------------------------------------------
    # erp_query
    # -----------------------------------------------------------------------
    elif at == "erp_query":
        key = action.params.get("query_key", "")
        val = action.params.get("query_value", "")
        result = query_erp(key, val)
        matched = result is not None
        sm.update_episode(episode_id, {
            "erp_result": result,
            "flags": {"erp_matched": matched},
        })
        outcome["erp_matched"] = matched
        outcome["erp_result"] = result

    # -----------------------------------------------------------------------
    # security_flag
    # -----------------------------------------------------------------------
    elif at == "security_flag":
        email_id    = action.params.get("email_id", "")
        threat_type = action.params.get("threat_type", "")
        flagged     = episode.get("flagged_emails", [])
        flagged.append({"email_id": email_id, "threat_type": threat_type})
        sm.update_episode(episode_id, {
            "flagged_emails": flagged,
            "flags": {"security_flagged": True},
        })
        # Count correct flags for partial reward
        legit_threats = {
            gt.get("inject_email_id"): "prompt_injection",
            gt.get("spoof_email_id"):  "bec_spoofing",
        }
        correct = sum(
            1 for f in flagged
            if legit_threats.get(f["email_id"]) and
               legit_threats[f["email_id"]] in f.get("threat_type", "")
        )
        outcome["security_flagged"] = True
        outcome["security_flags_correct"] = correct

    # -----------------------------------------------------------------------
    # mcp_external_call
    # -----------------------------------------------------------------------
    elif at == "mcp_external_call":
        tool    = action.params.get("tool", "unknown")
        payload = action.params.get("payload", {})
        # Simulated MCP response (calendar, slack, etc.)
        outcome["mcp_tool"]   = tool
        outcome["mcp_result"] = f"MCP:{tool} acknowledged payload with {len(str(payload))} chars"

    # -----------------------------------------------------------------------
    # reply
    # -----------------------------------------------------------------------
    elif at == "reply":
        email_id = action.params.get("email_id", "")
        body     = action.params.get("body", action.action_str)
        dept     = action.params.get("department", "general")

        # Check: was this a threat email? Penalise
        active_email_id = scenario["active_thread"]["email_id"]
        is_active_threat = scenario["active_thread"].get("is_adversarial", False)
        if is_active_threat:
            outcome["processed_bec"] = True
            sm.update_episode(episode_id, {"flags": {"processed_bec": True}})

        # PII check on reply body
        _, pii_found = detect_and_redact_pii(body)
        # If PII already cleaned in earlier step, flag correctly
        if episode["flags"].get("pii_cleaned") and not pii_found:
            outcome["pii_cleaned"] = True

        sm.update_episode(episode_id, {
            "reply_body": body,
            "reply_dept": dept,
            "replied_to_email_id": email_id,
            "flags": {"replied": True},
        })

        # Determine task completion
        task_id = _active_task_id or "task1_easy"
        outcome["replied_correctly"] = not is_active_threat
        outcome["correct_dept"] = dept.lower() == gt.get("correct_dept", "billing")

        # Task 1 complete when replied with PII cleaned + correct dept
        if task_id == "task1_easy":
            outcome["task_complete"] = (
                flags.get("lock_acquired") and
                flags.get("pii_cleaned") and
                outcome.get("replied_correctly") and
                outcome.get("correct_dept")
            )
        # Task 2 complete when OCR + ERP + replied
        elif task_id == "task2_medium":
            outcome["task_complete"] = (
                flags.get("lock_acquired") and
                flags.get("ocr_done") and
                flags.get("erp_matched") and
                outcome.get("replied_correctly")
            )
        # Task 3 complete when 2 threats flagged + legit replied
        elif task_id == "task3_hard":
            flagged = episode.get("flagged_emails", [])
            outcome["task_complete"] = len(flagged) >= 2 and outcome.get("replied_correctly")

    else:
        outcome["error"] = f"Unknown action_type: {action.action_type}"

    return outcome


# ---------------------------------------------------------------------------
# OpenEnv core endpoints
# ---------------------------------------------------------------------------

@app.post("/reset", tags=["openenv"])
def reset(task_id: str = Query(default="task1_easy")) -> Observation:
    """
    Reset the environment and return the initial observation.
    Implements OpenEnv reset() spec.
    """
    global _active_episode_id, _active_task_id

    if task_id not in TASK_REGISTRY:
        raise HTTPException(400, f"Unknown task_id '{task_id}'. "
                                 f"Valid: {list(TASK_REGISTRY.keys())}")

    sm.reset_all()
    episode_id = f"ep_{uuid.uuid4().hex[:8]}"
    _active_episode_id = episode_id
    _active_task_id    = task_id

    gen_fn, obs_fn = TASK_REGISTRY[task_id]
    scenario = gen_fn(episode_id)
    sm.init_episode(episode_id, task_id, scenario)
    return obs_fn(scenario, episode_id)


@app.post("/step", tags=["openenv"])
def step(action: Action) -> StepResult:
    """
    Execute one action and return (observation, reward, done, info).
    Implements OpenEnv step() spec.
    """
    episode_id = _require_episode()
    episode    = sm.get_episode(episode_id)

    if episode["step"] >= episode["scenario"].get("max_steps", 15):
        raise HTTPException(400, "Episode has exceeded max_steps. Call /reset.")

    # Snapshot flags BEFORE the action so the reward shaper sees the pre-action state
    flags_before = dict(episode["flags"])

    # Process action
    outcome  = _process_action(action, episode_id)
    episode  = sm.get_episode(episode_id)   # re-fetch after update

    # Compute reward using pre-action flags (partial-progress signals are new deltas)
    reward = compute_reward(action, outcome, flags_before, _active_task_id or "task1_easy")

    # Build next observation
    scenario  = episode["scenario"]
    gen_fn, obs_fn = TASK_REGISTRY[_active_task_id]
    next_obs = obs_fn(scenario, episode_id)

    # Update live observation fields
    next_obs.step_number  = episode["step"]
    next_obs.inbox_state.locked_threads = get_locked_threads()
    if episode.get("erp_result"):
        next_obs.erp_state.last_query_result = episode["erp_result"]
    if outcome.get("error"):
        next_obs.last_action_error = outcome["error"]

    return StepResult(
        observation=next_obs,
        reward=reward,
        done=reward.done,
        info=outcome,
    )


@app.get("/state", tags=["openenv"])
def state() -> Dict[str, Any]:
    """
    Return current episode state snapshot.
    Agents should call this before triage_lock() to avoid collision.
    Implements OpenEnv state() spec.
    """
    episode_id = _require_episode()
    episode    = sm.get_episode(episode_id)
    return {
        "episode_id":      episode_id,
        "task_id":         _active_task_id,
        "step":            episode["step"],
        "flags":           episode["flags"],
        "locked_threads":  get_locked_threads(),
        "flagged_emails":  episode.get("flagged_emails", []),
    }


# ---------------------------------------------------------------------------
# Grade endpoint
# ---------------------------------------------------------------------------

@app.post("/grade", tags=["openenv"])
def grade(use_judge: bool = Query(default=True)) -> Dict[str, Any]:
    """Run the task grader on the current episode."""
    episode_id = _require_episode()
    task_id    = _active_task_id or "task1_easy"
    episode    = sm.get_episode(episode_id)

    grader = GRADER_REGISTRY.get(task_id)
    if not grader:
        raise HTTPException(400, f"No grader for task_id '{task_id}'")

    if task_id == "task3_hard":
        return grader(episode, use_judge=use_judge)
    return grader(episode)


# ---------------------------------------------------------------------------
# Meta endpoints
# ---------------------------------------------------------------------------

@app.get("/tasks", tags=["meta"])
def list_tasks() -> list:
    """List all available tasks and their metadata."""
    return [
        {"task_id": "task1_easy",   "difficulty": "easy",
         "name": "Basic Email Triage with PII Detection"},
        {"task_id": "task2_medium", "difficulty": "medium",
         "name": "Multi-Step ERP Lookup with OCR and Collision Avoidance"},
        {"task_id": "task3_hard",   "difficulty": "hard",
         "name": "Adversarial BEC and Prompt Injection Detection"},
        {"task_id": "task4_expert", "difficulty": "expert",
         "name": "Multi-Threat Expert Scenario with 5-Email Sequence"},
    ]


@app.get("/health", tags=["meta"])
def health() -> Dict[str, str]:
    """Liveness probe — required by the HF Space automated ping."""
    return {"status": "ok", "service": "ESIG OpenEnv Environment"}


@app.get("/", tags=["meta"])
def root() -> Dict[str, str]:
    return {
        "name":    "Enterprise Shared-Inbox Guardian (ESIG)",
        "version": "1.0.0",
        "docs":    "/docs",
        "openenv": "/openenv.yaml",
    }


# ---------------------------------------------------------------------------
# Advanced Features (NEW)
# ---------------------------------------------------------------------------

@app.get("/tasks/advanced", tags=["advanced"])
def list_advanced_tasks() -> list:
    """List advanced and expert tasks."""
    return [
        {"task_id": "task4_expert", "difficulty": "expert",
         "name": "Multi-Threat Advanced Scenarios with 5-Email Sequence"},
    ]


@app.get("/threats/catalog", tags=["advanced"])
def get_threat_catalog() -> Dict[str, Any]:
    """
    Get comprehensive threat catalog with all detection characteristics.
    Used by agents to understand threat landscape.
    """
    from server.tasks.advanced_threats import THREAT_REGISTRY
    
    return {
        "total_threats": len(THREAT_REGISTRY),
        "threats": [
            {
                "threat_type": threat_type,
                "name": data["name"],
                "description": data["description"],
                "difficulty": data["difficulty_level"],
                "characteristics": {
                    "keywords": data["characteristics"].keywords,
                    "urgency_level": data["characteristics"].urgency_level,
                    "sophistication": data["characteristics"].sophistication,
                },
            }
            for threat_type, data in THREAT_REGISTRY.items()
        ],
    }


@app.post("/analyze/threat", tags=["advanced"])
def analyze_threat_in_email(
    email_body: str,
    sender_domain: str,
    subject: str,
) -> Dict[str, Any]:
    """
    Analyze an email for potential threats using threat signatures.
    Returns list of detected threats with confidence scores.
    """
    from server.tasks.advanced_threats import detect_threat
    
    detected = detect_threat(email_body, sender_domain, subject)
    return {
        "email_sender_domain": sender_domain,
        "threats_detected": len(detected),
        "threats": detected,
    }


@app.get("/analytics/task/{task_id}", tags=["analytics"])
def get_task_analytics(task_id: str) -> Dict[str, Any]:
    """Get analytics for a specific task."""
    from server.analytics import get_analytics_engine
    
    engine = get_analytics_engine()
    stats = engine.get_task_statistics(task_id)
    security = engine.get_security_metrics(task_id)
    
    return {
        "task_id": task_id,
        "statistics": stats,
        "security_metrics": security,
    }


@app.get("/analytics/leaderboard", tags=["analytics"])
def get_leaderboard(limit: int = Query(default=20)) -> Dict[str, Any]:
    """Get top-scoring episodes across all tasks."""
    from server.analytics import get_analytics_engine
    
    engine = get_analytics_engine()
    return {
        "limit": limit,
        "leaderboard": engine.get_leaderboard(limit=limit),
    }


@app.get("/analytics/learning-curve/{task_id}", tags=["analytics"])
def get_learning_curve(task_id: str) -> Dict[str, Any]:
    """Get learning curve (moving average) for agent performance on a task."""
    from server.analytics import get_analytics_engine
    
    engine = get_analytics_engine()
    curve = engine.get_learning_curve(task_id, window_size=10)
    
    return {
        "task_id": task_id,
        "window_size": 10,
        "learning_curve": curve,
    }


@app.get("/analytics/report", tags=["analytics"])
def get_performance_report() -> Dict[str, Any]:
    """Get comprehensive agent performance report."""
    from server.analytics import get_analytics_engine
    
    engine = get_analytics_engine()
    return engine.get_agent_performance_report()


@app.get("/erp/orders/customer/{customer_id}", tags=["erp"])
def get_customer_orders(customer_id: str) -> Dict[str, Any]:
    """Query all orders for a customer (enhanced ERP)."""
    from server.env.erp_enhanced import get_erp_database
    
    db = get_erp_database()
    orders = db.query_orders_by_customer(customer_id)
    
    return {
        "customer_id": customer_id,
        "order_count": len(orders),
        "orders": [db.get_order_summary(o.order_id) for o in orders],
    }


@app.get("/erp/order/{order_id}", tags=["erp"])
def get_order_details(order_id: str) -> Dict[str, Any]:
    """Get comprehensive order details (enhanced ERP)."""
    from server.env.erp_enhanced import get_erp_database
    
    db = get_erp_database()
    return db.get_order_summary(order_id)


@app.get("/erp/inventory/{sku}", tags=["erp"])
def check_inventory(sku: str) -> Dict[str, Any]:
    """Check inventory availability for SKU."""
    from server.env.erp_enhanced import get_erp_database
    
    db = get_erp_database()
    item = db.query_inventory(sku)
    
    if not item:
        raise HTTPException(404, f"SKU {sku} not found")
    
    return {
        "sku": sku,
        "product_name": item.product_name,
        "quantity_on_hand": item.quantity_on_hand,
        "quantity_reserved": item.quantity_reserved,
        "quantity_available": item.quantity_available,
        "reorder_point": item.reorder_point,
        "warehouse_location": item.warehouse_location,
    }


@app.post("/gymnasium/env", tags=["rl-frameworks"])
def get_gymnasium_env_info() -> Dict[str, Any]:
    """Get information about Gymnasium environment registration."""
    return {
        "environment_id": "ESIG-v1",
        "library": "gymnasium>=0.29.0",
        "entry_point": "server.env.gymnasium_wrapper:ESIGEnv",
        "usage": {
            "python": "import gymnasium as gym; env = gym.make('ESIG-v1')",
            "compatible_frameworks": [
                "Gymnasium",
                "OpenAI Baselines",
                "Stable-Baselines3",
                "Ray RLlib",
                "PyMARL",
            ],
        },
        "spaces": {
            "observation_space": "Dict (email subject, body, sender, adversarial status, etc.)",
            "action_space": "Discrete(6): triage_lock, ocr_process, erp_query, security_flag, mcp_external_call, reply",
        },
    }
