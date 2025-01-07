from sqlite3 import Connection
from pathlib import Path
from typing import Dict, List, Optional
# AI: Import the model from db_api here
from db_api import Note

from PySide6.QtCore import QObject, Signal

NOTES_FILE = Path("/tmp/notes.yml")
API_URL = "http://eir:37242"  # TODO inherit from cli


class NoteModel(QObject):
    refreshed = Signal()  # Notify view to refresh

    def __init__(self, db_connection: Connection) -> None:
        super().__init__()
        self.db_connection = db_connection

    def find_note_by_id(self, note_id: int) -> Optional[Note]:
        """Find a note by its ID in the entire tree"""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()

        if row:
            return Note(**row)
        return None

    def get_all_notes(self) -> List[Note]:
        """Get all notes from all folders"""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM notes")
        return [Note(**row) for row in cursor.fetchall()]

    def on_note_content_changed(self, note_id: int, content: str) -> None:
        """Handle note content changes from view"""
        print(f"Note content changed for note ID {note_id}")
        print(f"New content: {content}")

    def create_note(self, parent_folder_id: int) -> None:
        """Create a new note under the specified folder"""
        print(f"Trying to create a new note under folder ID {parent_folder_id}")

    # Fix this to instead return a pydantic dictionary AI!
    def get_note_tree_structure(self) -> Dict[str, dict]:
        """Get the folder/note tree structure from the database

        Returns:
            A dictionary where keys are folder IDs and values are folder data including:
            - type: "folder"
            - title: folder title
            - parent_id: parent folder ID or None
            - notes: list of notes in this folder
        """
        cursor = self.db_connection.cursor()

        # Get all folders
        cursor.execute("SELECT * FROM folders")
        folders = {
            row["id"]: {
                "type": "folder",
                "title": row["title"],
                "parent_id": row["parent_id"],
                "notes": [],
            }
            for row in cursor.fetchall()
        }

        # Get all notes and organize them under their folders
        cursor.execute("SELECT * FROM notes")
        for note_row in cursor.fetchall():
            folder_id = note_row["parent_id"]
            if folder_id in folders:
                folders[folder_id]["notes"].append(
                    {"id": note_row["id"], "title": note_row["title"]}
                )

        return folders

    def refresh(self) -> None:
        """Refresh the model"""
        print("TODO implement this")
