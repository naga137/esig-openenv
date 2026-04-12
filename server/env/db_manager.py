"""
ESIG Database Manager — SQLite persistence for concurrent episode management.

Supports:
  - Multiple concurrent episodes (100+)
  - Episode state snapshots
  - Action history & replay
  - Metrics aggregation
"""
from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import threading

# Thread-local storage for connections (safe concurrent access)
_local = threading.local()

DB_PATH = Path(__file__).parent.parent.parent / "esig.db"


def _get_connection() -> sqlite3.Connection:
    """Get thread-safe database connection."""
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db() -> None:
    """Initialize database schema."""
    conn = _get_connection()
    cursor = conn.cursor()

    # Episodes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            episode_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            final_score REAL,
            scenario_data TEXT,
            episode_flags TEXT,
            total_steps INTEGER DEFAULT 0
        )
    """)

    # Actions history (replay capability)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id TEXT NOT NULL,
            step_number INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            action_params TEXT,
            outcome_data TEXT,
            reward_value REAL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (episode_id) REFERENCES episodes (episode_id)
        )
    """)

    # Metrics aggregation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            episode_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            score REAL,
            collision_count INTEGER DEFAULT 0,
            pii_cleaned_count INTEGER DEFAULT 0,
            erp_queries INTEGER DEFAULT 0,
            threats_detected INTEGER DEFAULT 0,
            reply_quality_score REAL,
            completion_steps INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (episode_id) REFERENCES episodes (episode_id)
        )
    """)

    # Threat catalog
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS threat_catalog (
            threat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            threat_type TEXT NOT NULL,
            threat_name TEXT NOT NULL,
            description TEXT,
            difficulty_level TEXT,
            characteristics TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()


def save_episode(
    episode_id: str,
    task_id: str,
    scenario_data: Dict[str, Any],
    episode_flags: Dict[str, Any],
) -> None:
    """Save new episode to database."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO episodes (episode_id, task_id, scenario_data, episode_flags, status)
        VALUES (?, ?, ?, ?, 'active')
    """, (
        episode_id,
        task_id,
        json.dumps(scenario_data, default=str),
        json.dumps(episode_flags),
    ))
    conn.commit()


def get_episode(episode_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve episode by ID."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM episodes WHERE episode_id = ?", (episode_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
    
    return {
        "episode_id": row["episode_id"],
        "task_id": row["task_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "scenario_data": json.loads(row["scenario_data"]),
        "episode_flags": json.loads(row["episode_flags"]),
        "total_steps": row["total_steps"],
        "final_score": row["final_score"],
    }


def update_episode(
    episode_id: str,
    flags: Dict[str, Any] = None,
    status: str = None,
    score: float = None,
) -> None:
    """Update episode flags, status, or score."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if flags is not None:
        updates.append("episode_flags = ?")
        params.append(json.dumps(flags))
    
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    
    if score is not None:
        updates.append("final_score = ?")
        params.append(score)
    
    if not updates:
        return
    
    query = f"UPDATE episodes SET {', '.join(updates)} WHERE episode_id = ?"
    params.append(episode_id)
    
    cursor.execute(query, params)
    conn.commit()


def record_action(
    episode_id: str,
    step_number: int,
    action_type: str,
    action_params: Dict[str, Any],
    outcome_data: Dict[str, Any],
    reward_value: float,
) -> None:
    """Record action taken in an episode."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO actions (episode_id, step_number, action_type, action_params, outcome_data, reward_value)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        episode_id,
        step_number,
        action_type,
        json.dumps(action_params, default=str),
        json.dumps(outcome_data, default=str),
        reward_value,
    ))
    conn.commit()


def get_episode_history(episode_id: str) -> List[Dict[str, Any]]:
    """Get action history for an episode (replay capability)."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT step_number, action_type, action_params, outcome_data, reward_value, timestamp
        FROM actions
        WHERE episode_id = ?
        ORDER BY step_number ASC
    """, (episode_id,))
    
    return [dict(row) for row in cursor.fetchall()]


def save_metrics(
    episode_id: str,
    task_id: str,
    score: float,
    collision_count: int = 0,
    pii_cleaned_count: int = 0,
    erp_queries: int = 0,
    threats_detected: int = 0,
    reply_quality_score: float = 0.0,
    completion_steps: int = 0,
) -> None:
    """Aggregate metrics for analysis."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO metrics (
            episode_id, task_id, score, collision_count, pii_cleaned_count,
            erp_queries, threats_detected, reply_quality_score, completion_steps
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        episode_id, task_id, score, collision_count, pii_cleaned_count,
        erp_queries, threats_detected, reply_quality_score, completion_steps,
    ))
    conn.commit()


def get_task_stats(task_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get aggregated stats across all episodes for a task."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM metrics
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (task_id, limit))
    
    return [dict(row) for row in cursor.fetchall()]


def get_leaderboard(limit: int = 20) -> List[Dict[str, Any]]:
    """Get top-scoring episodes across all tasks."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT episode_id, task_id, score, completion_steps, created_at
        FROM metrics
        ORDER BY score DESC, completion_steps ASC
        LIMIT ?
    """, (limit,))
    
    return [dict(row) for row in cursor.fetchall()]


def register_threat_type(
    threat_type: str,
    threat_name: str,
    description: str,
    difficulty_level: str,
    characteristics: Dict[str, Any],
) -> int:
    """Register a new threat type in the catalog."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO threat_catalog (threat_type, threat_name, description, difficulty_level, characteristics)
        VALUES (?, ?, ?, ?, ?)
    """, (
        threat_type,
        threat_name,
        description,
        difficulty_level,
        json.dumps(characteristics),
    ))
    conn.commit()
    return cursor.lastrowid


def get_threat_catalog() -> List[Dict[str, Any]]:
    """Get all registered threat types."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM threat_catalog ORDER BY difficulty_level, threat_type")
    
    results = []
    for row in cursor.fetchall():
        results.append({
            "threat_id": row["threat_id"],
            "threat_type": row["threat_type"],
            "threat_name": row["threat_name"],
            "description": row["description"],
            "difficulty_level": row["difficulty_level"],
            "characteristics": json.loads(row["characteristics"]),
        })
    return results


def close_db() -> None:
    """Close database connection."""
    if hasattr(_local, 'conn') and _local.conn:
        _local.conn.close()
        _local.conn = None
