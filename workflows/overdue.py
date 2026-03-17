"""Overdue task review workflow."""

from __future__ import annotations

from datetime import date

from core.models import NoteFile, Task, TaskStatus
from core.task_parser import get_all_tasks


def get_overdue_tasks(notes: list[NoteFile]) -> list[Task]:
    """All open tasks past their due date."""
    today = date.today()
    return sorted(
        [
            t for t in get_all_tasks(notes)
            if t.status == TaskStatus.OPEN
            and t.due_date is not None
            and t.due_date < today
        ],
        key=lambda t: (t.due_date, t.priority),
    )


def overdue_summary(notes: list[NoteFile]) -> dict:
    overdue = get_overdue_tasks(notes)
    return {
        "overdue": overdue,
        "count": len(overdue),
        "by_folder": _group_by_folder(overdue),
        "by_age": _group_by_age(overdue),
    }


def _group_by_folder(tasks: list[Task]) -> dict[str, list[Task]]:
    groups: dict[str, list[Task]] = {}
    for t in tasks:
        groups.setdefault(t.source_folder, []).append(t)
    return groups


def _group_by_age(tasks: list[Task]) -> dict[str, list[Task]]:
    """Group by how overdue: 1 day, 2-7 days, 1-2 weeks, 2+ weeks."""
    today = date.today()
    groups: dict[str, list[Task]] = {
        "1 day": [],
        "2-7 days": [],
        "1-2 weeks": [],
        "2+ weeks": [],
    }
    for t in tasks:
        if t.due_date is None:
            continue
        days = (today - t.due_date).days
        if days <= 1:
            groups["1 day"].append(t)
        elif days <= 7:
            groups["2-7 days"].append(t)
        elif days <= 14:
            groups["1-2 weeks"].append(t)
        else:
            groups["2+ weeks"].append(t)
    return groups
