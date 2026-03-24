"""Daily task selection – unified workflow.

Presents tasks in priority order:
1. Not completed from yesterday (daily note carryover)
2. Overdue from projects (grouped by project)
3. Due today (grouped by project)
4. Due soon / this week (grouped by project)

User selects tasks to add to today's daily note.
Selecting a yesterday-carryover task also moves it to yesterday's
"Move to tomorrow" section and ticks it there.
"""

from __future__ import annotations

from datetime import date, timedelta

from config import PROJECTS_FOLDER, DAILY_FOLDER
from core.models import NoteFile, Task, TaskStatus
from core.task_parser import get_all_tasks
from workflows.weekly_planning import get_weekly_note_tasks


def _group_by_project(tasks: list[Task]) -> dict[str, list[Task]]:
    """Group tasks by their project file name."""
    groups: dict[str, list[Task]] = {}
    for t in tasks:
        key = t.file_path.stem
        groups.setdefault(key, []).append(t)
    return groups


def get_yesterday_incomplete(notes: list[NoteFile]) -> list[Task]:
    """Open tasks from yesterday's daily note."""
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    tasks: list[Task] = []
    for n in notes:
        if n.folder == DAILY_FOLDER and yesterday in n.path.stem:
            tasks.extend(t for t in n.tasks if t.status == TaskStatus.OPEN)
    return tasks


def get_overdue_project_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open project tasks past their due date."""
    today = date.today()
    return sorted(
        [
            t for t in get_all_tasks(notes)
            if t.source_folder == PROJECTS_FOLDER
            and t.status == TaskStatus.OPEN
            and t.due_date is not None
            and t.due_date < today
        ],
        key=lambda t: (t.due_date, t.priority),
    )


def get_due_today_project_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open project tasks due today."""
    today = date.today()
    return [
        t for t in get_all_tasks(notes)
        if t.source_folder == PROJECTS_FOLDER
        and t.status == TaskStatus.OPEN
        and t.due_date == today
    ]


def get_due_soon_project_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open project tasks due in the next 7 days (excluding today and overdue)."""
    today = date.today()
    soon = today + timedelta(days=7)
    return sorted(
        [
            t for t in get_all_tasks(notes)
            if t.source_folder == PROJECTS_FOLDER
            and t.status == TaskStatus.OPEN
            and t.due_date is not None
            and today < t.due_date <= soon
        ],
        key=lambda t: (t.due_date, t.priority),
    )


def get_weekly_note_open_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open tasks from this week's weekly note (for display alongside project tasks)."""
    return get_weekly_note_tasks(notes)


def daily_selection_groups(notes: list[NoteFile]) -> dict:
    """Return all groups for the unified daily selection view."""
    yesterday = get_yesterday_incomplete(notes)
    overdue = get_overdue_project_tasks(notes)
    due_today = get_due_today_project_tasks(notes)
    due_soon = get_due_soon_project_tasks(notes)

    return {
        "yesterday_incomplete": yesterday,
        "overdue": overdue,
        "overdue_by_project": _group_by_project(overdue),
        "due_today": due_today,
        "due_today_by_project": _group_by_project(due_today),
        "due_soon": due_soon,
        "due_soon_by_project": _group_by_project(due_soon),
    }
