"""Daily Selection page – pick your focus tasks for today."""

import streamlit as st
from datetime import date

from config import SCAN_FOLDERS, DAILY_FOLDER
from core.task_writer import append_task_to_section
from workflows.daily_selection import get_candidates, filter_by_folder, filter_overdue_first
from workflows.carryover import find_todays_note

st.set_page_config(page_title="Daily Selection", page_icon="🎯", layout="wide")
st.title("🎯 Daily Task Selection")
st.caption(f"Pick your focus tasks for **{date.today().strftime('%A, %B %d')}**")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes

# ── Filters ────────────────────────────────────────────────────────────

col1, col2 = st.columns(2)
with col1:
    folder_filter = st.selectbox("Filter by folder", ["All"] + SCAN_FOLDERS)
with col2:
    sort_mode = st.selectbox("Sort by", ["Priority + Due Date", "Overdue First"])

candidates = get_candidates(notes)

if folder_filter != "All":
    candidates = filter_by_folder(candidates, folder_filter)

if sort_mode == "Overdue First":
    candidates = filter_overdue_first(candidates)

st.divider()
st.subheader(f"Available Tasks ({len(candidates)})")

# ── Task selection ─────────────────────────────────────────────────────

selected_tasks = []
for t in candidates[:50]:
    status_icon = "🔴" if t.is_overdue else ("🟡" if t.is_due_today else "⚪")
    prio_icon = {1: "🔺", 2: "⏫", 3: "", 4: "🔽", 5: "⏬"}.get(t.priority, "")
    due_str = f" 📅 {t.due_date}" if t.due_date else ""
    label = f"{status_icon} {prio_icon} {t.description}{due_str} [{t.file_path.name}]"

    if st.checkbox(label, key=f"sel_{t.file_path}_{t.line_number}"):
        selected_tasks.append(t)

if len(candidates) > 50:
    st.caption(f"Showing 50 of {len(candidates)} tasks. Use filters to narrow down.")

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
                append_task_to_section(
                    todays_note.path,
                    "Daily Task List",
                    line,
                )
            st.success(f"Added {len(selected_tasks)} tasks to today's note!")
            st.info("Re-scan vault to refresh.")
    else:
        st.warning("Create today's daily note first (Morning Review page).")
