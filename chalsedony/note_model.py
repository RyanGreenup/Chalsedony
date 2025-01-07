from datetime import datetime
from sqlite3 import Connection
from pathlib import Path
from typing import Dict, List, Optional
from db_api import Note, Folder

from PySide6.QtCore import QObject, Signal

NOTES_FILE = Path("/tmp/notes.yml")
API_URL = "http://eir:37242"  # TODO inherit from cli


class NoteModel(QObject):
    refreshed = Signal()  # Notify view to refresh

    def __init__(self, db_connection: Connection) -> None:
        super().__init__()
        base_url = API_URL
        self.db_connection = db_connection

    # TODO
    # def find_note_by_id(self, note_id: int) -> Optional[Note]:
    #     """Find a note by its ID in the entire tree"""
    #     pass

    # TODO
    # def get_all_notes(self) -> List[Note]:
    #     """Get all notes from all folders"""

    def on_note_content_changed(self, note_id: int, content: str) -> None:
        """Handle note content changes from view"""
        print("Note content changed")


    def create_note(self, parent_folder_id: int) -> None:
        """Create a new note under the specified folder"""
        print("Trying to create a new note")


    # TODO
    # def _get_next_note_id(self) -> str:
    #     """Get the next available note ID"""
    #     all_notes = self.get_all_notes()
    #     return max(note.id for note in all_notes) + 1 if all_notes else 1



# Implement the method to get the tree data  AI!
    def get_note_tree_structure():

