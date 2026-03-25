"""Overdue task review workflow.

Only surfaces overdue tasks from the Projects folder (source of truth).
"""

from __future__ import annotations

from datetime import date

from config import PROJECTS_FOLDER, CASE_PRICING_FOLDER
from core.models import NoteFile, Task, TaskStatus
from core.task_parser import get_all_tasks

_SOURCE_FOLDERS = (PROJECTS_FOLDER, CASE_PRICING_FOLDER)


def get_overdue_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open project/case-pricing tasks past their due date."""
    today = date.today()
    return sorted(
        [
            t for t in get_all_tasks(notes)
            if t.source_folder in _SOURCE_FOLDERS
            and t.status == TaskStatus.OPEN
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
        "by_project": _group_by_project(overdue),
        "by_age": _group_by_age(overdue),
    }


def _group_by_project(tasks: list[Task]) -> dict[str, list[Task]]:
    """Group by project file name."""
    groups: dict[str, list[Task]] = {}
    for t in tasks:
        groups.setdefault(t.file_path.stem, []).append(t)
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
