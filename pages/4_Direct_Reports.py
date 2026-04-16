"""Direct Reports – morning planning for your team.

One per-person-per-day note under `To Do/07 Direct Reports/{Name}/{YYYY-MM-DD}.md`.
Each morning: pick a report, add tasks to delegate and 1:1 talking points,
and review what you planned for them yesterday.
"""

import streamlit as st
from datetime import date, timedelta

from config import DIRECT_REPORTS_FOLDER
from core.models import TaskStatus
from core.rescan import rescan_vault
from core.task_writer import append_task_to_section
from templates.engine import create_direct_report_note
from workflows.direct_reports import (
    SECTION_NOTES,
    SECTION_TALKING_POINTS,
    SECTION_TASKS,
    add_direct_report,
    get_note_for_date,
    get_note_path,
    list_direct_reports,
    list_past_notes,
    read_note_sections,
)

st.set_page_config(page_title="Direct Reports", page_icon="👥", layout="wide")
st.title("👥 Direct Reports")
st.caption(f"Today is **{date.today().strftime('%A, %B %d, %Y')}**")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

vault_path = st.session_state.vault_path
reports = list_direct_reports(vault_path)

# ── Empty state & add-report control ───────────────────────────────────

st.markdown(
    "Plan tasks to delegate and 1:1 talking points for each direct report. "
    f"Reports are auto-detected from subfolders of `{DIRECT_REPORTS_FOLDER}`."
)

with st.expander("➕ Add a new direct report"):
    new_name = st.text_input(
        "Name",
        key="new_report_name",
        placeholder="e.g. Alice",
    )
    if st.button("Create folder", disabled=not new_name.strip()):
        try:
            add_direct_report(vault_path, new_name.strip())
            rescan_vault()
            st.success(f"Created folder for {new_name.strip()}.")
            st.rerun()
        except (OSError, ValueError) as e:
            st.error(str(e))

if not reports:
    st.info(
        f"No direct reports found yet. Create a subfolder for each person "
        f"under `{DIRECT_REPORTS_FOLDER}/` (or use the control above)."
    )
    st.stop()

# ── Report picker ──────────────────────────────────────────────────────

selected = st.selectbox("Select report", options=reports, key="dr_selected")

today = date.today()
yesterday = today - timedelta(days=1)
todays_path = get_note_path(vault_path, selected, today)
yesterdays_path = get_note_for_date(vault_path, selected, yesterday)

st.divider()

# ── Today / Yesterday layout ───────────────────────────────────────────

left, right = st.columns([0.55, 0.45])

# ── Left: Today's plan ─────────────────────────────────────────────────

with left:
    st.subheader(f"📝 Today's plan for {selected}")
    if todays_path.is_file():
        st.caption(f"Adding to existing note: `{todays_path.name}`")
    else:
        st.caption("Note will be created on submit.")

    with st.form(f"dr_form_{selected}", clear_on_submit=True):
        tasks_text = st.text_area(
            "Tasks / items to delegate",
            placeholder="One task per line...\nReview PR #42\nSchedule Q2 roadmap sync",
            height=140,
        )
        talking_text = st.text_area(
            "1:1 talking points",
            placeholder="One point per line...\nCareer goals check-in\nFeedback on last week's demo",
            height=140,
        )
        notes_text = st.text_area(
            "Notes (optional)",
            placeholder="Freeform notes...",
            height=80,
        )

        submitted = st.form_submit_button(
            f"💾 Add to {selected}'s note for today", type="primary"
        )

        if submitted:
            task_lines = [ln.strip() for ln in tasks_text.splitlines() if ln.strip()]
            talking_lines = [ln.strip() for ln in talking_text.splitlines() if ln.strip()]
            note_lines = [ln.strip() for ln in notes_text.splitlines() if ln.strip()]

            if not (task_lines or talking_lines or note_lines):
                st.warning("Nothing to add — fill in at least one field.")
            else:
                note_path = create_direct_report_note(
                    vault_path, DIRECT_REPORTS_FOLDER, selected, today
                )
                for line in task_lines:
                    append_task_to_section(note_path, SECTION_TASKS, f"- [ ] {line}")
                for line in talking_lines:
                    append_task_to_section(note_path, SECTION_TALKING_POINTS, f"- {line}")
                for line in note_lines:
                    append_task_to_section(note_path, SECTION_NOTES, f"- {line}")

                rescan_vault()
                total = len(task_lines) + len(talking_lines) + len(note_lines)
                st.success(f"Added {total} items to {note_path.name}.")
                st.rerun()

    # Show what's already in today's note
    if todays_path.is_file():
        st.markdown("**Already in today's note:**")
        sections = read_note_sections(todays_path)
        for heading in (SECTION_TASKS, SECTION_TALKING_POINTS, SECTION_NOTES):
            bullets = sections.get(heading, [])
            if bullets:
                st.markdown(f"*{heading}*")
                for b in bullets:
                    st.markdown(f"- {b.lstrip('- ').lstrip('[ ]').lstrip('[x]').strip()}")

# ── Right: Yesterday's plan ────────────────────────────────────────────

with right:
    st.subheader(f"📥 Yesterday ({yesterday.strftime('%A, %b %d')})")

    if not yesterdays_path:
        st.info(f"No plan recorded for {selected} yesterday.")
    else:
        st.caption(f"`{yesterdays_path.name}`")
        sections = read_note_sections(yesterdays_path)

        # Tasks with completion status from parsed vault state
        tasks_from_vault = [
            t for n in st.session_state.notes
            if n.path == yesterdays_path
            for t in n.tasks
        ]
        if tasks_from_vault:
            st.markdown(f"**{SECTION_TASKS}**")
            open_n = sum(1 for t in tasks_from_vault if t.status == TaskStatus.OPEN)
            done_n = sum(1 for t in tasks_from_vault if t.status == TaskStatus.DONE)
            st.caption(f"{done_n} done · {open_n} open")
            for t in tasks_from_vault:
                icon = "✅" if t.status == TaskStatus.DONE else (
                    "❌" if t.status == TaskStatus.CANCELLED else "⬜"
                )
                st.markdown(f"{icon} {t.description}")
        elif sections.get(SECTION_TASKS):
            st.markdown(f"**{SECTION_TASKS}**")
            for b in sections[SECTION_TASKS]:
                st.markdown(f"- {b.lstrip('- ').strip()}")

        if sections.get(SECTION_TALKING_POINTS):
            st.markdown(f"**{SECTION_TALKING_POINTS}**")
            for b in sections[SECTION_TALKING_POINTS]:
                st.markdown(f"- {b.lstrip('- ').strip()}")

        if sections.get(SECTION_NOTES):
            st.markdown(f"**{SECTION_NOTES}**")
            for b in sections[SECTION_NOTES]:
                st.markdown(f"- {b.lstrip('- ').strip()}")

# ── History: past entries ──────────────────────────────────────────────

st.divider()
past = list_past_notes(vault_path, selected, limit=7)
with st.expander(f"📆 Past entries for {selected} ({len(past)})"):
    if not past:
        st.caption("No past entries yet.")
    else:
        for p in past:
            with st.container():
                st.markdown(f"**{p.stem}**")
                sections = read_note_sections(p)
                for heading in (SECTION_TASKS, SECTION_TALKING_POINTS, SECTION_NOTES):
                    bullets = sections.get(heading, [])
                    if bullets:
                        st.markdown(f"*{heading}*")
                        for b in bullets:
                            st.markdown(f"- {b.lstrip('- ').strip()}")
                st.markdown("")
