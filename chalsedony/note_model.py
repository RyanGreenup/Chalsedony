from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from api_client import NoteAPI, TagAPI, Note, TreeTagWithNotes, TreeNote

from PySide6.QtCore import QObject, Signal
from pydantic import BaseModel
import yaml

NOTES_FILE = Path("/tmp/notes.yml")
API_URL = "http://eir:37242"  # TODO inherit from cli


# OK, so what we need to do here is take the `TreeTagWithNotes` and use it as the model
# It will have no content by default, when the user requests it, check for None and fetch it.
# The model will keep a copy of the TreeTagWithNotes in memory and update it when the user modifies it
# the model will attempt to mirror the api representation of the TreeTagWithNotes on the server as closely as possible
# A refresh signal will tell the view to update its representation of the in-memory model
# If this receives a refresh signal, it will pull down the latest data from the server and send a refresh signal to the view
# This means the content in memory would be lost and need to be pulled again for each one.


def attach_notes_to_tags(
    tag_tree: List[TreeTagWithNotes], note_map: Dict[int, TreeNote]
) -> None:
    """
    Recursively attaches notes to tags based on the tag IDs present in the notes.

    Args:
        tag_tree (List[TreeTagWithNotes]): The list of tags with their hierarchical structure.
        note_map (Dict[int, TreeNote]): A dictionary mapping note IDs to TreeNote objects for quick lookup.
    """
    for tag in tag_tree:
        # Attach notes that have this tag
        tag.notes.extend(
            [
                note
                for note in note_map.values()
                if any(t.id == tag.id for t in note.tags)
            ]
        )

        # Recursively attach notes to children tags
        if tag.children:
            attach_notes_to_tags(tag.children, note_map)




class NoteModel(QObject):
    refreshed = Signal()  # Notify view to refresh

    def __init__(self) -> None:
        super().__init__()
        self._root_folders: List[TreeTagWithNotes] = []
        base_url = API_URL
        self.note_api = NoteAPI(base_url)
        self.tag_api = TagAPI(base_url)
        self._load_from_remote()

    def fetch_and_attach_notes_to_tags(self,
        note_api: NoteAPI, tag_api: TagAPI
    ) -> List[TreeTagWithNotes]:
        # Fetch tags tree
        self.tag_tree = tag_api.get_tags_tree()

        # Fetch notes tree
        print("Fetching notes")
        self.notes_tree = note_api.get_notes_tree(exclude_content=True)

        # Flatten the notes tree into a dictionary for quick lookup by ID
        self.note_map: Dict[int, TreeNote] = {}

        def flatten_notes(notes: List[TreeNote]) -> None:
            for note in notes:
                self.note_map[note.id] = note
                if note.children:
                    flatten_notes(note.children)

        flatten_notes(self.notes_tree)

        # Attach notes to tags
        attach_notes_to_tags(self.tag_tree, self.note_map)

    def _load_from_remote(self) -> None:
        """Load data from YAML file if it exists"""
        tags = (
            self.tag_api.get_tags_tree()
        )  # TODO there's two calls here, only need one
        # Resolve this by refactoring `fetch_and_attach_notes_to_tags` to take the tag tree as an argument
        tagged_notes_and_subpages = self.fetch_and_attach_notes_to_tags(
            self.note_api, self.tag_api
        )
        self.load_data(tagged_notes_and_subpages, tags)

    def load_data(
        self, data: List[TreeTagWithNotes], tags: List[TreeTagWithNotes]
    ) -> None:
        """Load data from JSON-like structure into the model"""
        self._root_folders = tags

    def get_root_folders(self) -> List[TreeTagWithNotes]:
        """Return all root level folders"""
        return self._root_folders

    def find_folder_by_id(self, folder_id: int) -> Optional[TreeTagWithNotes]:
        """Find a folder by its ID in the entire tree"""

        # TODO, could this be made more efficient with a hashmap? Create one on load and store as attribute?

        def search_folder(
            folders: List[TreeTagWithNotes],
        ) -> Optional[TreeTagWithNotes]:
            for folder in folders:
                if folder.id == folder_id:
                    return folder
                result = search_folder(folder.children)
                if result:
                    return result
            return None

        return search_folder(self._root_folders)

    def find_note_by_id(self, note_id: int) -> Optional[TreeNote]:
        """Find a note by its ID in the entire tree"""
        return self.note_map.get(note_id)


    def get_folder_path(self, folder_id: int) -> List[TreeTagWithNotes]:
        """Get the path from root to the specified folder"""

        def find_path(
            folders: List[TreeTagWithNotes],
            target_id: int,
            current_path: List[TreeTagWithNotes],
        ) -> Optional[List[TreeTagWithNotes]]:
            for folder in folders:
                new_path = current_path + [folder]
                if folder.id == target_id:
                    return new_path
                result = find_path(folder.children, target_id, new_path)
                if result:
                    return result
            return None

        path = find_path(self._root_folders, folder_id, [])
        return path if path else []

    def get_all_notes(self) -> List[Note]:
        """Get all notes from all folders"""
        notes: List[Note] = []

        def collect_notes(folders: List[TreeTagWithNotes]) -> None:
            for folder in folders:
                notes.extend(folder.notes)
                collect_notes(folder.children)

        collect_notes(self._root_folders)
        return notes

    def on_note_content_changed(self, note_id: int, content: str) -> None:
        """Handle note content changes from view"""
        self.save(note_id, content)

    def update_note(self, note_id: int, content: str) -> None:
        """Handle note content changes from view

        This receives the note ID and the new content, and updates the models
        internal representation of the note. It does not save to disk
        (use `save` method for that which updates the model representation
         **and** saves to disk)

        """
        note_ptr = self.find_note_by_id(note_id)
        if note_ptr:
            note_ptr.content = content
            note_ptr.modified_at = datetime.now()
        else:
            raise ValueError(f"Note with ID {note_id} not found")

    def refresh(self) -> None:
        """Refresh the model from the file"""
        # Load the data from the file
        self._load_from_remote()
        # Notify the view to refresh
        self.refreshed.emit()

    def save(self, note_id: int, content: str) -> None:
        """Update the model representation of a note and save to disk

        Note, if this is being called, the developer may want to:

            - Refresh the view (It may be ok, but there may be bugs in the a
                                attempt to mirror the model in the view)
                see: `refreshed` signal and `refresh` method
            - Save across all tabs (especially if refreshing the view)"""
        return
        # Update the given note
        self.update_note(note_id, content)

        # Save to disk
        self._save_to_file()

    def create_note(self, parent_folder_id: int) -> None:
        """Create a new note under the specified folder"""
        parent_folder = self.find_folder_by_id(parent_folder_id)
        if parent_folder:
            new_note = Note(
                id=self._get_next_note_id(),
                title="New Note",
                content="",
            )
            parent_folder.notes.append(new_note)
            self._save_to_file()
        else:
            raise ValueError(f"TreeTagWithNotes with ID {parent_folder_id} not found")

        # Emit a signal to refresh the view
        # NOTE: here the model is in perfect sync with the underlying data
        # as the memory representation clobbers the file
        # In a more complex system, we might want to reload the data from the file / api
        # and/or take great care to keep the model in sync with the upstream data
        self.refreshed.emit()

    def _get_next_note_id(self) -> int:
        """Get the next available note ID"""
        all_notes = self.get_all_notes()
        return max(note.id for note in all_notes) + 1 if all_notes else 1
