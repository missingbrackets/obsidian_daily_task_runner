"""Daily task selection – pick today's focus tasks from all open tasks."""

from __future__ import annotations

from datetime import date

from core.models import NoteFile, Task, TaskStatus
from core.task_parser import get_all_tasks


def get_candidates(notes: list[NoteFile]) -> list[Task]:
    """Get all open tasks suitable for today, sorted by priority then due date."""
    today = date.today()
    open_tasks = [t for t in get_all_tasks(notes) if t.status == TaskStatus.OPEN]

    def sort_key(t: Task) -> tuple:
        # Priority first (lower = more important), then due date (sooner = first)
        due_sort = t.due_date if t.due_date else date.max
        return (t.priority, due_sort)

    return sorted(open_tasks, key=sort_key)


def filter_by_folder(tasks: list[Task], folder: str) -> list[Task]:
    return [t for t in tasks if t.source_folder == folder]


def filter_overdue_first(tasks: list[Task]) -> list[Task]:
    """Put overdue tasks at the top."""
    overdue = [t for t in tasks if t.is_overdue]
    due_today = [t for t in tasks if t.is_due_today and not t.is_overdue]
    rest = [t for t in tasks if not t.is_overdue and not t.is_due_today]
    return overdue + due_today + rest
