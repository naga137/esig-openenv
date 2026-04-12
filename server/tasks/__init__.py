from .task1_triage import generate_scenario as gen_task1, build_initial_observation as obs_task1
from .task2_erp_lookup import generate_scenario as gen_task2, build_initial_observation as obs_task2
from .task3_adversarial import generate_scenario as gen_task3, build_initial_observation as obs_task3
from .task4_expert import generate_scenario as gen_task4, build_initial_observation as obs_task4

TASK_REGISTRY = {
    "task1_easy":   (gen_task1, obs_task1),
    "task2_medium": (gen_task2, obs_task2),
    "task3_hard":   (gen_task3, obs_task3),
    "task4_expert": (gen_task4, obs_task4),
}

__all__ = ["TASK_REGISTRY"]
