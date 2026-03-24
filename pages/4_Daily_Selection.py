"""Daily Selection – add extra tasks from the weekly note to today.

The Morning Review is the primary daily flow. This page lets you
cherry-pick additional tasks from the weekly note's categorized
sections during the day.
"""

import streamlit as st
from datetime import date

from config import DAILY_FOLDER
from core.task_writer import append_task_to_section
from core.rescan import rescan_vault
from workflows.weekly_planning import get_weekly_note_tasks
from workflows.carryover import find_todays_note

st.set_page_config(page_title="Daily Selection", page_icon="🎯", layout="wide")
st.title("🎯 Add from Weekly Note")
st.caption(f"Pick additional tasks for **{date.today().strftime('%A, %B %d')}**")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes
candidates = get_weekly_note_tasks(notes)

if not candidates:
    st.info(
        "No open tasks in this week's weekly note. "
        "Go to **Weekly Planning** to pull project tasks in first."
    )
    st.stop()

# ── Group by category section ──────────────────────────────────────────

by_section: dict[str, list] = {}
for t in candidates:
    by_section.setdefault(t.section, []).append(t)

selected_tasks = []
for section, tasks in by_section.items():
    st.subheader(f"{section}")
    for t in sorted(tasks, key=lambda x: (x.priority, x.due_date or date.max)):
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
        if st.button("📋 Add to Today's Daily Note", type="primary"):
            for t in selected_tasks:
                line = f"- [ ] {t.description}"
                if t.due_date:
                    line += f" 📅 {t.due_date.isoformat()}"
                if t.project_source and t.project_line:
                    line += f" <!-- project:{t.project_source}:{t.project_line} -->"
                append_task_to_section(todays_note.path, "Daily Task List", line)
            rescan_vault()
            st.success(f"Added {len(selected_tasks)} tasks!")
            st.rerun()
    else:
        st.warning("Create today's daily note first (Morning Review page).")
