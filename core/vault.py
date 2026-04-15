"""Vault scanner – discovers markdown files in configured folders."""

from pathlib import Path

from config import SCAN_FOLDERS, EXCLUDE_FOLDERS
from core.models import NoteFile


def get_vault_path(vault_path: str) -> Path:
    """Return validated vault path."""
    p = Path(vault_path).expanduser().resolve()
    if not p.is_dir():
        raise FileNotFoundError(f"Vault path does not exist: {p}")
    return p


def scan_vault(vault_path: str, folders: list[str] | None = None) -> list[NoteFile]:
    """Scan configured folders and return NoteFile objects (without parsed tasks)."""
    vault = get_vault_path(vault_path)
    folders = folders or SCAN_FOLDERS
    notes: list[NoteFile] = []

    for folder in folders:
        folder_path = vault / folder
        if not folder_path.is_dir():
            continue
        for md_file in sorted(folder_path.rglob("*.md")):
            rel = str(md_file.relative_to(vault))
            # Skip if the file matches any excluded folder path
            if any(excl in md_file.as_posix() for excl in EXCLUDE_FOLDERS):
                continue
            notes.append(NoteFile(path=md_file, relative_path=rel, folder=folder))

    return notes


def scan_folder(vault_path: str, folder: str) -> list[NoteFile]:
    """Scan a single folder."""
    return scan_vault(vault_path, folders=[folder])
