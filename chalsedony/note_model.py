from datetime import datetime
from sqlite3 import Connection
from pathlib import Path
from typing import Dict, List, Optional
from db_api import Note, Folder

from PySide6.QtCore import QObject, Signal

NOTES_FILE = Path("/tmp/notes.yml")
API_URL = "http://eir:37242"  # TODO inherit from cli


# OK, so what we need to do here is take the `TreeTagWithNotes` and use it as the model
# It will have no content by default, when the user requests it, check for None and fetch it.
# The model will keep a copy of the TreeTagWithNotes in memory and update it when the user modifies it
# the model will attempt to mirror the api representation of the TreeTagWithNotes on the server as closely as possible
# A refresh signal will tell the view to update its representation of the in-memory model
# If this receives a refresh signal, it will pull down the latest data from the server and send a refresh signal to the view
# This means the content in memory would be lost and need to be pulled again for each one.





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

