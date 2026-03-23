"""Weekly Planning page.

Projects are the source of truth. This page shows incomplete project tasks
due this week and lets you pull them into the weekly note.
"""

import streamlit as st
from datetime import date, timedelta

from config import WEEKLY_FOLDER, PROJECTS_FOLDER
from workflows.weekly_planning import (
    weekly_summary,
    find_weekly_note,
    write_tasks_to_weekly_note,
)
from templates.engine import create_weekly_note, create_project_note
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

# ── Pull project tasks into weekly note ────────────────────────────────

st.subheader("📋 Project Tasks Due This Week")
st.caption("These are incomplete tasks from your Projects folder due this week.")

all_pullable = summary["project_tasks_this_week"] + summary["project_tasks_overdue"]
if all_pullable:
    prio_labels = {1: "🔺 Highest", 2: "⏫ High", 3: "🔼 Medium", 4: "🔽 Low", 5: "⏬ Lowest"}
    for t in summary["this_week_by_priority"]:
        status_icon = "🔴" if t.is_overdue else "⚪"
        prio_icon = prio_labels.get(t.priority, "")
        due_str = f" (due {t.due_date})" if t.due_date else ""
        st.markdown(
            f"- {status_icon} {t.description}{due_str} "
            f"*[{t.file_path.name}]* {prio_icon}"
        )

    if weekly_note:
        if st.button(
            "📥 Pull All Into Weekly Note",
            type="primary",
            help="Writes these project tasks into the weekly note's Master Task List",
        ):
            count = write_tasks_to_weekly_note(
                weekly_note.path, all_pullable, st.session_state.vault_path,
            )
            rescan_vault()
            st.success(f"Pulled {count} tasks into weekly note!")
            st.rerun()
    else:
        st.warning("Create a weekly note first (button above) before pulling tasks.")
else:
    st.info("No project tasks due this week or overdue.")

# ── Tasks already in the weekly note ───────────────────────────────────

st.divider()
st.subheader(f"📝 Currently in Weekly Note ({len(summary['weekly_note_tasks'])})")
if summary["weekly_note_tasks"]:
    for t in summary["weekly_note_tasks"]:
        due_str = f" 📅 {t.due_date}" if t.due_date else ""
        st.markdown(f"- {t.description}{due_str}")
else:
    st.info("No tasks in the weekly note yet. Pull from projects above.")

# ── Next week preview ──────────────────────────────────────────────────

st.divider()
st.subheader(f"📆 Coming Next Week ({len(summary['project_tasks_next_week'])})")
if summary["project_tasks_next_week"]:
    for t in summary["project_tasks_next_week"]:
        st.markdown(f"- {t.description} (due {t.due_date}) *[{t.file_path.name}]*")
else:
    st.info("No project tasks due next week yet.")

# ── Unscheduled project tasks ─────────────────────────────────────────

st.divider()
st.subheader(f"❓ Unscheduled Project Tasks ({len(summary['unscheduled'])})")
if summary["unscheduled"]:
    st.caption("Project tasks with no due date. Consider adding due dates.")
    for t in summary["unscheduled"][:30]:
        st.markdown(f"- {t.description} *[{t.file_path.name}]*")
    if len(summary["unscheduled"]) > 30:
        st.caption(f"... and {len(summary['unscheduled']) - 30} more")
else:
    st.success("All project tasks have due dates!")
