"""Weekly planning workflow.

Projects are the source of truth for tasks.
At the beginning of the week, incomplete project tasks due this week
should be pulled into the weekly note.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from config import PROJECTS_FOLDER, WEEKLY_FOLDER
from core.models import NoteFile, Task, TaskStatus
from core.task_parser import get_all_tasks
from core.task_writer import append_task_to_section, build_project_source_comment


def _week_bounds(ref: date | None = None) -> tuple[date, date]:
    """Return (Monday, Sunday) of the week containing ref."""
    ref = ref or date.today()
    monday = ref - timedelta(days=ref.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_project_tasks_due_this_week(notes: list[NoteFile]) -> list[Task]:
    """Incomplete project tasks due this week (the source of truth)."""
    mon, sun = _week_bounds()
    return [
        t for t in get_all_tasks(notes)
        if t.source_folder == PROJECTS_FOLDER
        and t.status == TaskStatus.OPEN
        and t.due_date is not None
        and mon <= t.due_date <= sun
    ]


def get_project_tasks_overdue(notes: list[NoteFile]) -> list[Task]:
    """Incomplete project tasks that are already overdue."""
    today = date.today()
    return [
        t for t in get_all_tasks(notes)
        if t.source_folder == PROJECTS_FOLDER
        and t.status == TaskStatus.OPEN
        and t.due_date is not None
        and t.due_date < today
    ]


def get_project_tasks_due_next_week(notes: list[NoteFile]) -> list[Task]:
    """Incomplete project tasks due next week."""
    mon, sun = _week_bounds(date.today() + timedelta(weeks=1))
    return [
        t for t in get_all_tasks(notes)
        if t.source_folder == PROJECTS_FOLDER
        and t.status == TaskStatus.OPEN
        and t.due_date is not None
        and mon <= t.due_date <= sun
    ]


def get_weekly_note_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open tasks already in this week's weekly note."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_str = monday.strftime("%Y-%m-%d")
    tasks: list[Task] = []
    for n in notes:
        if n.folder == WEEKLY_FOLDER and week_str in n.path.stem:
            tasks.extend(t for t in n.tasks if t.status == TaskStatus.OPEN)
    return tasks


def find_weekly_note(notes: list[NoteFile]) -> NoteFile | None:
    """Find this week's weekly note."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_str = monday.strftime("%Y-%m-%d")
    for n in notes:
        if n.folder == WEEKLY_FOLDER and week_str in n.path.stem:
            return n
    return None


def get_unscheduled_project_tasks(notes: list[NoteFile]) -> list[Task]:
    """Open project tasks with no due date."""
    return [
        t for t in get_all_tasks(notes)
        if t.source_folder == PROJECTS_FOLDER
        and t.status == TaskStatus.OPEN
        and t.due_date is None
        and t.scheduled_date is None
    ]


# The category sub-sections in the weekly note template
WEEKLY_CATEGORIES = [
    "🧑‍💻 Work",
    "🏠 Life Admin",
    "💪 Health",
    "🌱 Personal / Growth",
]


def _build_task_line(task: Task, vault_path: str) -> str:
    """Build a markdown task line with metadata and project source."""
    line = f"- [ ] {task.description}"
    if task.due_date:
        line += f" 📅 {task.due_date.isoformat()}"
    if task.priority != 3:
        pmap = {1: "🔺", 2: "⏫", 3: "🔼", 4: "🔽", 5: "⏬"}
        line += f" {pmap.get(task.priority, '')}"
    for tag in task.tags:
        line += f" #{tag}"
    line += f" {build_project_source_comment(task, vault_path)}"
    return line


def write_tasks_to_weekly_note(
    weekly_note_path: Path,
    task_assignments: dict[str, list[Task]],
    vault_path: str,
) -> int:
    """Write project tasks into the weekly note under category sub-sections.

    task_assignments maps category heading (e.g. "🧑‍💻 Work") to tasks.
    Returns total count written.
    """
    count = 0
    for category, tasks in task_assignments.items():
        for task in tasks:
            line = _build_task_line(task, vault_path)
            append_task_to_section(weekly_note_path, category, line)
            count += 1
    return count


def weekly_summary(notes: list[NoteFile]) -> dict:
    """Return weekly planning data sourced from projects."""
    this_week = get_project_tasks_due_this_week(notes)
    overdue = get_project_tasks_overdue(notes)
    weekly_note_tasks = get_weekly_note_tasks(notes)

    return {
        "project_tasks_this_week": this_week,
        "project_tasks_overdue": overdue,
        "project_tasks_next_week": get_project_tasks_due_next_week(notes),
        "weekly_note_tasks": weekly_note_tasks,
        "unscheduled": get_unscheduled_project_tasks(notes),
        "this_week_by_priority": sorted(
            this_week + overdue, key=lambda t: (t.priority, t.due_date or date.max)
        ),
    }
