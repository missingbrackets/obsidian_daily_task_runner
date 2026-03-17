"""Data models for tasks and notes."""

from __future__ import annotations

import dataclasses
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional


class TaskStatus(Enum):
    OPEN = "open"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclasses.dataclass
class Task:
    """Represents a single markdown checkbox task."""

    raw_line: str               # original line text
    description: str            # task text without metadata markers
    status: TaskStatus
    file_path: Path             # absolute path to the source .md file
    line_number: int            # 1-based line number in the file
    due_date: Optional[date] = None
    scheduled_date: Optional[date] = None
    done_date: Optional[date] = None
    priority: int = 3           # 1 (highest) – 5 (lowest)
    tags: list[str] = dataclasses.field(default_factory=list)
    section: str = ""           # heading the task lives under
    source_folder: str = ""     # which scan folder it came from

    @property
    def is_overdue(self) -> bool:
        return (
            self.status == TaskStatus.OPEN
            and self.due_date is not None
            and self.due_date < date.today()
        )

    @property
    def is_due_today(self) -> bool:
        return (
            self.status == TaskStatus.OPEN
            and self.due_date is not None
            and self.due_date == date.today()
        )


@dataclasses.dataclass
class NoteFile:
    """Represents a markdown file in the vault."""

    path: Path
    relative_path: str
    folder: str          # which scan folder
    tasks: list[Task] = dataclasses.field(default_factory=list)
