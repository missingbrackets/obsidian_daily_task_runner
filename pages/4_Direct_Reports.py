"""Direct Reports – morning planning for your team.

Per-person-per-day notes at `To Do/07 Direct Reports/{Name}/{YYYY-MM-DD}.md`.

Morning flow:
  1. Pick a report.
  2. Assign real vault tasks (projects / weekly) to them — carries the project
     source comment so sync_task_status propagates completions everywhere.
  3. Add free-text 1:1 talking points and notes.
  4. Review yesterday's plan; mark any outstanding tasks done.
"""

import streamlit as st
from datetime import date, timedelta
from pathlib import Path

from config import DIRECT_REPORTS_FOLDER, WEEKLY_FOLDER
from core.models import Task, TaskStatus
from core.rescan import rescan_vault
from core.task_parser import get_all_tasks
from core.task_writer import (
    append_task_to_section,
    build_project_source_comment,
    sync_task_status,
)
from templates.engine import create_direct_report_note
from workflows.direct_reports import (
    SECTION_NOTES,
    SECTION_TALKING_POINTS,
    SECTION_TASKS,
    add_direct_report,
    get_note_for_date,
    get_note_path,
    list_direct_reports,
    list_past_notes,
    read_note_sections,
)

st.set_page_config(page_title="Direct Reports", page_icon="👥", layout="wide")
st.title("👥 Direct Reports")
st.caption(f"Today is **{date.today().strftime('%A, %B %d, %Y')}**")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

vault_path = st.session_state.vault_path
notes = st.session_state.notes
today = date.today()
yesterday = today - timedelta(days=1)


# ── Shared helpers ─────────────────────────────────────────────────────

def _task_key(t: Task) -> str:
    return f"{t.file_path.stem}_{t.line_number}"


def _prio_icon(t: Task) -> str:
    return {1: "🔺", 2: "⏫", 3: "", 4: "🔽", 5: "⏬"}.get(t.priority, "")


def _build_task_line(t: Task) -> str:
    """Markdown checkbox line with metadata and project-source tracking comment."""
    line = f"- [ ] {t.description}"
    if t.due_date:
        line += f" 📅 {t.due_date.isoformat()}"
    if t.priority != 3:
        line += f" {_prio_icon(t)}"
    # Carry source comment so sync_task_status can propagate completions.
    if t.project_source and t.project_line:
        line += f" <!-- project:{t.project_source}:{t.project_line} -->"
    else:
        comment = build_project_source_comment(t, vault_path)
        if comment.strip():
            line += f" {comment}"
    return line


def _get_assignable_tasks() -> list[Task]:
    """Open tasks from the weekly note, sorted by project then due date."""
    return sorted(
        [
            t for t in get_all_tasks(notes)
            if t.status == TaskStatus.OPEN
            and t.source_folder == WEEKLY_FOLDER
        ],
        key=lambda t: (_project_name(t), t.due_date or date.max, t.priority),
    )


def _project_name(t: Task) -> str:
    """Derive project name from the task's project_source, or fall back to file stem."""
    if t.project_source:
        return Path(t.project_source).stem
    return t.file_path.stem


def _tasks_in_note(path) -> list[Task]:
    """Return parsed Task objects whose source file is exactly `path`."""
    return [t for n in notes if n.path == path for t in n.tasks]


# ── Add-report control ─────────────────────────────────────────────────

st.markdown(
    "Plan for each direct report: assign vault tasks to delegate, add 1:1 talking "
    f"points, and review yesterday's plan. Reports are subfolders of "
    f"`{DIRECT_REPORTS_FOLDER}`."
)

with st.expander("➕ Add a new direct report"):
    new_name = st.text_input("Name", key="new_report_name", placeholder="e.g. Alice")
    if st.button("Create folder", disabled=not new_name.strip()):
        try:
            add_direct_report(vault_path, new_name.strip())
            rescan_vault()
            st.success(f"Created folder for **{new_name.strip()}**.")
            st.rerun()
        except (OSError, ValueError) as e:
            st.error(str(e))

reports = list_direct_reports(vault_path)
if not reports:
    st.info(
        f"No direct reports found. Create a subfolder for each person under "
        f"`{DIRECT_REPORTS_FOLDER}/` (or use the control above)."
    )
    st.stop()

# ── Report picker ──────────────────────────────────────────────────────

selected = st.selectbox("Select report", options=reports, key="dr_selected")
todays_path = get_note_path(vault_path, selected, today)
yesterdays_path = get_note_for_date(vault_path, selected, yesterday)

st.divider()

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: ASSIGN VAULT TASKS
# ═══════════════════════════════════════════════════════════════════════

st.subheader(f"🎯 Assign weekly tasks to {selected}")
st.caption(
    "Select tasks from your weekly note to delegate. Grouped by project and due date. "
    "Each carries its source link, so marking it done anywhere syncs everywhere."
)

assignable = _get_assignable_tasks()

if not assignable:
    st.info("No open tasks in the weekly note. Pull project tasks into your weekly note first.")
else:
    # Group by project, then by due date within each project
    by_project: dict[str, dict[str, list[tuple[int, Task]]]] = {}
    for i, t in enumerate(assignable):
        proj = _project_name(t)
        due_label = str(t.due_date) if t.due_date else "No due date"
        by_project.setdefault(proj, {}).setdefault(due_label, []).append((i, t))

    with st.form(f"assign_form_{selected}"):
        for project, dates in by_project.items():
            st.markdown(f"**📂 {project}**")
            for due_label, indexed_tasks in dates.items():
                if due_label != "No due date":
                    sample = indexed_tasks[0][1]
                    badge = "🔴 Overdue" if sample.is_overdue else (
                        "🟡 Today" if sample.is_due_today else f"📅 {due_label}"
                    )
                    st.caption(badge)
                else:
                    st.caption("📅 No due date")
                for idx, t in indexed_tasks:
                    label = f"{_prio_icon(t)} {t.description}".strip()
                    st.checkbox(label, key=f"assign_{idx}")

        submitted = st.form_submit_button(
            f"📋 Assign selected to {selected}'s plan for today", type="primary"
        )
        if submitted:
            to_assign = [
                t for i, t in enumerate(assignable)
                if st.session_state.get(f"assign_{i}", False)
            ]
            if not to_assign:
                st.warning("No tasks selected.")
            else:
                note_path = create_direct_report_note(
                    vault_path, DIRECT_REPORTS_FOLDER, selected, today
                )
                for t in to_assign:
                    append_task_to_section(note_path, SECTION_TASKS, _build_task_line(t))
                rescan_vault()
                st.success(f"Assigned {len(to_assign)} task(s) to {selected}'s note for today.")
                st.rerun()

st.divider()

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: TODAY / YESTERDAY COLUMNS
# ═══════════════════════════════════════════════════════════════════════

left, right = st.columns([0.55, 0.45])

# ── Left: Today's plan ─────────────────────────────────────────────────

with left:
    st.subheader(f"📝 Today — {selected}")

    todays_tasks = _tasks_in_note(todays_path)
    if todays_tasks:
        open_n = sum(1 for t in todays_tasks if t.status == TaskStatus.OPEN)
        done_n = sum(1 for t in todays_tasks if t.status == TaskStatus.DONE)
        st.markdown(f"**{SECTION_TASKS}** — {done_n} done · {open_n} open")
        for t in todays_tasks:
            key = _task_key(t)
            icon = "✅" if t.status == TaskStatus.DONE else (
                "❌" if t.status == TaskStatus.CANCELLED else "⬜"
            )
            col1, col2 = st.columns([0.75, 0.25])
            with col1:
                due_str = f" · {t.due_date}" if t.due_date else ""
                st.markdown(f"{icon} {_prio_icon(t)} {t.description}{due_str}")
            with col2:
                if t.status == TaskStatus.OPEN:
                    if st.button("✅ Done", key=f"done_today_{key}"):
                        updated = sync_task_status(t, TaskStatus.DONE, vault_path)
                        rescan_vault()
                        st.toast(f"Done! Synced: {', '.join(updated)}")
                        st.rerun()
                elif t.status == TaskStatus.DONE:
                    if st.button("↩️ Reopen", key=f"reopen_today_{key}"):
                        updated = sync_task_status(t, TaskStatus.OPEN, vault_path)
                        rescan_vault()
                        st.toast(f"Reopened in: {', '.join(updated)}")
                        st.rerun()

    # Talking points + notes already in today's file
    if todays_path.is_file():
        sections = read_note_sections(todays_path)
        for heading in (SECTION_TALKING_POINTS, SECTION_NOTES):
            bullets = sections.get(heading, [])
            if bullets:
                st.markdown(f"**{heading}**")
                for b in bullets:
                    st.markdown(f"- {b.lstrip('- ').strip()}")

    st.markdown("---")
    st.caption(
        "Add more items below (talking points, notes, or ad-hoc tasks not in your vault):"
    )

    with st.form(f"dr_freetext_{selected}", clear_on_submit=True):
        tasks_text = st.text_area(
            "Tasks / items to delegate",
            placeholder="One per line…",
            height=90,
        )
        talking_text = st.text_area(
            "1:1 talking points",
            placeholder="One per line…",
            height=90,
        )
        notes_text = st.text_area("Notes", placeholder="Freeform…", height=60)

        if st.form_submit_button("💾 Add items", type="secondary"):
            task_lines = [ln.strip() for ln in tasks_text.splitlines() if ln.strip()]
            talking_lines = [ln.strip() for ln in talking_text.splitlines() if ln.strip()]
            note_lines = [ln.strip() for ln in notes_text.splitlines() if ln.strip()]

            if not (task_lines or talking_lines or note_lines):
                st.warning("Nothing to add — fill in at least one field.")
            else:
                note_path = create_direct_report_note(
                    vault_path, DIRECT_REPORTS_FOLDER, selected, today
                )
                for line in task_lines:
                    append_task_to_section(note_path, SECTION_TASKS, f"- [ ] {line}")
                for line in talking_lines:
                    append_task_to_section(note_path, SECTION_TALKING_POINTS, f"- {line}")
                for line in note_lines:
                    append_task_to_section(note_path, SECTION_NOTES, f"- {line}")
                rescan_vault()
                total = len(task_lines) + len(talking_lines) + len(note_lines)
                st.success(f"Added {total} item(s) to {selected}'s note.")
                st.rerun()

# ── Right: Yesterday's plan ────────────────────────────────────────────

with right:
    st.subheader(f"📥 Yesterday — {selected}")
    st.caption(yesterday.strftime("%A, %b %d"))

    if not yesterdays_path:
        st.info(f"No plan recorded for {selected} yesterday.")
    else:
        sections = read_note_sections(yesterdays_path)
        yesterdays_tasks = _tasks_in_note(yesterdays_path)

        if yesterdays_tasks:
            open_n = sum(1 for t in yesterdays_tasks if t.status == TaskStatus.OPEN)
            done_n = sum(1 for t in yesterdays_tasks if t.status == TaskStatus.DONE)
            st.markdown(f"**{SECTION_TASKS}** — {done_n} done · {open_n} open")
            for t in yesterdays_tasks:
                key = _task_key(t)
                icon = "✅" if t.status == TaskStatus.DONE else (
                    "❌" if t.status == TaskStatus.CANCELLED else "⬜"
                )
                col1, col2 = st.columns([0.70, 0.30])
                with col1:
                    st.markdown(f"{icon} {t.description}")
                with col2:
                    if t.status == TaskStatus.OPEN:
                        if st.button("✅ Done", key=f"done_yest_{key}"):
                            updated = sync_task_status(t, TaskStatus.DONE, vault_path)
                            rescan_vault()
                            st.toast(f"Done! Synced: {', '.join(updated)}")
                            st.rerun()
        elif sections.get(SECTION_TASKS):
            st.markdown(f"**{SECTION_TASKS}**")
            for b in sections[SECTION_TASKS]:
                st.markdown(f"- {b.lstrip('- ').strip()}")

        if sections.get(SECTION_TALKING_POINTS):
            st.markdown(f"**{SECTION_TALKING_POINTS}**")
            for b in sections[SECTION_TALKING_POINTS]:
                st.markdown(f"- {b.lstrip('- ').strip()}")

        if sections.get(SECTION_NOTES):
            st.markdown(f"**{SECTION_NOTES}**")
            for b in sections[SECTION_NOTES]:
                st.markdown(f"- {b.lstrip('- ').strip()}")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: HISTORY
# ═══════════════════════════════════════════════════════════════════════

st.divider()
past = list_past_notes(vault_path, selected, limit=7)
with st.expander(f"📆 Past entries for {selected} ({len(past)})"):
    if not past:
        st.caption("No past entries yet.")
    else:
        for p in past:
            st.markdown(f"**{p.stem}**")
            sections = read_note_sections(p)
            for heading in (SECTION_TASKS, SECTION_TALKING_POINTS, SECTION_NOTES):
                bullets = sections.get(heading, [])
                if bullets:
                    st.markdown(f"*{heading}*")
                    for b in bullets:
                        st.markdown(f"- {b.lstrip('- ').strip()}")
            st.markdown("")
