"""Morning Review page – your daily task briefing."""

import streamlit as st
from datetime import date

from config import DAILY_FOLDER
from core.task_parser import get_all_tasks
from core.models import TaskStatus
from workflows.morning_review import morning_summary
from workflows.carryover import (
    find_yesterdays_note,
    find_todays_note,
    get_carryover_tasks,
    perform_carryover,
)
from templates.engine import create_daily_note

st.set_page_config(page_title="Morning Review", page_icon="🌅", layout="wide")
st.title("🌅 Morning Review")
st.caption(f"Today is **{date.today().strftime('%A, %B %d, %Y')}**")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes
summary = morning_summary(notes, DAILY_FOLDER)

# ── Metrics row ────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Due Today", len(summary["today"]))
with col2:
    st.metric("Overdue", len(summary["overdue"]))
with col3:
    st.metric("Carryover", len(summary["yesterday_incomplete"]))
with col4:
    st.metric("Total Open", summary["total_open"])

st.divider()

# ── Create today's daily note ─────────────────────────────────────────

todays_note = find_todays_note(notes, DAILY_FOLDER)
if not todays_note:
    st.subheader("📝 Create Today's Daily Note")
    if st.button("Create Daily Note", type="primary"):
        path = create_daily_note(st.session_state.vault_path, DAILY_FOLDER)
        st.success(f"Created: {path.name}")
        st.info("Re-scan vault to see the new note.")
    st.divider()

# ── Today's tasks ──────────────────────────────────────────────────────

st.subheader(f"📌 Tasks Due Today ({len(summary['today'])})")
if summary["today"]:
    for t in summary["today"]:
        prio = "🔺" if t.priority <= 2 else ""
        st.checkbox(
            f"{prio} {t.description}",
            value=False,
            key=f"today_{t.file_path}_{t.line_number}",
            help=f"From: {t.file_path.name} | Section: {t.section}",
        )
else:
    st.info("No tasks specifically due today.")

# ── Overdue tasks ──────────────────────────────────────────────────────

st.subheader(f"🔴 Overdue Tasks ({len(summary['overdue'])})")
if summary["overdue"]:
    for t in summary["overdue"]:
        days = (date.today() - t.due_date).days if t.due_date else 0
        st.markdown(
            f"- **{t.description}** – {days}d overdue (due {t.due_date}) "
            f"*[{t.file_path.name}]*"
        )
else:
    st.success("No overdue tasks!")

# ── Carryover ──────────────────────────────────────────────────────────

st.subheader(f"📥 Carryover from Yesterday ({len(summary['yesterday_incomplete'])})")
if summary["yesterday_incomplete"]:
    for t in summary["yesterday_incomplete"]:
        st.markdown(f"- {t.description}")

    if todays_note and st.button("📋 Copy Carryover to Today's Note"):
        count = perform_carryover(
            summary["yesterday_incomplete"],
            todays_note.path,
        )
        st.success(f"Carried over {count} tasks to today's note.")
        st.info("Re-scan vault to refresh.")
else:
    st.info("No incomplete tasks from yesterday.")

# ── By folder ──────────────────────────────────────────────────────────

st.divider()
st.subheader("📂 Open Tasks by Folder")
for folder, tasks in summary["by_folder"].items():
    with st.expander(f"{folder} ({len(tasks)} tasks)"):
        for t in sorted(tasks, key=lambda x: x.priority):
            due = f" 📅 {t.due_date}" if t.due_date else ""
            st.markdown(f"- {t.description}{due}")
