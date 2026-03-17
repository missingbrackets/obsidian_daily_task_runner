"""Parse markdown checkbox tasks with Obsidian Tasks plugin metadata.

Supported metadata:
  - [x] / [ ] / [-]  → done / open / cancelled
  - 📅 YYYY-MM-DD     → due date
  - ⏳ YYYY-MM-DD     → scheduled date
  - ✅ YYYY-MM-DD     → done date
  - 🔺 ⏫ 🔼 🔽 ⏬    → priority markers
  - #tag              → tags
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from config import DEFAULT_PRIORITY, PRIORITY_MAP
from core.models import NoteFile, Task, TaskStatus

_CHECKBOX_RE = re.compile(r"^(\s*)-\s+\[([ xX\-])\]\s+(.*)")
_DUE_RE = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})")
_SCHEDULED_RE = re.compile(r"⏳\s*(\d{4}-\d{2}-\d{2})")
_DONE_DATE_RE = re.compile(r"✅\s*(\d{4}-\d{2}-\d{2})")
_TAG_RE = re.compile(r"#([\w/\-]+)")

# Strip metadata markers from description for display
_META_STRIP_RE = re.compile(
    r"[📅⏳✅🔺⏫🔼🔽⏬]\s*\d{4}-\d{2}-\d{2}|[🔺⏫🔼🔽⏬]|#[\w/\-]+"
)


def _parse_date(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_task_line(line: str, file_path: Path, line_number: int) -> Task | None:
    """Parse a single line into a Task, or None if not a task."""
    m = _CHECKBOX_RE.match(line)
    if not m:
        return None

    marker = m.group(2)
    body = m.group(3)

    if marker in ("x", "X"):
        status = TaskStatus.DONE
    elif marker == "-":
        status = TaskStatus.CANCELLED
    else:
        status = TaskStatus.OPEN

    # Extract metadata
    due_match = _DUE_RE.search(body)
    sched_match = _SCHEDULED_RE.search(body)
    done_match = _DONE_DATE_RE.search(body)

    due_date = _parse_date(due_match.group(1)) if due_match else None
    scheduled_date = _parse_date(sched_match.group(1)) if sched_match else None
    done_date = _parse_date(done_match.group(1)) if done_match else None

    # Priority
    priority = DEFAULT_PRIORITY
    for emoji, pval in PRIORITY_MAP.items():
        if emoji in body:
            priority = pval
            break

    # Tags
    tags = _TAG_RE.findall(body)

    # Clean description
    description = _META_STRIP_RE.sub("", body).strip()
    description = re.sub(r"\s{2,}", " ", description)

    return Task(
        raw_line=line,
        description=description,
        status=status,
        file_path=file_path,
        line_number=line_number,
        due_date=due_date,
        scheduled_date=scheduled_date,
        done_date=done_date,
        priority=priority,
        tags=tags,
    )


def parse_file(note: NoteFile) -> NoteFile:
    """Parse all tasks in a NoteFile and populate note.tasks."""
    note.tasks = []
    current_section = ""

    lines = note.path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Track current heading
        if stripped.startswith("#"):
            current_section = stripped.lstrip("#").strip()
            continue

        task = parse_task_line(line, note.path, i)
        if task:
            task.section = current_section
            task.source_folder = note.folder
            note.tasks.append(task)

    return note


def parse_all(notes: list[NoteFile]) -> list[NoteFile]:
    """Parse tasks for all notes."""
    return [parse_file(n) for n in notes]


def get_all_tasks(notes: list[NoteFile]) -> list[Task]:
    """Flatten all tasks from parsed notes."""
    tasks: list[Task] = []
    for n in notes:
        tasks.extend(n.tasks)
    return tasks
