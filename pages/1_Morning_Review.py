"""Morning Review page – your daily task briefing."""

import streamlit as st
from datetime import date

from config import DAILY_FOLDER
from core.task_parser import get_all_tasks
from core.models import TaskStatus
from core.rescan import rescan_vault
from workflows.morning_review import morning_summary
from workflows.weekly_planning import get_weekly_note_tasks
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
        rescan_vault()
        st.success(f"Created: {path.name}")
        st.rerun()
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
        rescan_vault()
        st.success(f"Carried over {count} tasks to today's note.")
        st.rerun()
else:
    st.info("No incomplete tasks from yesterday.")

# ── This week's tasks by category ─────────────────────────────────────

st.divider()
st.subheader("📋 This Week's Tasks (from Weekly Note)")

weekly_tasks = get_weekly_note_tasks(notes)
if weekly_tasks:
    by_section: dict[str, list] = {}
    for t in weekly_tasks:
        by_section.setdefault(t.section, []).append(t)

    for section, tasks in by_section.items():
        with st.expander(f"**{section}** ({len(tasks)} tasks)", expanded=True):
            for t in sorted(tasks, key=lambda x: x.priority):
                status_icon = "🔴" if t.is_overdue else ("🟡" if t.is_due_today else "⚪")
                due = f" 📅 {t.due_date}" if t.due_date else ""
                st.markdown(f"{status_icon} {t.description}{due}")
else:
    st.info("No tasks in this week's weekly note yet. Go to **Weekly Planning** to set up your week.")
