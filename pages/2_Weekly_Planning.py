"""Weekly Planning page."""

import streamlit as st
from datetime import date, timedelta

from config import WEEKLY_FOLDER
from workflows.weekly_planning import weekly_summary
from templates.engine import create_weekly_note

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

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("This Week", len(summary["this_week"]))
with col2:
    st.metric("Next Week", len(summary["next_week"]))
with col3:
    st.metric("Unscheduled", len(summary["unscheduled"]))

st.divider()

# ── Create weekly note ─────────────────────────────────────────────────

st.subheader("📝 Create Weekly Note")
if st.button("Create This Week's Note", type="primary"):
    path = create_weekly_note(st.session_state.vault_path, WEEKLY_FOLDER)
    st.success(f"Created: {path.name}")
    st.info("Re-scan vault to see the new note.")

st.divider()

# ── This week's tasks by priority ──────────────────────────────────────

st.subheader(f"📋 This Week – By Priority ({len(summary['this_week'])})")
if summary["this_week_by_priority"]:
    prio_labels = {1: "🔺 Highest", 2: "⏫ High", 3: "🔼 Medium", 4: "🔽 Low", 5: "⏬ Lowest"}
    current_prio = None
    for t in summary["this_week_by_priority"]:
        if t.priority != current_prio:
            current_prio = t.priority
            st.markdown(f"**{prio_labels.get(t.priority, 'Normal')}**")
        due_str = f" (due {t.due_date})" if t.due_date else ""
        st.markdown(f"- {t.description}{due_str} *[{t.file_path.name}]*")
else:
    st.info("No tasks due this week with explicit due dates.")

# ── This week by folder ───────────────────────────────────────────────

st.subheader("📂 This Week – By Folder")
for folder, tasks in summary["this_week_by_folder"].items():
    with st.expander(f"{folder} ({len(tasks)} tasks)"):
        for t in tasks:
            due_str = f" (due {t.due_date})" if t.due_date else ""
            st.markdown(f"- {t.description}{due_str}")

# ── Next week ──────────────────────────────────────────────────────────

st.divider()
st.subheader(f"📆 Next Week ({len(summary['next_week'])})")
if summary["next_week"]:
    for t in summary["next_week"]:
        st.markdown(f"- {t.description} (due {t.due_date}) *[{t.file_path.name}]*")
else:
    st.info("No tasks due next week yet.")

# ── Unscheduled ────────────────────────────────────────────────────────

st.divider()
st.subheader(f"❓ Unscheduled Tasks ({len(summary['unscheduled'])})")
if summary["unscheduled"]:
    st.caption("These tasks have no due date or scheduled date. Consider scheduling them.")
    for t in summary["unscheduled"][:30]:
        st.markdown(f"- {t.description} *[{t.file_path.name}]*")
    if len(summary["unscheduled"]) > 30:
        st.caption(f"... and {len(summary['unscheduled']) - 30} more")
else:
    st.success("All tasks are scheduled!")
