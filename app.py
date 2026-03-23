"""
Obsidian Daily Task Runner – Streamlit MVP

A local-first task management dashboard that works with your Obsidian vault.
"""

import streamlit as st
from pathlib import Path

from config import DEFAULT_VAULT_PATH, SCAN_FOLDERS, DAILY_FOLDER
from core.vault import scan_vault, get_vault_path
from core.task_parser import parse_all, get_all_tasks
from core.models import TaskStatus

st.set_page_config(
    page_title="Obsidian Task Runner",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    if "vault_path" not in st.session_state:
        st.session_state.vault_path = DEFAULT_VAULT_PATH
    if "notes" not in st.session_state:
        st.session_state.notes = []


init_session_state()

# ── Sidebar ────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Settings")

    vault_path = st.text_input(
        "Obsidian Vault Path",
        value=st.session_state.vault_path,
        help="Absolute path to your Obsidian vault root folder",
    )
    st.session_state.vault_path = vault_path

    if st.button("🔄 Scan Vault", type="primary", use_container_width=True):
        try:
            notes = scan_vault(vault_path)
            notes = parse_all(notes)
            st.session_state.notes = notes
            st.success(f"Scanned {len(notes)} files")
        except FileNotFoundError as e:
            st.error(str(e))

    st.divider()

    if st.session_state.notes:
        all_tasks = get_all_tasks(st.session_state.notes)
        open_tasks = [t for t in all_tasks if t.status == TaskStatus.OPEN]
        done_tasks = [t for t in all_tasks if t.status == TaskStatus.DONE]

        st.metric("Total Files", len(st.session_state.notes))
        st.metric("Open Tasks", len(open_tasks))
        st.metric("Completed Tasks", len(done_tasks))

        overdue = [t for t in open_tasks if t.is_overdue]
        if overdue:
            st.metric("⚠️ Overdue", len(overdue))

    st.divider()
    st.caption("Navigate using the pages in the sidebar above.")

# ── Main Page ──────────────────────────────────────────────────────────

st.title("📋 Obsidian Daily Task Runner")
st.markdown("A local-first task dashboard for your Obsidian vault.")

if not st.session_state.notes:
    st.info(
        "👈 Set your vault path in the sidebar and click **Scan Vault** to get started."
    )
    st.markdown("""
### Quick Start

1. Enter the path to your Obsidian vault in the sidebar
2. Click **Scan Vault** to discover your tasks
3. Use the pages in the sidebar to:
   - **Morning Review** – See today's tasks, overdue items, and yesterday's carryover
   - **Weekly Planning** – Pull project tasks due this week into the weekly note
   - **Overdue Tasks** – Review, reschedule, or close overdue items
   - **Daily Selection** – Pick today's focus tasks from the weekly note
   - **AI Planner** – Get AI-powered task prioritization suggestions
   - **Projects** – Create projects and tasks (the source of truth)

### Scanned Folders

The app scans these folders in your vault:
""")
    for f in SCAN_FOLDERS:
        st.markdown(f"- `{f}`")

else:
    # Dashboard overview
    all_tasks = get_all_tasks(st.session_state.notes)
    open_tasks = [t for t in all_tasks if t.status == TaskStatus.OPEN]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📂 Files Scanned", len(st.session_state.notes))
    with col2:
        st.metric("📝 Total Tasks", len(all_tasks))
    with col3:
        st.metric("🔓 Open", len(open_tasks))
    with col4:
        overdue = [t for t in open_tasks if t.is_overdue]
        st.metric("🔴 Overdue", len(overdue))

    st.divider()

    # Tasks by folder
    st.subheader("Tasks by Folder")
    folder_groups: dict[str, list] = {}
    for t in open_tasks:
        folder_groups.setdefault(t.source_folder, []).append(t)

    for folder, tasks in sorted(folder_groups.items()):
        with st.expander(f"📁 {folder} ({len(tasks)} open tasks)"):
            for t in tasks[:20]:
                status_icon = "🔴" if t.is_overdue else ("🟡" if t.is_due_today else "⚪")
                due_str = f" (due {t.due_date})" if t.due_date else ""
                st.markdown(f"{status_icon} {t.description}{due_str}")
            if len(tasks) > 20:
                st.caption(f"... and {len(tasks) - 20} more")
