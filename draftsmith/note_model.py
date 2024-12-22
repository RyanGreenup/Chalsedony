from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Note(BaseModel):
    id: int
    title: str
    created_at: datetime
    modified_at: datetime


class Folder(BaseModel):
    id: int
    name: str
    children: List['Folder']
    notes: List[Note]


class NoteTreeModel:
    def __init__(self):
        self._root_folders: List[Folder] = []

    def load_data(self, data: List[dict]) -> None:
        """Load data from JSON-like structure into the model"""
        self._root_folders = [Folder.model_validate(folder) for folder in data]

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
        def find_path(folders: List[Folder], target_id: int, current_path: List[Folder]) -> Optional[List[Folder]]:
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
