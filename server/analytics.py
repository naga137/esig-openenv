"""
Analytics & Metrics Tracking for ESIG.

Tracks:
  - Agent performance across episodes
  - Learning curves (improvement over time)
  - Collision rates, security detection accuracy
  - Reply quality distribution
  - Task completion rates
"""
from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics


@dataclass
class EpisodeMetrics:
    """Metrics for a single episode."""
    episode_id: str
    task_id: str
    timestamp: str
    duration_seconds: float
    steps_taken: int
    final_score: float
    collision_count: int
    security_threats_detected: int
    security_threats_missed: int
    pii_incidents: int
    erp_queries: int
    reply_quality_score: float
    completion_status: str  # "success", "timeout", "failed"


@dataclass
class LearningCurvePoint:
    """Single point in agent learning curve."""
    episode_number: int
    timestamp: str
    task_id: str
    cumulative_score: float
    moving_average_score: float  # Last N episodes
    completion_rate: float
    collision_rate: float


class AnalyticsEngine:
    """Central analytics and metrics aggregation."""

    def __init__(self):
        self.episodes: Dict[str, EpisodeMetrics] = {}
        self.task_stats: Dict[str, List[float]] = {}  # task_id -> list of scores
        self.agent_learning_curves: Dict[str, List[LearningCurvePoint]] = {}  # agent_id -> curve

    def record_episode(
        self,
        episode_id: str,
        task_id: str,
        final_score: float,
        steps_taken: int,
        collision_count: int = 0,
        security_detected: int = 0,
        security_missed: int = 0,
        pii_incidents: int = 0,
        erp_queries: int = 0,
        reply_quality: float = 0.75,
        duration_seconds: float = 0.0,
        status: str = "success",
    ) -> None:
        """Record metrics for completed episode."""
        metrics = EpisodeMetrics(
            episode_id=episode_id,
            task_id=task_id,
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration_seconds,
            steps_taken=steps_taken,
            final_score=final_score,
            collision_count=collision_count,
            security_threats_detected=security_detected,
            security_threats_missed=security_missed,
            pii_incidents=pii_incidents,
            erp_queries=erp_queries,
            reply_quality_score=reply_quality,
            completion_status=status,
        )

        self.episodes[episode_id] = metrics

        # Update task stats
        if task_id not in self.task_stats:
            self.task_stats[task_id] = []
        self.task_stats[task_id].append(final_score)

    def get_task_statistics(self, task_id: str) -> Dict[str, Any]:
        """Get aggregated statistics for a task."""
        if task_id not in self.task_stats or not self.task_stats[task_id]:
            return {"error": f"No data for task {task_id}"}

        scores = self.task_stats[task_id]

        return {
            "task_id": task_id,
            "total_episodes": len(scores),
            "mean_score": round(statistics.mean(scores), 4),
            "median_score": round(statistics.median(scores), 4),
            "stdev_score": round(statistics.stdev(scores), 4) if len(scores) > 1 else 0.0,
            "min_score": round(min(scores), 4),
            "max_score": round(max(scores), 4),
            "pass_rate": round(sum(1 for s in scores if s >= 0.70) / len(scores), 3),
        }

    def get_security_metrics(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get security detection metrics (precision, recall)."""
        if task_id:
            episodes = [e for e in self.episodes.values() if e.task_id == task_id]
        else:
            episodes = list(self.episodes.values())

        if not episodes:
            return {"error": "No episodes found"}

        total_threats = sum(e.security_threats_detected + e.security_threats_missed for e in episodes)
        correctly_detected = sum(e.security_threats_detected for e in episodes)
        false_negatives = sum(e.security_threats_missed for e in episodes)

        if total_threats == 0:
            return {"error": "No security threats in dataset"}

        recall = correctly_detected / total_threats if total_threats > 0 else 0.0
        accuracy = correctly_detected / (correctly_detected + false_negatives) if (
            correctly_detected + false_negatives
        ) > 0 else 0.0

        return {
            "task_id": task_id or "all",
            "total_episodes": len(episodes),
            "total_threats": total_threats,
            "threats_detected": correctly_detected,
            "threats_missed": false_negatives,
            "detection_rate": round(correctly_detected / total_threats, 3),
            "accuracy": round(accuracy, 3),
            "avg_pii_incidents": round(
                statistics.mean([e.pii_incidents for e in episodes]), 2
            ),
        }

    def get_leaderboard(self, task_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top-scoring episodes."""
        if task_id:
            episodes = [e for e in self.episodes.values() if e.task_id == task_id]
        else:
            episodes = list(self.episodes.values())

        sorted_episodes = sorted(episodes, key=lambda x: -x.final_score)

        return [
            {
                "rank": i + 1,
                "episode_id": e.episode_id,
                "task_id": e.task_id,
                "score": e.final_score,
                "steps": e.steps_taken,
                "collisions": e.collision_count,
                "timestamp": e.timestamp,
            }
            for i, e in enumerate(sorted_episodes[:limit])
        ]

    def get_learning_curve(self, task_id: str, window_size: int = 10) -> List[Dict[str, Any]]:
        """Get learning curve (rolling average) for a task."""
        if task_id not in self.task_stats:
            return []

        scores = self.task_stats[task_id]
        curve = []

        for i in range(len(scores)):
            start_idx = max(0, i - window_size + 1)
            window = scores[start_idx : i + 1]
            moving_avg = statistics.mean(window)

            curve.append({
                "episode_number": i + 1,
                "score": scores[i],
                "moving_average": round(moving_avg, 4),
                "window_size": len(window),
            })

        return curve

    def compare_tasks(self) -> Dict[str, Any]:
        """Compare performance across all tasks."""
        comparison = {}

        for task_id in self.task_stats.keys():
            stats = self.get_task_statistics(task_id)
            comparison[task_id] = stats

        return comparison

    def get_agent_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            "total_episodes": len(self.episodes),
            "tasks": list(self.task_stats.keys()),
            "task_statistics": {
                task_id: self.get_task_statistics(task_id) for task_id in self.task_stats.keys()
            },
            "security_metrics": self.get_security_metrics(),
            "top_10_episodes": self.get_leaderboard(limit=10),
            "overall_pass_rate": round(
                sum(1 for e in self.episodes.values() if e.final_score >= 0.70)
                / len(self.episodes)
                if self.episodes
                else 0.0,
                3,
            ),
        }

    def export_metrics_csv(self, task_id: Optional[str] = None) -> str:
        """Export metrics as CSV for analysis."""
        if task_id:
            episodes = [e for e in self.episodes.values() if e.task_id == task_id]
        else:
            episodes = list(self.episodes.values())

        lines = ["episode_id,task_id,score,steps,collisions,threats_detected,threats_missed,reply_quality"]

        for e in episodes:
            lines.append(
                f"{e.episode_id},{e.task_id},{e.final_score},{e.steps_taken},"
                f"{e.collision_count},{e.security_threats_detected},"
                f"{e.security_threats_missed},{e.reply_quality_score}"
            )

        return "\n".join(lines)


# Global analytics engine
_analytics = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get or create global analytics engine."""
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsEngine()
    return _analytics
