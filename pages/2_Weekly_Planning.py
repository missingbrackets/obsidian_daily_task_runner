"""Weekly Planning page.

Projects are the source of truth. This page shows incomplete project tasks
due this week and lets you pull them into the weekly note's category sections
(Work, Life Admin, Health, Personal/Growth).

The project task query blocks in the weekly template auto-render in Obsidian
and are left untouched by this app.
"""

import streamlit as st
from datetime import date, timedelta

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

# ── Pull project tasks into weekly note by category ────────────────────

st.subheader("📋 Pull Project Tasks Into Weekly Note")
st.caption(
    "Assign each project task to a category section in your weekly note. "
    "The project query blocks at the bottom of the weekly note will auto-render in Obsidian."
)

all_pullable = summary["project_tasks_this_week"] + summary["project_tasks_overdue"]

if all_pullable and weekly_note:
    with st.form("pull_tasks_form"):
        assignments: dict[str, list] = {cat: [] for cat in WEEKLY_CATEGORIES}

        for i, t in enumerate(summary["this_week_by_priority"]):
            status_icon = "🔴" if t.is_overdue else "⚪"
            due_str = f" (due {t.due_date})" if t.due_date else ""
            task_key = f"{t.file_path.stem}_{t.line_number}_{i}"

            col1, col2 = st.columns([0.6, 0.4])
            with col1:
                st.markdown(f"{status_icon} **{t.description}**{due_str} *[{t.file_path.stem}]*")
            with col2:
                category = st.selectbox(
                    "Category",
                    options=WEEKLY_CATEGORIES,
                    key=f"cat_{task_key}",
                    label_visibility="collapsed",
                )

            # Store the assignment keyed by task identity
            if f"_assignment_{task_key}" not in st.session_state:
                st.session_state[f"_assignment_{task_key}"] = category

        submitted = st.form_submit_button(
            "📥 Pull Selected Into Weekly Note", type="primary"
        )

        if submitted:
            # Build assignments from form state
            task_assignments: dict[str, list] = {cat: [] for cat in WEEKLY_CATEGORIES}
            for i, t in enumerate(summary["this_week_by_priority"]):
                task_key = f"{t.file_path.stem}_{t.line_number}_{i}"
                cat = st.session_state.get(f"cat_{task_key}", WEEKLY_CATEGORIES[0])
                task_assignments[cat].append(t)

            count = write_tasks_to_weekly_note(
                weekly_note.path, task_assignments, st.session_state.vault_path,
            )
            rescan_vault()
            st.success(f"Pulled {count} tasks into weekly note!")
            st.rerun()

elif all_pullable and not weekly_note:
    for t in summary["this_week_by_priority"]:
        status_icon = "🔴" if t.is_overdue else "⚪"
        due_str = f" (due {t.due_date})" if t.due_date else ""
        st.markdown(f"- {status_icon} {t.description}{due_str} *[{t.file_path.stem}]*")
    st.warning("Create a weekly note first (button above) before pulling tasks.")
else:
    st.info("No project tasks due this week or overdue.")

# ── Tasks already in the weekly note (by category) ────────────────────

st.divider()
st.subheader(f"📝 Currently in Weekly Note ({len(summary['weekly_note_tasks'])})")

if summary["weekly_note_tasks"]:
    # Group by section heading
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

# ── Next week preview ──────────────────────────────────────────────────

st.divider()
st.subheader(f"📆 Coming Next Week ({len(summary['project_tasks_next_week'])})")
if summary["project_tasks_next_week"]:
    for t in summary["project_tasks_next_week"]:
        st.markdown(f"- {t.description} (due {t.due_date}) *[{t.file_path.stem}]*")
else:
    st.info("No project tasks due next week yet.")

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
