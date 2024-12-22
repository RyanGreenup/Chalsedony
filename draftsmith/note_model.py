from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import yaml

NOTES_FILE = Path("/tmp/notes.yml")


class Note(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime = datetime.now()
    modified_at: datetime = datetime.now()

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:  # type: ignore [no-untyped-def]
        # Convert datetime objects to ISO format strings for YAML serialization
        d = super().model_dump(*args, **kwargs)
        d["created_at"] = d["created_at"].isoformat()
        d["modified_at"] = d["modified_at"].isoformat()
        return d


class Folder(BaseModel):
    id: int
    name: str
    children: List["Folder"] = []
    notes: List[Note] = []


class NoteModel:
    def __init__(self) -> None:
        self._root_folders: List[Folder] = []
        self._load_from_file()

    def _load_from_file(self) -> None:
        """Load data from YAML file if it exists"""
        if NOTES_FILE.exists():
            with NOTES_FILE.open("r") as f:
                data = yaml.safe_load(f)
                if data:
                    self.load_data(data)
        else:
            # Initialize with dummy data if file doesn't exist
            self._root_folders = self.__class__.generate_dummy_data()
            self._save_to_file()

    def _save_to_file(self) -> None:
        """Save current data to YAML file"""
        data = [folder.model_dump() for folder in self._root_folders]
        with NOTES_FILE.open("w") as f:
            yaml.safe_dump(data, f, default_flow_style=False)

    @classmethod
    def generate_dummy_data(cls) -> List[Folder]:
        """Generate dummy data for development purposes.
        Returns a list of folders rather than setting internal state."""
        # Create some notes
        note1 = Note(id=1, title="First Note", content="This is the first note")
        note2 = Note(id=2, title="Second Note", content="This is the second note")

        # Create a subfolder with a note
        subfolder = Folder(id=3, name="Subfolder", children=[], notes=[note2])

        # Create a root folder with notes and a subfolder
        root_folder = Folder(
            id=1, name="Root Folder", children=[subfolder], notes=[note1]
        )

        return [root_folder]

    def load_data(self, data: List[Folder]) -> None:
        """Load data from JSON-like structure into the model"""
        self._root_folders = [Folder.model_validate(folder) for folder in data]
        self._save_to_file()

    def get_root_folders(self) -> List[Folder]:
        """Return all root level folders"""
        return self._root_folders

    def find_folder_by_id(self, folder_id: int) -> Optional[Folder]:
        """Find a folder by its ID in the entire tree"""

        def search_folder(folders: List[Folder]) -> Optional[Folder]:
            for folder in folders:
                if folder.id == folder_id:
                    return folder
                result = search_folder(folder.children)
                if result:
                    return result
            return None

        return search_folder(self._root_folders)

    def find_note_by_id(self, note_id: int) -> Optional[Note]:
        """Find a note by its ID in the entire tree"""

        def search_note(folders: List[Folder]) -> Optional[Note]:
            for folder in folders:
                for note in folder.notes:
                    if note.id == note_id:
                        return note
                result = search_note(folder.children)
                if result:
                    return result
            return None

        return search_note(self._root_folders)

    def get_folder_path(self, folder_id: int) -> List[Folder]:
        """Get the path from root to the specified folder"""

        def find_path(
            folders: List[Folder], target_id: int, current_path: List[Folder]
        ) -> Optional[List[Folder]]:
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

        def collect_notes(folders: List[Folder]) -> None:
            for folder in folders:
                notes.extend(folder.notes)
                collect_notes(folder.children)

        collect_notes(self._root_folders)
        return notes


    def update_note_content(self, content: str) -> None:
        """Update the content of the currently selected note"""
        note = self.find_note_by_id(self.current_note_id)
        if note:
            note.content = content
            note.modified_at = datetime.now()
            self._save_to_file()
