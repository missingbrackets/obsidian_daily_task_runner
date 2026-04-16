"""Direct reports planning workflow.

Each direct report gets a subfolder under `DIRECT_REPORTS_FOLDER`, with one
dated markdown file per day (YYYY-MM-DD.md). Reports are auto-detected:
any subfolder under `DIRECT_REPORTS_FOLDER` is treated as a report.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from config import DIRECT_REPORTS_FOLDER

# Section headings in the direct-report daily template. Kept in sync with
# `templates.engine.DIRECT_REPORT_DAILY_TEMPLATE`.
SECTION_TASKS = "✅ Tasks / To Delegate"
SECTION_TALKING_POINTS = "💬 1:1 Talking Points"
SECTION_NOTES = "🗒️ Notes"


def list_direct_reports(vault_path: str) -> list[str]:
    """Return sorted list of direct report names (subfolders).

    Returns an empty list if the direct reports folder doesn't exist yet.
    """
    folder = Path(vault_path).expanduser() / DIRECT_REPORTS_FOLDER
    if not folder.is_dir():
        return []
    return sorted(
        p.name for p in folder.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def add_direct_report(vault_path: str, name: str) -> Path:
    """Create an empty subfolder for a new direct report. Returns the path."""
    name = name.strip()
    if not name:
        raise ValueError("Direct report name cannot be empty")
    folder = Path(vault_path).expanduser() / DIRECT_REPORTS_FOLDER / name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_note_path(vault_path: str, name: str, target_date: date) -> Path:
    """Return the path the dated note for a report *would* be at."""
    return (
        Path(vault_path).expanduser()
        / DIRECT_REPORTS_FOLDER
        / name
        / f"{target_date.strftime('%Y-%m-%d')}.md"
    )


def get_note_for_date(vault_path: str, name: str, target_date: date) -> Path | None:
    """Return the dated note path if it exists, else None."""
    path = get_note_path(vault_path, name, target_date)
    return path if path.is_file() else None


def list_past_notes(vault_path: str, name: str, limit: int = 7) -> list[Path]:
    """Return the most recent dated notes for a report (excluding today)."""
    folder = Path(vault_path).expanduser() / DIRECT_REPORTS_FOLDER / name
    if not folder.is_dir():
        return []
    today_name = f"{date.today().strftime('%Y-%m-%d')}.md"
    dated = sorted(
        (p for p in folder.glob("*.md") if p.name != today_name),
        key=lambda p: p.stem,
        reverse=True,
    )
    return dated[:limit]


def read_note_sections(path: Path) -> dict[str, list[str]]:
    """Parse a markdown file into {section_heading: [content_lines]}.

    Splits on `##` headings. The heading text is stored without the leading
    `## ` prefix. Empty content lines are dropped.
    """
    sections: dict[str, list[str]] = {}
    current: str | None = None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return sections

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            current = stripped[3:].strip()
            sections.setdefault(current, [])
        elif current is not None and stripped:
            sections[current].append(stripped)
    return sections
