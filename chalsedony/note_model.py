import time
from PySide6.QtCore import QObject, Signal
from utils__get_first_markdown_heading import get_markdown_heading
from sqlite3 import Connection
from pathlib import Path
from typing import Dict, List, Optional, NamedTuple
from db_api import Note, Folder, FolderTreeItem, NoteSearchResult




NOTES_FILE = Path("/tmp/notes.yml")
API_URL = "http://eir:37242"  # TODO inherit from cli


class NoteModel(QObject):
    refreshed = Signal()  # Notify view to refresh

    def __init__(self, db_connection: Connection) -> None:
        super().__init__()
        self.db_connection = db_connection

    def find_note_by_id(self, note_id: str) -> Optional[Note]:
        """Find a note by its ID in the entire tree"""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()

        if row:
            # Convert tuple to dictionary using cursor description
            columns = [col[0] for col in cursor.description]
            row_dict = dict(zip(columns, row))
            return Note(**row_dict)
        return None

    def get_all_notes(self) -> List[NoteSearchResult]:
        """Get all notes from all folders
        
        Returns:
            List of NoteSearchResult containing note IDs and titles
        """
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT id, title FROM notes")
        return [NoteSearchResult(id=row[0], title=row[1]) for row in cursor.fetchall()]

    def on_note_content_changed(self, note_id: str, content: str) -> None:
        """Handle note content changes from view

        Args:
            note_id: ID of the note being updated
            content: New content for the note
        """
        self.save_note(note_id, content)

    def save_note(
        self,
        note_id: str,
        content: str,
        refresh: bool = False,
        update_title_from_heading: bool = False,
    ) -> None:
        """
        Write the content to the given note id

        Args:
            note_id: ID of the note being updated
            content: New content for the note
            refresh: Whether to emit refresh signal
            update_title_from_heading: Whether to update title from first markdown heading
        """
        title = None
        if update_title_from_heading:
            title = get_markdown_heading(content)

        self.update_note(note_id, body=content, title=title)
        if refresh:
            self.refreshed.emit()

    def create_note(self, parent_folder_id: int) -> None:
        """Create a new note under the specified folder"""
        print(f"Trying to create a new note under folder ID {parent_folder_id}")

    def get_note_tree_structure(
        self, order_by: str = "order"
    ) -> Dict[str, FolderTreeItem]:
        """Get the folder/note tree structure from the database

        params:
            order_by: The order in which to sort the notes. Default is "order" which
                      is the user custom order. Other options are "created_time", "updated_time", "title"

        Returns:
            A dictionary where keys are folder IDs and values are FolderTreeItem objects containing:
            - type: "folder"
            - folder: Folder model instance
            - parent_id: parent folder ID or None
            - notes: list of Note model instances in this folder
            - children: list of child FolderTreeItems (added)

        Implementation Notes:
            - Joplin marks notes as rubbish in a separate table, we don't consider that
              Either the note is deleted or it's not, so there may be a discrepancy in the number of notes
              between joplin and this GUI, If you want the notes gone, just empty the rubbish bin.

        Future work
            - Toggle ordering between Order field, modified, created, alphabetically

        """
        cursor = self.db_connection.cursor()
        cursor.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }

        # Get all folders
        cursor.execute("SELECT * FROM folders")
        folders = {}
        for row in cursor.fetchall():
            # Convert empty string parent_id to None
            parent_id = row["parent_id"]
            if parent_id == "":
                parent_id = None
            elif parent_id is not None:
                parent_id = str(parent_id)

            folders[row["id"]] = FolderTreeItem(
                type="folder",
                folder=Folder(**row),
                parent_id=parent_id,
                notes=[],
                children=[],
            )

        # Get all notes and organize them under their folders with multiple ordering criteria
        cursor.execute(f"""
            SELECT * FROM notes
            ORDER BY
                "{order_by}" ASC,
                title COLLATE NOCASE ASC,
                updated_time DESC,
                created_time DESC
        """)
        for note_row in cursor.fetchall():
            folder_id = note_row["parent_id"]
            if folder_id in folders:
                folders[folder_id].notes.append(Note(**note_row))

        # Build hierarchical structure
        root_folders = {}
        for folder_id, folder_data in folders.items():
            if folder_data.parent_id is None:
                # This is a root folder
                root_folders[folder_id] = folder_data
            else:
                # This is a child folder - add it to its parent's children
                if folder_data.parent_id in folders:
                    folders[folder_data.parent_id].children.append(folder_data)

        # Sort folders and their children by title
        def sort_folders(
            folder_dict: Dict[str, FolderTreeItem],
        ) -> Dict[str, FolderTreeItem]:
            """Sort folders by title in case-insensitive alphabetical order

            Args:
                folder_dict: Dictionary of folder IDs to FolderTreeItems

            Returns:
                Dictionary with folders sorted by title
            """
            # Convert dict to list of tuples and sort by folder title
            sorted_folders = sorted(
                folder_dict.items(), key=lambda x: x[1].folder.title.lower()
            )
            # Convert back to dict while maintaining order
            return dict(sorted_folders)

        # Sort root folders
        root_folders = sort_folders(root_folders)

        # Sort children of each folder
        for folder_data in folders.values():
            if folder_data.children:
                folder_data.children.sort(key=lambda x: x.folder.title.lower())

        return root_folders

    def refresh(self) -> None:
        """Refresh the model"""
        self.refreshed.emit()

    def search_notes(self, query: str) -> List[NoteSearchResult]:
        """Perform full text search on notes

        Args:
            query: The search query string

        Returns:
            List of NoteSearchResult containing note IDs and titles
        """
        cursor = self.db_connection.cursor()
        cursor.execute(
            """
            SELECT id, title,
                   length(title) - length(replace(lower(title), lower(?), '')) AS relevance
            FROM notes_fts
            WHERE notes_fts MATCH ?
            ORDER BY relevance DESC
        """,
            (query, query),
        )

        return [NoteSearchResult(id=row[0], title=row[1]) for row in cursor.fetchall()]

    def get_note_from_search_result(self, result: NoteSearchResult) -> Optional[Note]:
        """Get full note details from a search result

        Args:
            result: The NoteSearchResult to get full details for

        Returns:
            The full Note object if found, None otherwise
        """
        return self.find_note_by_id(result.id)

    def update_note(
        self,
        note_id: str,
        *,
        title: Optional[str] = None,
        body: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> None:
        """Update specific fields of a note

        Args:
            note_id: ID of the note to update
            title: New title (optional)
            body: New body content (optional)
            parent_id: New parent folder ID (optional)
        """
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if body is not None:
            updates.append("body = ?")
            params.append(body)
        if parent_id is not None:
            updates.append("parent_id = ?")
            params.append(parent_id)

        if not updates:
            return

        # Add updated_time
        updates.append("updated_time = ?")
        params.append(str(int(time.time())))  # Convert timestamp to string

        # Add note_id last for WHERE clause
        params.append(note_id)

        query = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?"

        cursor = self.db_connection.cursor()
        cursor.execute(query, params)
        self.db_connection.commit()

    def update_folder(
        self,
        folder_id: str,
        *,
        title: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> None:
        """Update specific fields of a folder

        Args:
            folder_id: ID of the folder to update
            title: New title (optional)
            parent_id: New parent folder ID (optional)
        """
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if parent_id is not None:
            updates.append("parent_id = ?")
            params.append(parent_id)

        if not updates:
            return

        # Add updated_time
        updates.append("updated_time = ?")
        params.append(str(int(time.time())))  # Convert timestamp to string

        # Add folder_id last for WHERE clause
        params.append(folder_id)

        query = f"UPDATE folders SET {', '.join(updates)} WHERE id = ?"

        cursor = self.db_connection.cursor()
        cursor.execute(query, params)
        self.db_connection.commit()

        self.refreshed.emit()

