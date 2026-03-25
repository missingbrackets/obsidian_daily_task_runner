"""Carryover workflow – move incomplete tasks from yesterday to today's note."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from core.models import NoteFile, Task, TaskStatus
from core.task_writer import append_task_to_section


def find_yesterdays_note(notes: list[NoteFile], daily_folder: str) -> NoteFile | None:
    """Find yesterday's daily note."""
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    for n in notes:
        if n.folder == daily_folder and yesterday in n.path.stem:
            return n
    return None


def find_todays_note(notes: list[NoteFile], daily_folder: str) -> NoteFile | None:
    """Find today's daily note."""
    today = date.today().strftime("%Y-%m-%d")
    for n in notes:
        if n.folder == daily_folder and today in n.path.stem:
            return n
    return None


def get_carryover_tasks(yesterday_note: NoteFile) -> list[Task]:
    """Get incomplete tasks from yesterday's note."""
    return [t for t in yesterday_note.tasks if t.status == TaskStatus.OPEN]


def perform_carryover(
    carryover_tasks: list[Task],
    today_note_path: Path,
    section: str = "📥 Carryover From Yesterday",
) -> int:
    """Write carryover tasks into today's note under the specified section.

    Preserves project source labels so sync continues to work.
    Returns the number of tasks carried over.
    """
    count = 0
    for task in carryover_tasks:
        line = f"- [ ] {task.description}"
        if task.due_date:
            line += f" 📅 {task.due_date.isoformat()}"
        if task.priority != 3:
            pmap = {1: "🔺", 2: "⏫", 3: "🔼", 4: "🔽", 5: "⏬"}
            line += f" {pmap.get(task.priority, '')}"
        for tag in task.tags:
            line += f" #{tag}"
        # Propagate project source label if present
        if task.project_source and task.project_line:
            line += f" <!-- project:{task.project_source}:{task.project_line} -->"

        append_task_to_section(today_note_path, section, line)
        count += 1

    return count
