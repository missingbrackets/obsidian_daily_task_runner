"""Morning review workflow.

Gathers today's tasks across all folders, highlights overdue items,
and shows carryover from yesterday's daily note.
"""

from __future__ import annotations

from datetime import date, timedelta

from core.models import NoteFile, Task, TaskStatus
from core.task_parser import get_all_tasks


def get_todays_tasks(notes: list[NoteFile]) -> list[Task]:
    """Tasks due today or scheduled for today."""
    today = date.today()
    return [
        t for t in get_all_tasks(notes)
        if t.status == TaskStatus.OPEN
        and (t.due_date == today or t.scheduled_date == today)
    ]


def get_overdue_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open tasks with a due date before today."""
    return [t for t in get_all_tasks(notes) if t.is_overdue]


def get_yesterdays_incomplete(notes: list[NoteFile], daily_folder: str) -> list[Task]:
    """Open tasks from yesterday's daily note."""
    yesterday = date.today() - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    tasks: list[Task] = []
    for n in notes:
        if n.folder != daily_folder:
            continue
        if yesterday_str in n.path.stem:
            tasks.extend(t for t in n.tasks if t.status == TaskStatus.OPEN)
    return tasks


def morning_summary(notes: list[NoteFile], daily_folder: str) -> dict:
    """Return a dict with all morning review data."""
    all_tasks = get_all_tasks(notes)
    open_tasks = [t for t in all_tasks if t.status == TaskStatus.OPEN]

    return {
        "today": get_todays_tasks(notes),
        "overdue": get_overdue_tasks(notes),
        "yesterday_incomplete": get_yesterdays_incomplete(notes, daily_folder),
        "total_open": len(open_tasks),
        "total_tasks": len(all_tasks),
        "by_folder": _group_by_folder(open_tasks),
    }


def _group_by_folder(tasks: list[Task]) -> dict[str, list[Task]]:
    groups: dict[str, list[Task]] = {}
    for t in tasks:
        groups.setdefault(t.source_folder, []).append(t)
    return groups
