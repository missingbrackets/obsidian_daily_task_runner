"""Weekly Planning page.

Projects are the source of truth. This page shows incomplete project tasks
and lets you pull them into the weekly note's category sections
(Work, Life Admin, Health, Personal/Growth).

Tasks already in the weekly note are filtered out of the pull list.
"""

import streamlit as st
from datetime import date, timedelta
from pathlib import Path

from config import WEEKLY_FOLDER
from workflows.weekly_planning import (
    weekly_summary,
    find_weekly_note,
    write_tasks_to_weekly_note,
    get_weekly_note_tasks,
    WEEKLY_CATEGORIES,
)
from templates.engine import create_weekly_note
from core.rescan import rescan_vault

st.set_page_config(page_title="Weekly Planning", page_icon="📅", layout="wide")
st.title("📅 Weekly Planning")

today = date.today()
monday = today - timedelta(days=today.weekday())
sunday = monday + timedelta(days=6)
st.caption(f"Week of **{monday.strftime('%B %d')}** – **{sunday.strftime('%B %d, %Y')}**")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes
summary = weekly_summary(notes)

# ── Metrics ────────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Project Tasks Due", len(summary["project_tasks_this_week"]))
with col2:
    st.metric("Overdue (Projects)", len(summary["project_tasks_overdue"]))
with col3:
    st.metric("In Weekly Note", len(summary["weekly_note_tasks"]))
with col4:
    st.metric("Next Week", len(summary["project_tasks_next_week"]))

st.divider()

# ── Create / find weekly note ──────────────────────────────────────────

weekly_note = find_weekly_note(notes)

if not weekly_note:
    st.subheader("📝 Create Weekly Note")
    if st.button("Create This Week's Note", type="primary"):
        path = create_weekly_note(st.session_state.vault_path, WEEKLY_FOLDER)
        rescan_vault()
        st.success(f"Created: {path.name}")
        st.rerun()
    st.divider()

# ── Build pullable list: filter out tasks already in the weekly note ──

vault = Path(st.session_state.vault_path).expanduser().resolve()

already_pulled: set[tuple[str, int]] = set()
for t in summary["weekly_note_tasks"]:
    if t.project_source and t.project_line:
        already_pulled.add((t.project_source, t.project_line))


def _is_already_pulled(t) -> bool:
    try:
        rel = str(t.file_path.relative_to(vault))
    except ValueError:
        rel = str(t.file_path)
    return (rel, t.line_number) in already_pulled


due_this_week_or_overdue = set(
    id(t) for t in summary["project_tasks_overdue"] + summary["project_tasks_this_week"]
)

all_project_tasks = (
    summary["project_tasks_overdue"]
    + summary["project_tasks_this_week"]
    + summary["project_tasks_next_week"]
    + summary["project_tasks_future"]
)
pullable = [t for t in all_project_tasks if not _is_already_pulled(t)]
pullable.sort(key=lambda t: (t.file_path.stem, t.priority, t.due_date or date.max))

# Group by project, carrying the global index for unique widget keys
by_project: dict[str, list[tuple[int, object]]] = {}
for i, t in enumerate(pullable):
    by_project.setdefault(t.file_path.stem, []).append((i, t))

# ── Pull project tasks into weekly note by category ────────────────────

st.subheader("📋 Pull Project Tasks Into Weekly Note")
st.caption(
    "Assign project tasks to a category section in your weekly note. "
    "Tasks already pulled are hidden. Overdue, this week, next week, and future tasks are all shown."
)

if pullable and weekly_note:
    with st.form("pull_tasks_form"):
        for project, indexed_tasks in by_project.items():
            st.markdown(f"**📂 {project}**")
            for idx, t in indexed_tasks:
                status_icon = "🔴" if t.is_overdue else (
                    "🟡" if t.is_due_today else "⚪"
                )
                due_str = f" (due {t.due_date})" if t.due_date else ""
                default_on = id(t) in due_this_week_or_overdue

                col1, col2, col3 = st.columns([0.1, 0.5, 0.4])
                with col1:
                    st.checkbox(
                        "sel",
                        value=default_on,
                        key=f"sel_{idx}",
                        label_visibility="collapsed",
                    )
                with col2:
                    st.markdown(f"{status_icon} {t.description}{due_str}")
                with col3:
                    st.selectbox(
                        "Category",
                        options=WEEKLY_CATEGORIES,
                        key=f"cat_{idx}",
                        label_visibility="collapsed",
                    )

        submitted = st.form_submit_button(
            "📥 Pull Selected Into Weekly Note", type="primary"
        )

        if submitted:
            task_assignments: dict[str, list] = {cat: [] for cat in WEEKLY_CATEGORIES}
            for idx, t in enumerate(pullable):
                if not st.session_state.get(f"sel_{idx}", False):
                    continue
                cat = st.session_state.get(f"cat_{idx}", WEEKLY_CATEGORIES[0])
                task_assignments[cat].append(t)

            count = write_tasks_to_weekly_note(
                weekly_note.path, task_assignments, st.session_state.vault_path,
            )
            if count:
                rescan_vault()
                st.success(f"Pulled {count} tasks into weekly note!")
                st.rerun()
            else:
                st.warning("No tasks selected.")

elif pullable and not weekly_note:
    for project, indexed_tasks in by_project.items():
        st.markdown(f"**📂 {project}**")
        for _, t in indexed_tasks:
            status_icon = "🔴" if t.is_overdue else "⚪"
            due_str = f" (due {t.due_date})" if t.due_date else ""
            st.markdown(f"- {status_icon} {t.description}{due_str}")
    st.warning("Create a weekly note first (button above) before pulling tasks.")
else:
    st.info("No project tasks to pull — everything is already in the weekly note (or no open tasks).")

# ── Tasks already in the weekly note (by category) ────────────────────

st.divider()
st.subheader(f"📝 Currently in Weekly Note ({len(summary['weekly_note_tasks'])})")

if summary["weekly_note_tasks"]:
    by_section: dict[str, list] = {}
    for t in summary["weekly_note_tasks"]:
        by_section.setdefault(t.section, []).append(t)

    for section, tasks in by_section.items():
        st.markdown(f"**{section}**")
        for t in tasks:
            due_str = f" 📅 {t.due_date}" if t.due_date else ""
            proj_str = f" *[{t.file_path.stem}]*" if t.project_source else ""
            st.markdown(f"- {t.description}{due_str}{proj_str}")
else:
    st.info("No tasks in the weekly note yet. Pull from projects above.")

# ── Unscheduled project tasks ─────────────────────────────────────────

st.divider()
st.subheader(f"❓ Unscheduled Project Tasks ({len(summary['unscheduled'])})")
if summary["unscheduled"]:
    st.caption("Project tasks with no due date. Consider adding due dates.")
    for t in summary["unscheduled"][:30]:
        st.markdown(f"- {t.description} *[{t.file_path.stem}]*")
    if len(summary["unscheduled"]) > 30:
        st.caption(f"... and {len(summary['unscheduled']) - 30} more")
else:
    st.success("All project tasks have due dates!")
