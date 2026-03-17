"""Safely update markdown files – toggle tasks, insert lines, etc.

All writes use atomic-ish patterns: read → modify in memory → write back.
A .bak file is created before each write for safety.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from core.models import Task, TaskStatus


def _backup(path: Path) -> Path:
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    return bak


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _write_lines(path: Path, lines: list[str]) -> None:
    _backup(path)
    path.write_text("".join(lines), encoding="utf-8")


def toggle_task(task: Task, new_status: TaskStatus) -> None:
    """Toggle a task's checkbox in its source file."""
    lines = _read_lines(task.file_path)
    idx = task.line_number - 1

    if idx >= len(lines):
        raise IndexError(f"Line {task.line_number} out of range in {task.file_path}")

    line = lines[idx]

    if new_status == TaskStatus.DONE:
        line = line.replace("[ ]", "[x]", 1).replace("[-]", "[x]", 1)
    elif new_status == TaskStatus.OPEN:
        line = line.replace("[x]", "[ ]", 1).replace("[X]", "[ ]", 1).replace("[-]", "[ ]", 1)
    elif new_status == TaskStatus.CANCELLED:
        line = line.replace("[ ]", "[-]", 1).replace("[x]", "[-]", 1).replace("[X]", "[-]", 1)

    lines[idx] = line
    _write_lines(task.file_path, lines)


def append_task_to_section(file_path: Path, section_heading: str, task_line: str) -> None:
    """Append a task line after the specified section heading."""
    lines = _read_lines(file_path)
    insert_idx = None

    for i, line in enumerate(lines):
        if line.strip().lstrip("#").strip() == section_heading.lstrip("#").strip():
            # Find end of section (next heading or EOF)
            insert_idx = i + 1
            while insert_idx < len(lines):
                next_line = lines[insert_idx].strip()
                if next_line.startswith("#"):
                    break
                if next_line == "":
                    insert_idx += 1
                    continue
                insert_idx += 1
            break

    if insert_idx is None:
        # Section not found – append at end
        insert_idx = len(lines)

    if not task_line.endswith("\n"):
        task_line += "\n"

    lines.insert(insert_idx, task_line)
    _write_lines(file_path, lines)


def replace_line(file_path: Path, line_number: int, new_line: str) -> None:
    """Replace a specific line in a file."""
    lines = _read_lines(file_path)
    idx = line_number - 1
    if idx >= len(lines):
        raise IndexError(f"Line {line_number} out of range in {file_path}")
    if not new_line.endswith("\n"):
        new_line += "\n"
    lines[idx] = new_line
    _write_lines(file_path, lines)
