"""Safely update markdown files – toggle tasks, insert lines, sync across files.

All writes use atomic-ish patterns: read -> modify in memory -> write back.
A .bak file is created before each write for safety.
"""

from __future__ import annotations

import re
import shutil
from datetime import date, timedelta
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


# ── Checkbox toggling ──────────────────────────────────────────────────

def _toggle_line(line: str, new_status: TaskStatus) -> str:
    """Toggle the checkbox marker in a single line string."""
    if new_status == TaskStatus.DONE:
        line = line.replace("[ ]", "[x]", 1).replace("[-]", "[x]", 1)
    elif new_status == TaskStatus.OPEN:
        line = line.replace("[x]", "[ ]", 1).replace("[X]", "[ ]", 1).replace("[-]", "[ ]", 1)
    elif new_status == TaskStatus.CANCELLED:
        line = line.replace("[ ]", "[-]", 1).replace("[x]", "[-]", 1).replace("[X]", "[-]", 1)
    return line


def toggle_task(task: Task, new_status: TaskStatus) -> None:
    """Toggle a task's checkbox in its source file."""
    lines = _read_lines(task.file_path)
    idx = task.line_number - 1

    if idx >= len(lines):
        raise IndexError(f"Line {task.line_number} out of range in {task.file_path}")

    lines[idx] = _toggle_line(lines[idx], new_status)
    _write_lines(task.file_path, lines)


# ── Synced status change (project <-> weekly <-> daily) ────────────────

def sync_task_status(
    task: Task,
    new_status: TaskStatus,
    vault_path: str,
    notes: list | None = None,
) -> list[str]:
    """Toggle a task AND propagate the change to linked files.

    Returns a list of file names that were updated (for UI feedback).
    """
    updated: list[str] = []
    vault = Path(vault_path).expanduser().resolve()

    # 1. Toggle the task in the file it lives in
    toggle_task(task, new_status)
    updated.append(task.file_path.name)

    # 2. If the task carries a project_source, toggle in the project file too
    if task.project_source and task.project_line:
        proj_path = vault / task.project_source
        if proj_path.is_file():
            _toggle_line_in_file(proj_path, task.project_line, new_status)
            updated.append(proj_path.name)

    # 3. If this task lives in a project file, find matching tasks in weekly/daily/
    #    direct-report notes by scanning for the project source comment pointing at
    #    this file+line.
    from config import WEEKLY_FOLDER, DAILY_FOLDER, DIRECT_REPORTS_FOLDER
    source_rel = str(task.file_path.relative_to(vault)) if _is_under(task.file_path, vault) else ""

    if source_rel:
        pattern = f"<!-- project:{source_rel}:{task.line_number} -->"
        for folder in (WEEKLY_FOLDER, DAILY_FOLDER, DIRECT_REPORTS_FOLDER):
            folder_path = vault / folder
            if not folder_path.is_dir():
                continue
            for md_file in folder_path.rglob("*.md"):
                hits = _find_lines_containing(md_file, pattern)
                if hits:
                    lines = _read_lines(md_file)
                    for line_num in hits:
                        lines[line_num - 1] = _toggle_line(lines[line_num - 1], new_status)
                    _write_lines(md_file, lines)
                    updated.append(md_file.name)

    # 4. If this task lives in a weekly/daily/direct-report note and has a project
    #    source, also find sibling copies in other downstream notes.
    if task.project_source and task.project_line:
        pattern = f"<!-- project:{task.project_source}:{task.project_line} -->"
        for folder in (WEEKLY_FOLDER, DAILY_FOLDER, DIRECT_REPORTS_FOLDER):
            folder_path = vault / folder
            if not folder_path.is_dir():
                continue
            for md_file in folder_path.rglob("*.md"):
                if md_file == task.file_path:
                    continue  # already toggled
                hits = _find_lines_containing(md_file, pattern)
                if hits:
                    lines = _read_lines(md_file)
                    for line_num in hits:
                        lines[line_num - 1] = _toggle_line(lines[line_num - 1], new_status)
                    _write_lines(md_file, lines)
                    if md_file.name not in updated:
                        updated.append(md_file.name)

    return updated


def _toggle_line_in_file(path: Path, line_number: int, new_status: TaskStatus) -> None:
    """Toggle a specific line in a file by line number."""
    lines = _read_lines(path)
    idx = line_number - 1
    if idx >= len(lines):
        return  # silently skip if line number is stale
    lines[idx] = _toggle_line(lines[idx], new_status)
    _write_lines(path, lines)


def _find_lines_containing(path: Path, pattern: str) -> list[int]:
    """Return 1-based line numbers containing the exact pattern string."""
    hits: list[int] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return hits
    for i, line in enumerate(lines, start=1):
        if pattern in line:
            hits.append(i)
    return hits


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


# ── Project source comment helper ──────────────────────────────────────

def build_project_source_comment(task: Task, vault_path: str) -> str:
    """Build an HTML comment that tracks which project file+line a task came from.

    Example: <!-- project:To Do/03 Projects/MyProject.md:42 -->
    """
    vault = Path(vault_path).expanduser().resolve()
    try:
        rel = str(task.file_path.relative_to(vault))
    except ValueError:
        rel = str(task.file_path)
    return f"<!-- project:{rel}:{task.line_number} -->"


# ── Section appending ──────────────────────────────────────────────────

def append_task_to_section(file_path: Path, section_heading: str, task_line: str) -> None:
    """Append a task line after the specified section heading.

    Matching is flexible: the heading in the file may contain extra emojis or
    formatting, so we check whether the stripped search term appears *within*
    the heading line (after stripping ``#`` prefixes from both).
    """
    lines = _read_lines(file_path)
    insert_idx = None
    needle = section_heading.lstrip("#").strip()

    for i, line in enumerate(lines):
        stripped = line.strip().lstrip("#").strip()
        # Exact match OR the needle is contained in the heading
        if stripped == needle or needle in stripped:
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


# ── Line replacement ──────────────────────────────────────────────────

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


# ── Due date editing ──────────────────────────────────────────────────

def update_due_date(task: Task, new_date: str) -> None:
    """Update (or add) the due date on a task line in its source file.

    new_date should be a YYYY-MM-DD string.
    """
    lines = _read_lines(task.file_path)
    idx = task.line_number - 1
    if idx >= len(lines):
        raise IndexError(f"Line {task.line_number} out of range in {task.file_path}")

    line = lines[idx]
    due_pattern = re.compile(r"📅\s*\d{4}-\d{2}-\d{2}")

    if due_pattern.search(line):
        line = due_pattern.sub(f"📅 {new_date}", line)
    else:
        # Insert due date before the newline
        line = line.rstrip("\n") + f" 📅 {new_date}\n"

    lines[idx] = line
    _write_lines(task.file_path, lines)


def sync_due_date(
    task: Task,
    new_date: str,
    vault_path: str,
) -> list[str]:
    """Update due date on a task AND propagate to linked files.

    Returns list of updated file names.
    """
    updated: list[str] = []
    vault = Path(vault_path).expanduser().resolve()

    # 1. Update in the source file
    update_due_date(task, new_date)
    updated.append(task.file_path.name)

    # 2. Update in the project file if this is a downstream copy
    if task.project_source and task.project_line:
        proj_path = vault / task.project_source
        if proj_path.is_file():
            _update_due_date_at_line(proj_path, task.project_line, new_date)
            updated.append(proj_path.name)

    # 3. If this task lives in a project file, update downstream copies in all
    #    downstream folders (weekly, daily, direct reports).
    source_rel = str(task.file_path.relative_to(vault)) if _is_under(task.file_path, vault) else ""
    if source_rel:
        pattern = f"<!-- project:{source_rel}:{task.line_number} -->"
        from config import WEEKLY_FOLDER, DAILY_FOLDER, DIRECT_REPORTS_FOLDER
        for folder in (WEEKLY_FOLDER, DAILY_FOLDER, DIRECT_REPORTS_FOLDER):
            folder_path = vault / folder
            if not folder_path.is_dir():
                continue
            for md_file in folder_path.rglob("*.md"):
                hits = _find_lines_containing(md_file, pattern)
                if hits:
                    for line_num in hits:
                        _update_due_date_at_line(md_file, line_num, new_date)
                    updated.append(md_file.name)

    # 4. Update sibling copies sharing the same project source.
    if task.project_source and task.project_line:
        pattern = f"<!-- project:{task.project_source}:{task.project_line} -->"
        from config import WEEKLY_FOLDER, DAILY_FOLDER, DIRECT_REPORTS_FOLDER
        for folder in (WEEKLY_FOLDER, DAILY_FOLDER, DIRECT_REPORTS_FOLDER):
            folder_path = vault / folder
            if not folder_path.is_dir():
                continue
            for md_file in folder_path.rglob("*.md"):
                if md_file == task.file_path:
                    continue
                hits = _find_lines_containing(md_file, pattern)
                if hits:
                    for line_num in hits:
                        _update_due_date_at_line(md_file, line_num, new_date)
                    if md_file.name not in updated:
                        updated.append(md_file.name)

    return updated


# ── Carryover: move task to "Move to tomorrow" and tick it ─────────────

def move_task_to_tomorrow_section(task: Task) -> None:
    """In yesterday's daily note: tick the task where it is, and add a
    ticked copy under the 'Move to tomorrow' marker.

    This marks the task as handled in yesterday's note so it no longer
    appears as incomplete.
    """
    lines = _read_lines(task.file_path)
    idx = task.line_number - 1
    if idx >= len(lines):
        return

    # 1. Tick the original line
    lines[idx] = _toggle_line(lines[idx], TaskStatus.DONE)

    # 2. Find the "Move to tomorrow" marker (bold line, not a heading)
    ticked_line = f"- [x] {task.description}"
    if task.due_date:
        ticked_line += f" 📅 {task.due_date.isoformat()}"
    if task.project_source and task.project_line:
        ticked_line += f" <!-- project:{task.project_source}:{task.project_line} -->"
    if not ticked_line.endswith("\n"):
        ticked_line += "\n"

    insert_idx = None
    for i, line in enumerate(lines):
        if "move to tomorrow" in line.lower():
            insert_idx = i + 1
            break

    if insert_idx is not None:
        lines.insert(insert_idx, ticked_line)
    else:
        # Fallback: append at end
        lines.append(ticked_line)

    _write_lines(task.file_path, lines)


def _update_due_date_at_line(path: Path, line_number: int, new_date: str) -> None:
    """Update due date on a specific line in a file."""
    lines = _read_lines(path)
    idx = line_number - 1
    if idx >= len(lines):
        return
    line = lines[idx]
    due_pattern = re.compile(r"📅\s*\d{4}-\d{2}-\d{2}")
    if due_pattern.search(line):
        line = due_pattern.sub(f"📅 {new_date}", line)
    else:
        line = line.rstrip("\n") + f" 📅 {new_date}\n"
    lines[idx] = line
    _write_lines(path, lines)
