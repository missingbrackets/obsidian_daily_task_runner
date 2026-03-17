"""AI planning layer.

Phase 1: Rule-based prioritization.
Phase 2 (future): LLM integration via a simple interface.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from core.models import Task


class Planner(Protocol):
    """Interface for plugging in different planning strategies."""

    def rank_tasks(self, tasks: list[Task], top_n: int = 5) -> list[Task]:
        """Return the top N recommended tasks for today."""
        ...

    def suggest_schedule(self, tasks: list[Task]) -> dict[str, list[Task]]:
        """Suggest a daily schedule grouping."""
        ...


class RuleBasedPlanner:
    """Simple rule-based prioritization.

    Scoring:
      - Overdue tasks get +50 points
      - Due today gets +30 points
      - Due this week gets +15 points
      - Priority bonus: (6 - priority) * 10   (so priority 1 → 50 pts)
      - Tasks from Case Pricing get +5 (deadline-driven)
    """

    def rank_tasks(self, tasks: list[Task], top_n: int = 5) -> list[Task]:
        scored = [(t, self._score(t)) for t in tasks]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scored[:top_n]]

    def suggest_schedule(self, tasks: list[Task]) -> dict[str, list[Task]]:
        """Group tasks into morning / afternoon / if-time buckets."""
        ranked = self.rank_tasks(tasks, top_n=len(tasks))

        morning: list[Task] = []
        afternoon: list[Task] = []
        if_time: list[Task] = []

        for i, t in enumerate(ranked):
            if i < 3:
                morning.append(t)
            elif i < 6:
                afternoon.append(t)
            else:
                if_time.append(t)

        return {
            "🌅 Morning (Top Priority)": morning,
            "☀️ Afternoon": afternoon,
            "🌙 If Time Permits": if_time,
        }

    def _score(self, task: Task) -> float:
        score = 0.0
        today = date.today()

        if task.is_overdue:
            score += 50
            # Extra urgency for very overdue
            if task.due_date:
                days_overdue = (today - task.due_date).days
                score += min(days_overdue * 2, 20)

        if task.is_due_today:
            score += 30

        if task.due_date and not task.is_overdue and not task.is_due_today:
            days_until = (task.due_date - today).days
            if days_until <= 7:
                score += 15

        # Priority bonus
        score += (6 - task.priority) * 10

        # Case pricing bonus
        if "Case Pricing" in task.source_folder:
            score += 5

        return score


# ── Future LLM integration stub ───────────────────────────────────────

class LLMPlanner:
    """Placeholder for future LLM-based planning.

    To implement:
    1. Set OPENAI_API_KEY or ANTHROPIC_API_KEY env var
    2. Override rank_tasks / suggest_schedule with LLM calls
    3. Use RuleBasedPlanner output as a starting point for the prompt
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._fallback = RuleBasedPlanner()

    def rank_tasks(self, tasks: list[Task], top_n: int = 5) -> list[Task]:
        # TODO: Replace with LLM call
        return self._fallback.rank_tasks(tasks, top_n)

    def suggest_schedule(self, tasks: list[Task]) -> dict[str, list[Task]]:
        # TODO: Replace with LLM call
        return self._fallback.suggest_schedule(tasks)


def get_planner(use_llm: bool = False) -> RuleBasedPlanner | LLMPlanner:
    if use_llm:
        return LLMPlanner()
    return RuleBasedPlanner()
