"""
ESIG Gymnasium Wrapper — standard RL environment interface.

Enables compatibility with:
  - OpenAI Baselines
  - Stable-Baselines3
  - Ray RLlib
  - Any Gymnasium-compatible framework

Usage:
    import gymnasium as gym
    env = gym.make("ESIG-v1", task_id="task1_easy")
    obs, info = env.reset()
    action, _ = model.predict(obs)
    obs, reward, terminated, truncated, info = env.step(action)
"""
from __future__ import annotations
from typing import Any, Dict, Tuple, Optional
import numpy as np
import uuid

try:
    import gymnasium as gym
    from gymnasium import spaces
    HAS_GYMNASIUM = True
except ImportError:
    HAS_GYMNASIUM = False
    # Dummy classes for when gymnasium not available
    class gym:
        class Env:
            pass
    class spaces:
        class Discrete:
            def __init__(self, n):
                self.n = n
        class Dict:
            pass
        class Box:
            def __init__(self, low, high, shape, dtype):
                pass
        class Categorical:
            pass
        class Text:
            pass

from server.env.models import Action, Observation
from server.env import state_manager as sm
from server.tasks import TASK_REGISTRY
from server.graders import GRADER_REGISTRY
from server.reward import compute_reward


class ESIGEnv(gym.Env if HAS_GYMNASIUM else object):
    """
    Gymnasium-compatible ESIG environment.

    Observation space: Dict with structured observations
    Action space: Discrete or MultiBinary depending on configuration
    """

    if HAS_GYMNASIUM:
        metadata = {
            "render_modes": ["human", "rgb_array"],
            "render_fps": 1,
        }
    else:
        metadata = {}

    def __init__(
        self,
        task_id: str = "task1_easy",
        render_mode: Optional[str] = None,
        max_steps: Optional[int] = None,
    ):
        """
        Initialize ESIG environment.

        Args:
            task_id: Task to use ("task1_easy", "task2_medium", "task3_hard")
            render_mode: "human" or "rgb_array" or None
            max_steps: Override default max steps (if None, use task default)
        """
        self.task_id = task_id
        self.render_mode = render_mode
        self.episode_id: Optional[str] = None
        self.current_step: int = 0
        self.max_steps: int = max_steps or self._get_task_max_steps()

        # Get task generator
        if task_id not in TASK_REGISTRY:
            raise ValueError(f"Unknown task: {task_id}. Available: {list(TASK_REGISTRY.keys())}")

        self.task_generator = TASK_REGISTRY[task_id]
        self.grader = GRADER_REGISTRY.get(task_id)

        # Define action space
        self._setup_action_space()

        # Define observation space (Dict space for flexibility)
        self.observation_space = spaces.Dict({
            "task_id": spaces.Text(max_length=50),
            "step_number": spaces.Discrete(self.max_steps + 1),
            "max_steps": spaces.Discrete(self.max_steps + 1),
            "active_thread_subject": spaces.Text(max_length=500),
            "active_thread_body": spaces.Text(max_length=5000),
            "sender": spaces.Text(max_length=100),
            "is_adversarial": spaces.Discrete(2),  # 0 or 1
            "threat_type": spaces.Text(max_length=50),
            "locked_threads_count": spaces.Discrete(100),
            "crm_customer_tier": spaces.Categorical(["bronze", "silver", "gold", "platinum"]),
            "crm_sentiment_score": spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32),
            "erp_orders_count": spaces.Discrete(20),
            "erp_invoices_count": spaces.Discrete(20),
            "step_error": spaces.Text(max_length=200),
        })

        self.last_observation: Optional[Dict[str, Any]] = None

    def _get_task_max_steps(self) -> int:
        """Get max steps from task definition."""
        # Dynamically import task to get MAX_STEPS
        if self.task_id == "task1_easy":
            from server.tasks.task1_triage import MAX_STEPS
            return MAX_STEPS
        elif self.task_id == "task2_medium":
            from server.tasks.task2_erp_lookup import MAX_STEPS
            return MAX_STEPS
        elif self.task_id == "task3_hard":
            from server.tasks.task3_adversarial import MAX_STEPS
            return MAX_STEPS
        return 20

    def _setup_action_space(self) -> None:
        """Define action space with all available actions."""
        # Discrete action space:
        # 0: triage_lock
        # 1: ocr_process
        # 2: erp_query
        # 3: security_flag
        # 4: mcp_external_call
        # 5: reply
        self.action_space = spaces.Discrete(6)

        # Action mapping for discrete -> action type
        self.action_type_map = {
            0: "triage_lock",
            1: "ocr_process",
            2: "erp_query",
            3: "security_flag",
            4: "mcp_external_call",
            5: "reply",
        }

    def reset(
        self, seed: Optional[int] = None, options: Optional[Dict] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Reset environment for new episode.

        Returns:
            observation: Dict with initial state
            info: Dict with metadata
        """
        super().reset(seed=seed)

        # Generate new episode
        self.episode_id = str(uuid.uuid4())
        self.current_step = 0

        # Generate task scenario
        scenario = self.task_generator["generate_scenario"](self.episode_id)

        # Initialize episode in state manager
        sm.start_episode(self.episode_id, self.task_id, scenario)

        # Build initial observation
        initial_obs = self.task_generator["build_initial_observation"](scenario, self.episode_id)

        # Convert to gym format
        self.last_observation = self._convert_observation_to_dict(initial_obs)

        info = {
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "step": 0,
            "max_steps": self.max_steps,
        }

        return self.last_observation, info

    def step(self, action: int) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]:
        """
        Execute one step of the environment.

        Args:
            action: Discrete action (0-5)

        Returns:
            observation: Updated observation dict
            reward: Reward value
            terminated: Whether episode finished successfully
            truncated: Whether max steps exceeded
            info: Additional info
        """
        if self.episode_id is None:
            raise RuntimeError("Must call reset() before step()")

        # Validate action
        if not isinstance(action, (int, np.integer)):
            raise ValueError(f"Invalid action type: {type(action)}")
        if action not in self.action_space:
            raise ValueError(f"Invalid action: {action}")

        action_type = self.action_type_map[action]

        # Convert discrete action to ESIG Action with dummy params
        # In real usage, agent would output structured params
        action_obj = Action(
            action_type=action_type,
            action_str=f"Execute {action_type}",
            params=self._get_action_params(action, self.last_observation),
        )

        # Execute action via state manager
        from server.main import _process_action
        outcome = _process_action(action_obj, self.episode_id)

        # Get reward
        episode = sm.get_episode(self.episode_id)
        reward_obj = compute_reward(
            action_obj,
            outcome,
            episode["flags"],
            self.task_id,
        )
        reward = reward_obj.value

        # Update step
        self.current_step += 1
        episode["step"] = self.current_step

        # Check termination conditions
        task_complete = outcome.get("task_complete", False)
        max_steps_exceeded = self.current_step >= self.max_steps
        terminated = task_complete
        truncated = max_steps_exceeded

        # Get updated observation
        new_obs = self._get_current_observation()
        self.last_observation = new_obs

        # Score if terminal
        info = {
            "episode_id": self.episode_id,
            "step": self.current_step,
            "action_type": action_type,
            "reward_signals": reward_obj.partial_signals,
        }

        if terminated or truncated:
            if self.grader:
                score = self.grader["grade"](episode)
                info["final_score"] = score["score"]
                info["score_breakdown"] = score["breakdown"]

        return new_obs, reward, terminated, truncated, info

    def render(self) -> Optional[str]:
        """Render environment."""
        if self.last_observation is None:
            return None

        if self.render_mode == "human":
            print(f"\n--- Step {self.current_step} / {self.max_steps} ---")
            print(f"Subject: {self.last_observation.get('active_thread_subject', '???')}")
            print(f"Sender: {self.last_observation.get('sender', '???')}")
            print(f"Adversarial: {self.last_observation.get('is_adversarial', False)}")
            return None

        return None

    def close(self) -> None:
        """Close environment."""
        pass

    # =========================================================================
    # Helper methods
    # =========================================================================

    def _convert_observation_to_dict(self, obs: Observation) -> Dict[str, Any]:
        """Convert Observation model to gym Dict format."""
        return {
            "task_id": obs.task_id or self.task_id,
            "step_number": obs.step_number,
            "max_steps": obs.max_steps,
            "active_thread_subject": obs.active_thread.subject or "",
            "active_thread_body": obs.active_thread.body or "",
            "sender": obs.active_thread.sender or "",
            "is_adversarial": 1 if obs.active_thread.is_adversarial else 0,
            "threat_type": obs.active_thread.threat_type or "none",
            "locked_threads_count": len(obs.inbox_state.locked_threads),
            "crm_customer_tier": obs.crm_context.customer_tier or "bronze",
            "crm_sentiment_score": np.array([obs.crm_context.sentiment_score or 0.5], dtype=np.float32),
            "erp_orders_count": len(obs.erp_state.orders or []),
            "erp_invoices_count": len(obs.erp_state.invoices or []),
            "step_error": obs.last_action_error or "",
        }

    def _get_current_observation(self) -> Dict[str, Any]:
        """Get current observation from state manager."""
        if not self.episode_id:
            return {}

        episode = sm.get_episode(self.episode_id)
        scenario = episode.get("scenario", {})

        # Reconstruct observation (simplified)
        from server.env.models import EmailThread, ERPState, CRMContext, InboxState

        obs = Observation(
            active_thread=EmailThread(**scenario.get("active_thread", {})),
            erp_state=ERPState(),
            crm_context=CRMContext(**scenario.get("crm", {})),
            inbox_state=InboxState(locked_threads=scenario.get("locked_threads", {})),
            step_number=self.current_step,
            task_id=self.task_id,
            max_steps=self.max_steps,
        )

        return self._convert_observation_to_dict(obs)

    def _get_action_params(self, action_idx: int, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate reasonable default action params based on action type."""
        action_type = self.action_type_map[action_idx]

        if action_type == "triage_lock":
            # Find any email_id to lock
            episode = sm.get_episode(self.episode_id)
            email_id = episode.get("scenario", {}).get("active_thread", {}).get("email_id", "EMAIL-001")
            return {"email_id": email_id}

        elif action_type == "ocr_process":
            return {"attachment_name": "document.pdf"}

        elif action_type == "erp_query":
            return {"query_key": "order_id", "query_value": "ORD-2024-001"}

        elif action_type == "security_flag":
            return {"email_id": "EMAIL-001", "threat_type": "prompt_injection"}

        elif action_type == "reply":
            return {
                "email_id": "EMAIL-001",
                "body": "Thank you for your email. We will respond shortly.",
                "department": "support",
            }

        elif action_type == "mcp_external_call":
            return {"tool": "slack", "payload": {}}

        return {}

    def seed(self, seed: Optional[int] = None) -> list:
        """Set random seed."""
        super().seed(seed)
        return [seed]


# Register environment with Gymnasium
def register_esig_env():
    """Register ESIG environment with Gymnasium."""
    if not HAS_GYMNASIUM:
        return  # Skip if gymnasium not available
    
    try:
        gym.register(
            id="ESIG-v1",
            entry_point="server.env.gymnasium_wrapper:ESIGEnv",
            max_episode_steps=20,
            kwargs={"task_id": "task1_easy"},
        )
    except gym.error.Error:
        # Already registered
        pass


# Auto-register on import
if HAS_GYMNASIUM:
    register_esig_env()
