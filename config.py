"""
Configuration for Obsidian Daily Task Runner.
Set OBSIDIAN_VAULT_PATH env var or edit DEFAULT_VAULT_PATH.
"""

import os
from pathlib import Path

DEFAULT_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", str(Path.home() / "ObsidianVault"))

SCAN_FOLDERS = [
    "To Do/01 Daily",
    "To Do/02 Weekly",
    "To Do/03 Projects",
    "To Do/06 Case Pricing",
]

EXCLUDE_FOLDERS = [
    "To Do/03 Projects/Completed",
]

DAILY_FOLDER = "To Do/01 Daily"
WEEKLY_FOLDER = "To Do/02 Weekly"
PROJECTS_FOLDER = "To Do/03 Projects"
CASE_PRICING_FOLDER = "To Do/06 Case Pricing"

DATE_FORMAT = "%Y-%m-%d"
DAILY_NOTE_PREFIX = ""  # e.g. "Daily - " if you prefix daily notes
WEEKLY_NOTE_PREFIX = "Week of "

# Obsidian Tasks plugin priority markers
PRIORITY_MAP = {
    "🔺": 1,   # highest
    "⏫": 2,   # high
    "🔼": 3,   # medium
    "🔽": 4,   # low
    "⏬": 5,   # lowest
}

# Default priority for tasks without a marker
DEFAULT_PRIORITY = 3
