"""Daily task selection – pick today's tasks from this week's weekly note."""

from __future__ import annotations

from datetime import date

from core.models import NoteFile, Task, TaskStatus
from workflows.weekly_planning import get_weekly_note_tasks


def get_candidates(notes: list[NoteFile]) -> list[Task]:
    """Get open tasks from this week's weekly note, sorted by priority then due date."""
    open_tasks = get_weekly_note_tasks(notes)

    def sort_key(t: Task) -> tuple:
        due_sort = t.due_date if t.due_date else date.max
        return (t.priority, due_sort)

    return sorted(open_tasks, key=sort_key)


def filter_overdue_first(tasks: list[Task]) -> list[Task]:
    """Put overdue tasks at the top."""
    overdue = [t for t in tasks if t.is_overdue]
    due_today = [t for t in tasks if t.is_due_today and not t.is_overdue]
    rest = [t for t in tasks if not t.is_overdue and not t.is_due_today]
    return overdue + due_today + rest
