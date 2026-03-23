"""Daily Selection page – pick today's tasks from the weekly note."""

import streamlit as st
from datetime import date

from config import DAILY_FOLDER
from core.task_writer import append_task_to_section
from core.rescan import rescan_vault
from workflows.daily_selection import get_candidates, filter_overdue_first
from workflows.carryover import find_todays_note

st.set_page_config(page_title="Daily Selection", page_icon="🎯", layout="wide")
st.title("🎯 Daily Task Selection")
st.caption(f"Pick your focus tasks for **{date.today().strftime('%A, %B %d')}**")
st.caption("*Sourced from this week's weekly note*")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes

# ── Sort control ───────────────────────────────────────────────────────

sort_mode = st.selectbox("Sort by", ["Priority + Due Date", "Overdue First"])

candidates = get_candidates(notes)

if sort_mode == "Overdue First":
    candidates = filter_overdue_first(candidates)

if not candidates:
    st.info(
        "No tasks found in this week's weekly note. "
        "Go to **Weekly Planning** to pull project tasks into the weekly note first."
    )
    st.stop()

# ── Group by category section from weekly note ─────────────────────────

by_section: dict[str, list] = {}
for t in candidates:
    by_section.setdefault(t.section, []).append(t)

st.divider()
st.subheader(f"Weekly Tasks ({len(candidates)})")

selected_tasks = []
for section, tasks in by_section.items():
    st.markdown(f"**{section}**")
    for t in tasks:
        status_icon = "🔴" if t.is_overdue else ("🟡" if t.is_due_today else "⚪")
        prio_icon = {1: "🔺", 2: "⏫", 3: "", 4: "🔽", 5: "⏬"}.get(t.priority, "")
        due_str = f" 📅 {t.due_date}" if t.due_date else ""
        label = f"{status_icon} {prio_icon} {t.description}{due_str}"

        if st.checkbox(label, key=f"sel_{t.file_path}_{t.line_number}"):
            selected_tasks.append(t)

# ── Write to daily note ───────────────────────────────────────────────

st.divider()
if selected_tasks:
    st.subheader(f"📝 Selected: {len(selected_tasks)} tasks")
    for t in selected_tasks:
        st.markdown(f"- {t.description}")

    todays_note = find_todays_note(notes, DAILY_FOLDER)
    if todays_note:
        if st.button("📋 Write Selected to Today's Daily Note", type="primary"):
            for t in selected_tasks:
                line = f"- [ ] {t.description}"
                if t.due_date:
                    line += f" 📅 {t.due_date.isoformat()}"
                # Propagate project source label for sync
                if t.project_source and t.project_line:
                    line += f" <!-- project:{t.project_source}:{t.project_line} -->"
                append_task_to_section(
                    todays_note.path,
                    "Daily Task List",
                    line,
                )
            rescan_vault()
            st.success(f"Added {len(selected_tasks)} tasks to today's note!")
            st.rerun()
    else:
        st.warning("Create today's daily note first (Morning Review page).")
