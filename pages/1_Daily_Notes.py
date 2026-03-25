"""Daily Notes – unified daily workflow.

One page, one flow:
1. Auto-create today's daily note if needed
2. AI-recommended Top 3 tasks
3. Triage: yesterday incomplete + overdue (bring forward / reschedule / cancel)
4. Case Pricing tasks
5. Select from due-today and due-soon tasks
6. Write all selections to today's daily note
"""

import streamlit as st
from datetime import date

from config import DAILY_FOLDER, CASE_PRICING_FOLDER
from core.models import TaskStatus
from core.rescan import rescan_vault
from core.task_parser import get_all_tasks
from core.task_writer import (
    append_task_to_section,
    build_project_source_comment,
    move_task_to_tomorrow_section,
    sync_due_date,
    sync_task_status,
)
from ai.planner import get_planner
from workflows.daily_selection import daily_selection_groups
from workflows.carryover import find_todays_note
from workflows.weekly_planning import get_weekly_note_tasks
from templates.engine import create_daily_note

st.set_page_config(page_title="Daily Notes", page_icon="📋", layout="wide")
st.title("📋 Daily Notes")
st.caption(f"Today is **{date.today().strftime('%A, %B %d, %Y')}**")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes

# ── Section heading constants (must match templates/engine.py exactly) ─

SECTION_TOP3 = "🔥 Top 3 Must-Do Today"
SECTION_DAILY_TASKS = "✅ Daily Task List"
SECTION_CARRYOVER = "📥 Carryover From Yesterday"
SECTION_CASE_PRICINGS = "Case Pricings"


# ── Ensure today's daily note exists ──────────────────────────────────

def _ensure_todays_note():
    """Find or create today's daily note. Always returns a NoteFile."""
    todays = find_todays_note(notes, DAILY_FOLDER)
    if todays:
        return todays
    # Auto-create
    create_daily_note(st.session_state.vault_path, DAILY_FOLDER)
    rescan_vault()
    # Re-fetch after rescan
    refreshed = st.session_state.notes
    return find_todays_note(refreshed, DAILY_FOLDER)


todays_note = find_todays_note(notes, DAILY_FOLDER)
if not todays_note:
    st.info("No daily note for today yet — it will be created automatically when you add tasks.")


# ── Helpers ───────────────────────────────────────────────────────────

def _task_key(t) -> str:
    return f"{t.file_path.stem}_{t.line_number}"


def _prio_icon(t) -> str:
    return {1: "🔺", 2: "⏫", 3: "", 4: "🔽", 5: "⏬"}.get(t.priority, "")


def _is_case_pricing(t) -> bool:
    return t.source_folder == CASE_PRICING_FOLDER


def _build_task_line(t) -> str:
    """Build the markdown line to write into the daily note."""
    line = f"- [ ] {t.description}"
    if t.due_date:
        line += f" 📅 {t.due_date.isoformat()}"
    if t.project_source and t.project_line:
        line += f" <!-- project:{t.project_source}:{t.project_line} -->"
    else:
        comment = build_project_source_comment(t, st.session_state.vault_path)
        if comment.strip():
            line += f" {comment}"
    return line


# ── Gather all data ──────────────────────────────────────────────────

groups = daily_selection_groups(notes)
all_open = [t for t in get_all_tasks(notes) if t.status == TaskStatus.OPEN]
planner = get_planner(use_llm=False)

# Initialise bring_forward tracking
if "bring_forward" not in st.session_state:
    st.session_state.bring_forward = set()

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: AI SMART SUMMARY
# ═══════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("🧠 Today's Focus – AI Recommendations")

top_tasks = planner.rank_tasks(all_open, top_n=3)

if top_tasks:
    st.markdown("Based on urgency, priority, and deadlines, here's what matters most today:")
    for i, t in enumerate(top_tasks, 1):
        status_icon = "🔴" if t.is_overdue else ("🟡" if t.is_due_today else "🟢")
        due_str = f" · due {t.due_date}" if t.due_date else ""
        source = "Case Pricing" if _is_case_pricing(t) else t.file_path.stem
        st.markdown(
            f"**{i}.** {status_icon} {_prio_icon(t)} {t.description}{due_str}  \n"
            f"&nbsp;&nbsp;&nbsp;&nbsp;*{source}*"
        )

    if st.button("⚡ Write Top 3 to Today's Note", key="write_top3"):
        note = _ensure_todays_note()
        for t in top_tasks[:3]:
            section = SECTION_CASE_PRICINGS if _is_case_pricing(t) else SECTION_TOP3
            append_task_to_section(note.path, section, _build_task_line(t))
        rescan_vault()
        st.success("Top 3 written to today's note!")
        st.rerun()
else:
    st.success("No open tasks to recommend – enjoy your day!")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: TRIAGE – Yesterday Incomplete + Overdue
# ═══════════════════════════════════════════════════════════════════════

yesterday_tasks = groups["yesterday_incomplete"]
overdue_tasks = groups["overdue"]
triage_tasks = yesterday_tasks + overdue_tasks

if triage_tasks:
    st.divider()
    st.subheader(f"⚠️ Triage – Needs Attention ({len(triage_tasks)})")
    st.caption(
        "These tasks are overdue or weren't completed yesterday. "
        "Decide: bring forward, reschedule, or remove."
    )

    # -- Yesterday incomplete --
    if yesterday_tasks:
        st.markdown("#### 📥 Not Completed Yesterday")
        st.caption(
            "Bringing these forward ticks them in yesterday's note "
            "and adds a fresh copy to today."
        )
        for t in yesterday_tasks:
            key = _task_key(t)
            due_str = f" 📅 {t.due_date}" if t.due_date else ""

            col1, col2, col3 = st.columns([0.55, 0.25, 0.20])
            with col1:
                st.markdown(f"🟠 {_prio_icon(t)} **{t.description}**{due_str}")
                st.caption(f"{t.file_path.stem} · {t.section}")
            with col2:
                if st.button("➡️ Bring Forward", key=f"fwd_y_{key}"):
                    st.session_state.bring_forward.add(f"y_{key}")
                    st.rerun()
                if f"y_{key}" in st.session_state.bring_forward:
                    st.success("Will add to today")
            with col3:
                if st.button("✅ Done", key=f"done_y_{key}"):
                    updated = sync_task_status(
                        t, TaskStatus.DONE, st.session_state.vault_path
                    )
                    rescan_vault()
                    st.toast(f"Done! Synced: {', '.join(updated)}")
                    st.rerun()
                if st.button("❌ Cancel", key=f"cancel_y_{key}"):
                    updated = sync_task_status(
                        t, TaskStatus.CANCELLED, st.session_state.vault_path
                    )
                    rescan_vault()
                    st.toast(f"Cancelled. Synced: {', '.join(updated)}")
                    st.rerun()

    # -- Overdue from projects/case pricing --
    if overdue_tasks:
        st.markdown("#### 🔴 Overdue from Projects / Case Pricing")
        for project, tasks in groups["overdue_by_project"].items():
            st.markdown(f"**{project}**")
            for t in tasks:
                key = _task_key(t)
                days = (date.today() - t.due_date).days if t.due_date else 0

                col1, col2, col3 = st.columns([0.45, 0.30, 0.25])
                with col1:
                    st.markdown(
                        f"🔴 {_prio_icon(t)} **{t.description}** ({days}d overdue)"
                    )
                    st.caption(f"{t.file_path.stem} · {t.section}")
                with col2:
                    if st.button("➡️ Bring Forward", key=f"fwd_o_{key}"):
                        st.session_state.bring_forward.add(f"o_{key}")
                        st.rerun()
                    if f"o_{key}" in st.session_state.bring_forward:
                        st.success("Will add to today")
                    new_date = st.date_input(
                        "Reschedule",
                        value=date.today(),
                        min_value=date.today(),
                        key=f"date_o_{key}",
                        label_visibility="collapsed",
                    )
                    if st.button("📅 Reschedule", key=f"redate_o_{key}"):
                        updated = sync_due_date(
                            t, new_date.strftime("%Y-%m-%d"),
                            st.session_state.vault_path,
                        )
                        rescan_vault()
                        st.toast(f"Rescheduled to {new_date} ({', '.join(updated)})")
                        st.rerun()
                with col3:
                    if st.button("✅ Done", key=f"done_o_{key}"):
                        updated = sync_task_status(
                            t, TaskStatus.DONE, st.session_state.vault_path
                        )
                        rescan_vault()
                        st.toast(f"Done! Synced: {', '.join(updated)}")
                        st.rerun()
                    if st.button("❌ Cancel", key=f"cancel_o_{key}"):
                        updated = sync_task_status(
                            t, TaskStatus.CANCELLED, st.session_state.vault_path
                        )
                        rescan_vault()
                        st.toast(f"Cancelled. Synced: {', '.join(updated)}")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: CASE PRICING TASKS
# ═══════════════════════════════════════════════════════════════════════

case_pricing_tasks = groups.get("case_pricing", [])
# Exclude any already shown in overdue triage
overdue_keys = {_task_key(t) for t in overdue_tasks}
case_pricing_fresh = [t for t in case_pricing_tasks if _task_key(t) not in overdue_keys]

selected_case_pricing: list = []

if case_pricing_fresh:
    st.divider()
    st.subheader(f"💼 Case Pricing ({len(case_pricing_fresh)})")
    for project, tasks in groups.get("case_pricing_by_project", {}).items():
        fresh = [t for t in tasks if _task_key(t) not in overdue_keys]
        if not fresh:
            continue
        st.markdown(f"**{project}**")
        for t in sorted(fresh, key=lambda x: (x.due_date or date.max, x.priority)):
            due_str = f" (due {t.due_date})" if t.due_date else ""
            label = f"💼 {_prio_icon(t)} {t.description}{due_str}"
            if st.checkbox(label, key=f"cp_{_task_key(t)}"):
                selected_case_pricing.append(t)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: TODAY'S TASK SELECTION (due today -> due soon)
# ═══════════════════════════════════════════════════════════════════════

due_today = groups["due_today"]
due_soon = groups["due_soon"]

if due_today or due_soon:
    st.divider()
    st.subheader("📅 Tasks by Due Date")

selected_today: list = []
selected_soon: list = []

# -- Due today --
if due_today:
    st.markdown(f"#### 🟡 Due Today ({len(due_today)})")
    for project, tasks in groups["due_today_by_project"].items():
        st.markdown(f"**{project}**")
        for t in sorted(tasks, key=lambda x: x.priority):
            label = f"🟡 {_prio_icon(t)} {t.description}"
            if st.checkbox(label, key=f"today_{_task_key(t)}"):
                selected_today.append(t)

# -- Due soon --
if due_soon:
    st.markdown(f"#### ⚪ Due This Week ({len(due_soon)})")
    for project, tasks in groups["due_soon_by_project"].items():
        st.markdown(f"**{project}**")
        for t in sorted(tasks, key=lambda x: (x.due_date or date.max, x.priority)):
            days_until = (t.due_date - date.today()).days if t.due_date else 0
            label = f"⚪ {_prio_icon(t)} {t.description} (in {days_until}d)"
            if st.checkbox(label, key=f"soon_{_task_key(t)}"):
                selected_soon.append(t)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: COMMIT – Write selections to today's daily note
# ═══════════════════════════════════════════════════════════════════════

# Gather all "bring forward" tasks from triage
bring_forward_yesterday = [
    t for t in yesterday_tasks
    if f"y_{_task_key(t)}" in st.session_state.get("bring_forward", set())
]
bring_forward_overdue = [
    t for t in overdue_tasks
    if f"o_{_task_key(t)}" in st.session_state.get("bring_forward", set())
]

all_to_add = (
    bring_forward_yesterday
    + bring_forward_overdue
    + selected_case_pricing
    + selected_today
    + selected_soon
)

st.divider()
if all_to_add:
    st.subheader(f"📝 Ready to Add: {len(all_to_add)} tasks")

    # Warn if selecting too many
    if len(all_to_add) > 7:
        st.warning(
            f"You've selected {len(all_to_add)} tasks. "
            "Productivity research suggests focusing on 3-5 key tasks per day. "
            "Consider trimming your list."
        )

    for t in all_to_add:
        if _is_case_pricing(t):
            status = "💼"
        elif t in bring_forward_yesterday:
            status = "🟠"
        elif t in bring_forward_overdue:
            status = "🔴"
        elif t.is_due_today:
            status = "🟡"
        else:
            status = "⚪"
        st.markdown(f"- {status} {t.description}")

    if st.button("📋 Add All to Today's Daily Note", type="primary"):
        # Auto-create today's note if it doesn't exist yet
        note = _ensure_todays_note()

        # 1. Handle yesterday carryovers (tick + move to tomorrow in yesterday's note)
        for t in bring_forward_yesterday:
            move_task_to_tomorrow_section(t)
            section = SECTION_CASE_PRICINGS if _is_case_pricing(t) else SECTION_DAILY_TASKS
            append_task_to_section(note.path, section, _build_task_line(t))

        # 2. Handle overdue brought forward
        for t in bring_forward_overdue:
            section = SECTION_CASE_PRICINGS if _is_case_pricing(t) else SECTION_DAILY_TASKS
            append_task_to_section(note.path, section, _build_task_line(t))

        # 3. Handle case pricing selections
        for t in selected_case_pricing:
            append_task_to_section(note.path, SECTION_CASE_PRICINGS, _build_task_line(t))

        # 4. Handle due-today and due-soon selections
        for t in selected_today + selected_soon:
            section = SECTION_CASE_PRICINGS if _is_case_pricing(t) else SECTION_DAILY_TASKS
            append_task_to_section(note.path, section, _build_task_line(t))

        # Clear the bring_forward state
        st.session_state.bring_forward = set()

        rescan_vault()
        st.success(f"Added {len(all_to_add)} tasks to today's note!")
        st.rerun()
else:
    st.info("Select tasks above to add to today's daily note.")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: WEEKLY OVERVIEW (read-only reference)
# ═══════════════════════════════════════════════════════════════════════

st.divider()
with st.expander("📋 This Week's Tasks (from Weekly Note)", expanded=False):
    weekly_tasks = get_weekly_note_tasks(notes)
    if weekly_tasks:
        by_section: dict[str, list] = {}
        for t in weekly_tasks:
            by_section.setdefault(t.section, []).append(t)

        for section, tasks in by_section.items():
            st.markdown(f"**{section}** ({len(tasks)} tasks)")
            for t in sorted(tasks, key=lambda x: x.priority):
                status_icon = "🔴" if t.is_overdue else (
                    "🟡" if t.is_due_today else "⚪"
                )
                due = f" 📅 {t.due_date}" if t.due_date else ""
                st.markdown(f"&nbsp;&nbsp;{status_icon} {t.description}{due}")
    else:
        st.info(
            "No tasks in this week's weekly note. "
            "Go to **Weekly Planning** to set up your week."
        )

# ── Scoring explanation (collapsed) ──────────────────────────────────

with st.expander("ℹ️ How AI recommendations work"):
    st.markdown("""
**Rule-based scoring:**
- **Overdue** → +50 pts (+ 2 pts per day overdue, max +20)
- **Due today** → +30 pts
- **Due this week** → +15 pts
- **Priority** → (6 − priority) × 10 pts (priority 1 = 50 pts)
- **Case Pricing** → +5 pts (deadline-driven work)

*Future: LLM integration will consider context, workload balance, and energy patterns.*
""")
