# Obsidian Daily Task Runner

A local-first Python Streamlit app that integrates with your Obsidian vault to manage tasks across Daily, Weekly, Project, and Case Pricing notes.

## Features

- **Vault Scanner** – Scans `To Do/01 Daily`, `To Do/02 Weekly`, `To Do/03 Projects`, `To Do/06 Case Pricing`
- **Task Parser** – Parses markdown checkboxes with Obsidian Tasks plugin metadata (due dates, scheduled dates, completion dates, priority markers)
- **Morning Review** – See today's tasks, overdue items, and yesterday's carryover
- **Weekly Planning** – Plan your week with tasks grouped by priority and folder
- **Overdue Task Review** – Review and act on overdue items, grouped by age
- **Carryover** – Move yesterday's incomplete tasks to today's note
- **Daily Selection** – Pick focus tasks from all open tasks and write them to your daily note
- **Template Engine** – Create daily, weekly, project, and case pricing notes from your templates
- **AI Planner** – Rule-based task prioritization with a pluggable interface for future LLM integration

## Quick Start

```bash
# Clone and setup
chmod +x setup.sh
./setup.sh

# Set your vault path
export OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# Run
source .venv/bin/activate
streamlit run app.py
```

## Architecture

```
app.py                    # Streamlit entry point + dashboard
config.py                 # Configuration (vault path, folders, priorities)
core/
  models.py               # Data models (Task, NoteFile)
  vault.py                # Vault scanner
  task_parser.py          # Markdown task parser with Obsidian Tasks metadata
  task_writer.py          # Safe file writer (with .bak backups)
workflows/
  morning_review.py       # Morning review workflow
  weekly_planning.py      # Weekly planning workflow
  overdue.py              # Overdue task review
  carryover.py            # Carryover from yesterday
  daily_selection.py      # Daily task selection
templates/
  engine.py               # Note creation from templates
ai/
  planner.py              # Rule-based prioritization + LLM stub
pages/
  1_Morning_Review.py     # Streamlit page
  2_Weekly_Planning.py    # Streamlit page
  3_Overdue_Tasks.py      # Streamlit page
  4_Daily_Selection.py    # Streamlit page
  5_AI_Planner.py         # Streamlit page
```

## Obsidian Tasks Metadata Supported

| Marker | Meaning |
|--------|---------|
| `[ ]` | Open task |
| `[x]` | Completed task |
| `[-]` | Cancelled task |
| `📅 YYYY-MM-DD` | Due date |
| `⏳ YYYY-MM-DD` | Scheduled date |
| `✅ YYYY-MM-DD` | Done date |
| `🔺` | Highest priority |
| `⏫` | High priority |
| `🔼` | Medium priority |
| `🔽` | Low priority |
| `⏬` | Lowest priority |

## Configuration

Edit `config.py` or set environment variables:

- `OBSIDIAN_VAULT_PATH` – Path to your Obsidian vault (default: `~/ObsidianVault`)

## Assumptions & Limitations

- **Local-first**: No cloud sync, no database. Reads/writes markdown files directly.
- **File naming**: Daily notes must contain `YYYY-MM-DD` in the filename. Weekly notes use `Week of YYYY-MM-DD`.
- **Backup**: A `.bak` file is created before any write operation. Not a substitute for version control.
- **Obsidian Tasks queries**: The app does not execute Obsidian Tasks plugin query blocks (` ```tasks ... ``` `). It parses raw markdown checkboxes only.
- **Single user**: No auth, no multi-user support. Designed for personal use.
- **AI Planner**: Currently rule-based only. The `LLMPlanner` class is a stub ready for API integration.
