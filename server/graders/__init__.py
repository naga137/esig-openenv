from .grader_easy   import grade as grade_easy
from .grader_medium import grade as grade_medium
from .grader_hard   import grade as grade_hard
from .grader_expert import grade as grade_expert

GRADER_REGISTRY = {
    "task1_easy":   grade_easy,
    "task2_medium": grade_medium,
    "task3_hard":   grade_hard,
    "task4_expert": grade_expert,
}

__all__ = ["GRADER_REGISTRY"]
