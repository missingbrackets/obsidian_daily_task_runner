"""Overdue Tasks page – with due date editing, done, and cancel actions."""

import streamlit as st
from datetime import date, timedelta

from core.models import TaskStatus
from core.task_writer import toggle_task, update_due_date
from workflows.overdue import overdue_summary

st.set_page_config(page_title="Overdue Tasks", page_icon="🔴", layout="wide")
st.title("🔴 Overdue Tasks")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes
summary = overdue_summary(notes)

st.metric("Total Overdue", summary["count"])
st.divider()

# ── By age ─────────────────────────────────────────────────────────────

st.subheader("📊 By Age")
for age_label, tasks in summary["by_age"].items():
    if not tasks:
        continue
    with st.expander(f"{age_label} ({len(tasks)} tasks)", expanded=(age_label == "2+ weeks")):
        for t in tasks:
            days = (date.today() - t.due_date).days if t.due_date else 0
            task_key = f"{t.file_path}_{t.line_number}"

            col1, col2, col3 = st.columns([0.5, 0.25, 0.25])
            with col1:
                st.markdown(f"**{t.description}**")
                st.caption(f"{t.file_path.name} | Section: {t.section}")
            with col2:
                st.markdown(f"📅 {t.due_date} ({days}d overdue)")
                new_date = st.date_input(
                    "Reschedule to",
                    value=date.today(),
                    min_value=date.today(),
                    key=f"date_{task_key}",
                    label_visibility="collapsed",
                )
                if st.button("📅 Update Due Date", key=f"redate_{task_key}"):
                    update_due_date(t, new_date.strftime("%Y-%m-%d"))
                    st.success(f"Rescheduled to {new_date}")
                    st.info("Re-scan vault to refresh.")
            with col3:
                if st.button("✅ Done", key=f"done_{task_key}"):
                    toggle_task(t, TaskStatus.DONE)
                    st.success(f"Marked done: {t.description[:40]}...")
                    st.info("Re-scan vault to refresh.")
                if st.button("❌ Cancel", key=f"cancel_{task_key}"):
                    toggle_task(t, TaskStatus.CANCELLED)
                    st.success(f"Cancelled: {t.description[:40]}...")
                    st.info("Re-scan vault to refresh.")

# ── By folder ──────────────────────────────────────────────────────────

st.divider()
st.subheader("📂 By Folder")
for folder, tasks in summary["by_folder"].items():
    with st.expander(f"{folder} ({len(tasks)} tasks)"):
        for t in tasks:
            days = (date.today() - t.due_date).days if t.due_date else 0
            st.markdown(
                f"- **{t.description}** – {days}d overdue (due {t.due_date}) "
                f"*[{t.file_path.name}]*"
            )
