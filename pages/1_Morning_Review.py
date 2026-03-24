"""Morning Review – unified daily task selection.

One page, one flow:
1. Create today's daily note if needed
2. Select tasks from: yesterday incomplete -> overdue -> due today -> due soon
3. Write selected to today's note; yesterday tasks get moved to "Move to tomorrow"
"""

import streamlit as st
from datetime import date

from config import DAILY_FOLDER
from core.rescan import rescan_vault
from core.task_writer import (
    append_task_to_section,
    move_task_to_tomorrow_section,
)
from workflows.daily_selection import daily_selection_groups
from workflows.carryover import find_todays_note
from workflows.weekly_planning import get_weekly_note_tasks
from templates.engine import create_daily_note

st.set_page_config(page_title="Morning Review", page_icon="🌅", layout="wide")
st.title("🌅 Morning Review")
st.caption(f"Today is **{date.today().strftime('%A, %B %d, %Y')}**")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes

# ── Create today's daily note ─────────────────────────────────────────

todays_note = find_todays_note(notes, DAILY_FOLDER)
if not todays_note:
    if st.button("📝 Create Today's Daily Note", type="primary"):
        path = create_daily_note(st.session_state.vault_path, DAILY_FOLDER)
        rescan_vault()
        st.success(f"Created: {path.name}")
        st.rerun()
    st.stop()

# ── Gather all candidate groups ───────────────────────────────────────

groups = daily_selection_groups(notes)

total = (
    len(groups["yesterday_incomplete"])
    + len(groups["overdue"])
    + len(groups["due_today"])
    + len(groups["due_soon"])
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Yesterday", len(groups["yesterday_incomplete"]))
with col2:
    st.metric("Overdue", len(groups["overdue"]))
with col3:
    st.metric("Due Today", len(groups["due_today"]))
with col4:
    st.metric("Due Soon", len(groups["due_soon"]))

if total == 0:
    st.success("No tasks to review! Go to **Weekly Planning** to set up your week.")
    st.stop()

st.divider()
st.markdown("Select tasks to add to today's daily note, then click the button at the bottom.")

# ── Track selections ──────────────────────────────────────────────────

selected_yesterday: list = []
selected_project: list = []


def _task_key(t) -> str:
    return f"{t.file_path.stem}_{t.line_number}"


def _prio_icon(t) -> str:
    return {1: "🔺", 2: "⏫", 3: "", 4: "🔽", 5: "⏬"}.get(t.priority, "")


# ── 1. Yesterday incomplete ───────────────────────────────────────────

if groups["yesterday_incomplete"]:
    st.subheader(f"📥 Not Completed Yesterday ({len(groups['yesterday_incomplete'])})")
    st.caption("Selecting these will tick them off in yesterday's note and move them to 'Move to tomorrow'.")
    for t in groups["yesterday_incomplete"]:
        due_str = f" 📅 {t.due_date}" if t.due_date else ""
        label = f"🟠 {_prio_icon(t)} {t.description}{due_str}"
        if st.checkbox(label, key=f"yest_{_task_key(t)}"):
            selected_yesterday.append(t)

# ── 2. Overdue from projects ─────────────────────────────────────────

if groups["overdue"]:
    st.divider()
    st.subheader(f"🔴 Overdue Project Tasks ({len(groups['overdue'])})")
    for project, tasks in groups["overdue_by_project"].items():
        st.markdown(f"**{project}**")
        for t in tasks:
            days = (date.today() - t.due_date).days if t.due_date else 0
            label = f"🔴 {_prio_icon(t)} {t.description} ({days}d overdue)"
            if st.checkbox(label, key=f"over_{_task_key(t)}"):
                selected_project.append(t)

# ── 3. Due today ──────────────────────────────────────────────────────

if groups["due_today"]:
    st.divider()
    st.subheader(f"🟡 Due Today ({len(groups['due_today'])})")
    for project, tasks in groups["due_today_by_project"].items():
        st.markdown(f"**{project}**")
        for t in tasks:
            label = f"🟡 {_prio_icon(t)} {t.description}"
            if st.checkbox(label, key=f"today_{_task_key(t)}"):
                selected_project.append(t)

# ── 4. Due soon ───────────────────────────────────────────────────────

if groups["due_soon"]:
    st.divider()
    st.subheader(f"📅 Due Soon ({len(groups['due_soon'])})")
    for project, tasks in groups["due_soon_by_project"].items():
        st.markdown(f"**{project}**")
        for t in tasks:
            days_until = (t.due_date - date.today()).days if t.due_date else 0
            label = f"⚪ {_prio_icon(t)} {t.description} (in {days_until}d, {t.due_date})"
            if st.checkbox(label, key=f"soon_{_task_key(t)}"):
                selected_project.append(t)

# ── Write selected to daily note ──────────────────────────────────────

all_selected = selected_yesterday + selected_project

st.divider()
if all_selected:
    st.subheader(f"📝 Selected: {len(all_selected)} tasks")
    for t in all_selected:
        st.markdown(f"- {t.description}")

    if st.button("📋 Add Selected to Today's Daily Note", type="primary"):
        for t in selected_yesterday:
            # Tick in yesterday's note + move to "Move to tomorrow"
            move_task_to_tomorrow_section(t)
            # Add fresh copy to today's daily task list
            line = f"- [ ] {t.description}"
            if t.due_date:
                line += f" 📅 {t.due_date.isoformat()}"
            if t.project_source and t.project_line:
                line += f" <!-- project:{t.project_source}:{t.project_line} -->"
            append_task_to_section(todays_note.path, "Daily Task List", line)

        for t in selected_project:
            line = f"- [ ] {t.description}"
            if t.due_date:
                line += f" 📅 {t.due_date.isoformat()}"
            # Build project source from the project task itself
            from core.task_writer import build_project_source_comment
            line += f" {build_project_source_comment(t, st.session_state.vault_path)}"
            append_task_to_section(todays_note.path, "Daily Task List", line)

        rescan_vault()
        st.success(f"Added {len(all_selected)} tasks to today's note!")
        st.rerun()
else:
    st.info("Select tasks above to add to today's daily note.")

# ── This week's tasks (from weekly note) ──────────────────────────────

st.divider()
st.subheader("📋 This Week (from Weekly Note)")

weekly_tasks = get_weekly_note_tasks(notes)
if weekly_tasks:
    by_section: dict[str, list] = {}
    for t in weekly_tasks:
        by_section.setdefault(t.section, []).append(t)

    for section, tasks in by_section.items():
        with st.expander(f"**{section}** ({len(tasks)} tasks)"):
            for t in sorted(tasks, key=lambda x: x.priority):
                status_icon = "🔴" if t.is_overdue else ("🟡" if t.is_due_today else "⚪")
                due = f" 📅 {t.due_date}" if t.due_date else ""
                st.markdown(f"{status_icon} {t.description}{due}")
else:
    st.info("No tasks in this week's weekly note. Go to **Weekly Planning** to set up your week.")
