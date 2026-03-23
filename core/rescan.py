"""Helper to rescan the vault and refresh session state after a write."""

from __future__ import annotations

import streamlit as st

from core.vault import scan_vault
from core.task_parser import parse_all


def rescan_vault() -> None:
    """Re-scan the vault and update st.session_state.notes in place.

    Call this after any write operation so the UI reflects changes
    without the user having to manually click Scan Vault.
    """
    vault_path = st.session_state.get("vault_path", "")
    if not vault_path:
        return
    try:
        notes = scan_vault(vault_path)
        notes = parse_all(notes)
        st.session_state.notes = notes
    except FileNotFoundError:
        pass
