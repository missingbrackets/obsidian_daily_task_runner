"""Projects page – manage project tasks (the source of truth for all tasks)."""

import streamlit as st
from datetime import date

from config import PROJECTS_FOLDER
from core.models import TaskStatus
from core.task_parser import get_all_tasks
from core.task_writer import append_task_to_section, toggle_task
from core.vault import scan_folder
from core.task_parser import parse_all
from templates.engine import create_project_note

st.set_page_config(page_title="Projects", page_icon="📁", layout="wide")
st.title("📁 Projects")
st.caption("Projects are the source of truth for tasks. Add tasks here, then pull them into weekly and daily notes.")

if not st.session_state.get("notes"):
    st.warning("Please scan your vault first from the main page.")
    st.stop()

notes = st.session_state.notes

# ── Get project notes and tasks ────────────────────────────────────────

project_notes = [n for n in notes if n.folder == PROJECTS_FOLDER]
project_tasks = [t for t in get_all_tasks(notes) if t.source_folder == PROJECTS_FOLDER]
open_tasks = [t for t in project_tasks if t.status == TaskStatus.OPEN]

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Projects", len(project_notes))
with col2:
    st.metric("Open Tasks", len(open_tasks))
with col3:
    overdue = [t for t in open_tasks if t.is_overdue]
    st.metric("Overdue", len(overdue))

st.divider()

# ── Create new project ────────────────────────────────────────────────

st.subheader("📝 Create New Project")
with st.form("new_project_form"):
    project_title = st.text_input("Project Title")
    submitted = st.form_submit_button("Create Project", type="primary")
    if submitted and project_title.strip():
        path = create_project_note(
            st.session_state.vault_path, PROJECTS_FOLDER, project_title.strip()
        )
        st.success(f"Created: {path.name}")
        st.info("Re-scan vault to see the new project.")

st.divider()

# ── Add task to existing project ───────────────────────────────────────

st.subheader("➕ Add Task to Project")
if project_notes:
    with st.form("add_task_form"):
        target_project = st.selectbox(
            "Project",
            options=project_notes,
            format_func=lambda n: n.path.stem,
        )
        task_desc = st.text_input("Task description")
        col_a, col_b = st.columns(2)
        with col_a:
            task_due = st.date_input("Due date (optional)", value=None)
        with col_b:
            task_priority = st.selectbox(
                "Priority",
                options=["Medium", "Highest", "High", "Low", "Lowest"],
            )

        add_submitted = st.form_submit_button("Add Task", type="primary")

        if add_submitted and task_desc.strip():
            prio_map = {"Highest": "🔺", "High": "⏫", "Medium": "", "Low": "🔽", "Lowest": "⏬"}
            line = f"- [ ] {task_desc.strip()}"
            if task_due:
                line += f" 📅 {task_due.isoformat()}"
            prio_emoji = prio_map.get(task_priority, "")
            if prio_emoji:
                line += f" {prio_emoji}"

            append_task_to_section(target_project.path, "Next Actions (Only physical, doable steps)", line)
            st.success(f"Added task to {target_project.path.stem}")
            st.info("Re-scan vault to refresh.")
else:
    st.info("No project files found. Create a project first.")

st.divider()

# ── Browse projects and their tasks ───────────────────────────────────

st.subheader("📂 All Projects")
for note in sorted(project_notes, key=lambda n: n.path.stem):
    note_tasks = [t for t in note.tasks if t.status == TaskStatus.OPEN]
    done_tasks = [t for t in note.tasks if t.status == TaskStatus.DONE]

    with st.expander(
        f"**{note.path.stem}** – {len(note_tasks)} open, {len(done_tasks)} done"
    ):
        if note_tasks:
            for t in note_tasks:
                due_str = f" 📅 {t.due_date}" if t.due_date else " (no due date)"
                prio_icon = {1: "🔺", 2: "⏫", 3: "", 4: "🔽", 5: "⏬"}.get(t.priority, "")
                status_icon = "🔴" if t.is_overdue else ("🟡" if t.is_due_today else "⚪")
                st.markdown(f"{status_icon} {prio_icon} {t.description}{due_str}")
        else:
            st.caption("No open tasks.")
