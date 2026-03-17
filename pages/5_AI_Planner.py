"""AI Planner page – rule-based prioritization with future LLM integration."""

import streamlit as st
from datetime import date

from config import DAILY_FOLDER
from core.task_parser import get_all_tasks
from core.models import TaskStatus
from core.task_writer import append_task_to_section
from ai.planner import get_planner
from workflows.carryover import find_todays_note

st.set_page_config(page_title="AI Planner", page_icon="🧠", layout="wide")
st.title("🧠 AI Task Planner")
st.caption("Rule-based prioritization (LLM integration coming soon)")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes
all_tasks = get_all_tasks(notes)
open_tasks = [t for t in all_tasks if t.status == TaskStatus.OPEN]

if not open_tasks:
    st.info("No open tasks found.")
    st.stop()

# ── Planner settings ──────────────────────────────────────────────────

col1, col2 = st.columns(2)
with col1:
    top_n = st.slider("How many tasks to recommend?", 3, 15, 5)
with col2:
    show_schedule = st.toggle("Show suggested schedule", value=True)

planner = get_planner(use_llm=False)

st.divider()

# ── Top recommendations ───────────────────────────────────────────────

st.subheader(f"🏆 Top {top_n} Recommended Tasks")
ranked = planner.rank_tasks(open_tasks, top_n=top_n)

for i, t in enumerate(ranked, 1):
    status_icon = "🔴" if t.is_overdue else ("🟡" if t.is_due_today else "🟢")
    prio_icon = {1: "🔺", 2: "⏫", 3: "", 4: "🔽", 5: "⏬"}.get(t.priority, "")
    due_str = f" 📅 {t.due_date}" if t.due_date else ""

    st.markdown(
        f"**{i}.** {status_icon} {prio_icon} {t.description}{due_str}\n"
        f"   *{t.file_path.name} | {t.source_folder}*"
    )

# ── Write top tasks to daily note ─────────────────────────────────────

todays_note = find_todays_note(notes, DAILY_FOLDER)
if todays_note:
    if st.button("📋 Write Top Tasks to Today's Note", type="primary"):
        for t in ranked[:3]:
            line = f"- [ ] {t.description}"
            if t.due_date:
                line += f" 📅 {t.due_date.isoformat()}"
            append_task_to_section(todays_note.path, "Top 3 Must-Do Today", line)
        st.success(f"Added top {min(3, len(ranked))} tasks to today's note!")
        st.info("Re-scan vault to refresh.")

# ── Suggested schedule ─────────────────────────────────────────────────

if show_schedule:
    st.divider()
    st.subheader("📅 Suggested Daily Schedule")

    schedule = planner.suggest_schedule(open_tasks)
    for period, tasks in schedule.items():
        if not tasks:
            continue
        st.markdown(f"### {period}")
        for t in tasks:
            due_str = f" (due {t.due_date})" if t.due_date else ""
            st.markdown(f"- {t.description}{due_str}")

# ── Scoring explanation ────────────────────────────────────────────────

with st.expander("ℹ️ How scoring works"):
    st.markdown("""
**Rule-based scoring:**
- **Overdue** → +50 pts (+ 2 pts per day overdue, max +20)
- **Due today** → +30 pts
- **Due this week** → +15 pts
- **Priority** → (6 − priority) × 10 pts (so priority 1 = 50 pts)
- **Case Pricing** → +5 pts (deadline-driven work)

*Future: LLM integration will consider context, workload balance, and energy patterns.*
""")
