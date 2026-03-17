"""Weekly planning workflow.

Surfaces tasks due this week, groups by category, and identifies
tasks that need scheduling.
"""

from __future__ import annotations

from datetime import date, timedelta

from core.models import NoteFile, Task, TaskStatus
from core.task_parser import get_all_tasks


def _week_bounds(ref: date | None = None) -> tuple[date, date]:
    """Return (Monday, Sunday) of the week containing ref."""
    ref = ref or date.today()
    monday = ref - timedelta(days=ref.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_this_week_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open tasks due this week."""
    mon, sun = _week_bounds()
    return [
        t for t in get_all_tasks(notes)
        if t.status == TaskStatus.OPEN
        and t.due_date is not None
        and mon <= t.due_date <= sun
    ]


def get_next_week_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open tasks due next week."""
    mon, sun = _week_bounds(date.today() + timedelta(weeks=1))
    return [
        t for t in get_all_tasks(notes)
        if t.status == TaskStatus.OPEN
        and t.due_date is not None
        and mon <= t.due_date <= sun
    ]


def get_unscheduled_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open tasks with no due date and no scheduled date."""
    return [
        t for t in get_all_tasks(notes)
        if t.status == TaskStatus.OPEN
        and t.due_date is None
        and t.scheduled_date is None
    ]


def weekly_summary(notes: list[NoteFile]) -> dict:
    """Return weekly planning data."""
    this_week = get_this_week_tasks(notes)
    return {
        "this_week": this_week,
        "next_week": get_next_week_tasks(notes),
        "unscheduled": get_unscheduled_tasks(notes),
        "this_week_by_priority": sorted(this_week, key=lambda t: t.priority),
        "this_week_by_folder": _group_by_folder(this_week),
    }


def _group_by_folder(tasks: list[Task]) -> dict[str, list[Task]]:
    groups: dict[str, list[Task]] = {}
    for t in tasks:
        groups.setdefault(t.source_folder, []).append(t)
    return groups
