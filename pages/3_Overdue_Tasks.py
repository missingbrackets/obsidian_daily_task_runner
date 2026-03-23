"""Overdue Tasks page – project tasks only, with sync and instant feedback."""

import streamlit as st
from datetime import date

from core.models import TaskStatus
from core.task_writer import sync_task_status, sync_due_date
from core.rescan import rescan_vault
from workflows.overdue import overdue_summary

st.set_page_config(page_title="Overdue Tasks", page_icon="🔴", layout="wide")
st.title("🔴 Overdue Tasks")
st.caption("*Showing overdue tasks from Projects only (source of truth)*")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes
summary = overdue_summary(notes)

st.metric("Total Overdue", summary["count"])
st.divider()

if summary["count"] == 0:
    st.success("No overdue project tasks!")
    st.stop()

# ── By age ─────────────────────────────────────────────────────────────

st.subheader("📊 By Age")
for age_label, tasks in summary["by_age"].items():
    if not tasks:
        continue
    with st.expander(f"{age_label} ({len(tasks)} tasks)", expanded=(age_label == "2+ weeks")):
        for t in tasks:
            days = (date.today() - t.due_date).days if t.due_date else 0
            task_key = f"{t.file_path.stem}_{t.line_number}"

            col1, col2, col3 = st.columns([0.5, 0.25, 0.25])
            with col1:
                st.markdown(f"**{t.description}**")
                st.caption(f"{t.file_path.stem} | Section: {t.section}")
            with col2:
                st.markdown(f"📅 {t.due_date} ({days}d overdue)")
                new_date = st.date_input(
                    "Reschedule to",
                    value=date.today(),
                    min_value=date.today(),
                    key=f"date_{task_key}",
                    label_visibility="collapsed",
                )
                if st.button("📅 Reschedule", key=f"redate_{task_key}"):
                    updated = sync_due_date(
                        t, new_date.strftime("%Y-%m-%d"),
                        st.session_state.vault_path,
                    )
                    rescan_vault()
                    st.success(f"Rescheduled to {new_date} (synced: {', '.join(updated)})")
                    st.rerun()
            with col3:
                if st.button("✅ Done", key=f"done_{task_key}"):
                    updated = sync_task_status(
                        t, TaskStatus.DONE, st.session_state.vault_path,
                    )
                    rescan_vault()
                    st.success(f"Done! Synced: {', '.join(updated)}")
                    st.rerun()
                if st.button("❌ Cancel", key=f"cancel_{task_key}"):
                    updated = sync_task_status(
                        t, TaskStatus.CANCELLED, st.session_state.vault_path,
                    )
                    rescan_vault()
                    st.success(f"Cancelled. Synced: {', '.join(updated)}")
                    st.rerun()

# ── By project ─────────────────────────────────────────────────────────

st.divider()
st.subheader("📁 By Project")
for project, tasks in summary["by_project"].items():
    with st.expander(f"{project} ({len(tasks)} tasks)"):
        for t in tasks:
            days = (date.today() - t.due_date).days if t.due_date else 0
            st.markdown(
                f"- **{t.description}** – {days}d overdue (due {t.due_date})"
            )
