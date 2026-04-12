"""
ESIG State Manager — thread-safe locking to prevent agent collision.

If two agents call triage_lock() on the same email_id simultaneously,
the second caller receives a -2.0 collision penalty. This teaches agents
to call state() before acting.
"""
from __future__ import annotations
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

_LOCK_TIMEOUT_SECONDS = 60

_locks: Dict[str, Tuple[str, datetime]] = {}
_episode_state: Dict[str, dict] = {}
_mutex = threading.Lock()


# ---------------------------------------------------------------------------
# Lock management
# ---------------------------------------------------------------------------

def acquire_lock(email_id: str, agent_id: str) -> Tuple[bool, str]:
    """
    Attempt to lock a thread for exclusive processing.
    Returns (success, message).
    Collision → returns False → caller should apply -2.0 penalty.
    """
    with _mutex:
        now = datetime.utcnow()
        if email_id in _locks:
            holder, ts = _locks[email_id]
            age = now - ts
            if age < timedelta(seconds=_LOCK_TIMEOUT_SECONDS):
                if holder != agent_id:
                    return False, f"COLLISION: thread {email_id} is locked by {holder}"
        _locks[email_id] = (agent_id, now)
        return True, f"Lock acquired on {email_id} by {agent_id}"


def release_lock(email_id: str, agent_id: str) -> bool:
    with _mutex:
        if email_id in _locks and _locks[email_id][0] == agent_id:
            del _locks[email_id]
            return True
        return False


def get_locked_threads() -> Dict[str, str]:
    with _mutex:
        now = datetime.utcnow()
        # expire stale locks
        expired = [eid for eid, (_, ts) in _locks.items()
                   if now - ts >= timedelta(seconds=_LOCK_TIMEOUT_SECONDS)]
        for eid in expired:
            del _locks[eid]
        return {eid: holder for eid, (holder, _) in _locks.items()}


# ---------------------------------------------------------------------------
# Episode state (per task run)
# ---------------------------------------------------------------------------

def init_episode(episode_id: str, task_id: str, scenario: dict) -> None:
    with _mutex:
        _episode_state[episode_id] = {
            "task_id": task_id,
            "scenario": scenario,
            "step": 0,
            "actions_taken": [],
            "flags": {
                "lock_acquired": False,
                "pii_cleaned": False,
                "ocr_done": False,
                "erp_matched": False,
                "security_flagged": False,
                "processed_bec": False,
                "replied": False,
                "hallucinated": False,
                "used_llm_for_regex": False,
                "collision": False,
            },
            "ocr_result": None,
            "erp_result": None,
            "reply_body": None,
            "flagged_emails": [],
        }


def get_episode(episode_id: str) -> Optional[dict]:
    with _mutex:
        return _episode_state.get(episode_id)


def update_episode(episode_id: str, updates: dict) -> None:
    with _mutex:
        if episode_id in _episode_state:
            ep = _episode_state[episode_id]
            for k, v in updates.items():
                if k == "flags" and isinstance(v, dict):
                    ep["flags"].update(v)
                else:
                    ep[k] = v
            ep["step"] += 1


def clear_episode(episode_id: str) -> None:
    with _mutex:
        _episode_state.pop(episode_id, None)


def reset_all() -> None:
    """Full reset — call on /reset to clear stale state between episodes."""
    with _mutex:
        _locks.clear()
        _episode_state.clear()
