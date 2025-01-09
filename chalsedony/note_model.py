import time
import os
from PySide6.QtCore import QObject, Signal
from utils__get_first_markdown_heading import get_markdown_heading
from sqlite3 import Connection
from pathlib import Path
from typing import Dict, List, Optional
from db_api import Note, Folder, FolderTreeItem, NoteSearchResult, IdTable


class NoteModel(QObject):
    refreshed = Signal()  # Notify view to refresh

    def __init__(self, db_connection: Connection, assets: Path) -> None:
        super().__init__()
        self.db_connection = db_connection
        self.asset_dir = assets

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

        # Don't refresh as this could be slow on mere content change that is
        # Already reflected in the view (user can refresh or save to trigger that)
        # self.refreshed.emit()

    def move_note(self, note_id: str, parent_id: str) -> None:
        """
        Move a note to a different Folder
        """
        self.update_note(note_id, parent_id=parent_id)
        # Don't refresh as this could be slow
        self.refreshed.emit()

    def set_folder_to_root(self, folder_id: str) -> None:
        """Move a folder to the root of the folder tree

        Args:
            folder_id: ID of the folder to move to root
        """
        self.update_folder(folder_id, parent_id="")

    @staticmethod
    def create_id() -> str:
        # return note_id = str(int(time.time() * 1000))  # Simple timestamp-based ID
        return "".join(
            f"{b:02x}"
            for b in bytes.fromhex(hex(int(time.time() * 1000000))[2:].zfill(16))
            + os.urandom(8)
        )

    def create_note(
        self, parent_folder_id: str, title: str | None = None, body: str = ""
    ) -> str:
        """Create a new note in the specified folder

        Args:
            parent_folder_id: ID of the parent folder
            title: Note title (default empty string)
            body: Note content (default empty string)

        Returns:
            The ID of the newly created note
        """
        # Generate a 32 character hex string ID
        note_id = self.create_id()
        created_time = int(time.time())

        if title is None:
            title = "Untitled"

        cursor = self.db_connection.cursor()
        cursor.execute(
            """
            INSERT INTO notes (
                id, title, body, created_time, updated_time,
                user_created_time, user_updated_time, is_todo, todo_completed,
                parent_id, latitude, longitude, altitude, source_url, todo_due
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                note_id,
                title,
                body,
                created_time,
                created_time,
                created_time,
                created_time,
                0,
                0,
                parent_folder_id,
                0.0,
                0.0,
                0.0,
                "",
                0,
            ),
        )
        self.db_connection.commit()
        self.refreshed.emit()
        return note_id

    def delete_note(self, note_id: str) -> None:
        """Delete a note from the database

        Args:
            note_id: ID of the note to delete
        """
        cursor = self.db_connection.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.db_connection.commit()
        self.refreshed.emit()

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

            set parent_id as an empty (`""`) string to set the parent to None
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

    def get_folder_path(self, folder_id: str) -> str:
        """Get the materialized path of a folder from root to the specified folder

        Args:
            folder_id: ID of the target folder

        Returns:
            List of Folder objects representing the path from root to target folder
        """
        path: List[Folder] = []
        current_id: str | None = folder_id

        while current_id:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT * FROM folders WHERE id = ?", (current_id,))
            row = cursor.fetchone()

            if not row:
                break

            # Convert tuple to dictionary using cursor description
            columns = [col[0] for col in cursor.description]
            folder = Folder(**dict(zip(columns, row)))
            path.insert(0, folder)  # Add to beginning to maintain root->child order

            current_id = folder.parent_id if folder.parent_id else None

        return "/".join([f.title for f in path])

    def get_folder_id_from_note(self, note_id: str) -> str:
        """Get the parent folder ID for a given note ID

        Args:
            note_id: The ID of the note to look up

        Returns:
            The parent folder ID if found, None otherwise
        """
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT parent_id FROM notes WHERE id = ?", (note_id,))
        result = cursor.fetchone()
        assert (
            result is not None
        ), "Notes at root level (without parent folder) are not supported"
        return str(result[0])

    def get_notes_by_parent_id(self, parent_id: str) -> List[Note]:
        """Get all notes that belong to a specific folder

        Args:
            parent_id: The ID of the parent folder

        Returns:
            List of Note objects belonging to the specified folder
        """
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM notes WHERE parent_id = ?", (parent_id,))
        return [
            Note(**dict(zip([col[0] for col in cursor.description], row)))
            for row in cursor.fetchall()
        ]

    def delete_notes(self, note_ids: List[str]) -> None:
        """Delete multiple notes in a single SQL query

        Args:
            note_ids: List of note IDs to delete
        """
        if not note_ids:
            return

        # Create a parameterized query with the right number of placeholders
        placeholders = ",".join("?" * len(note_ids))
        query = f"DELETE FROM notes WHERE id IN ({placeholders})"

        cursor = self.db_connection.cursor()
        cursor.execute(query, note_ids)
        self.db_connection.commit()
        self.refreshed.emit()

    def delete_folder_recursive(self, folder_id: str) -> None:
        """Delete a folder and all its child folders and notes recursively

        Args:
            folder_id: ID of the folder to delete
        """
        # Get all child folders
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT id FROM folders WHERE parent_id = ?", (folder_id,))
        child_folders = [row[0] for row in cursor.fetchall()]

        # Recursively delete child folders
        for child_id in child_folders:
            self.delete_folder_recursive(child_id)

        # Get all notes in this folder
        cursor.execute("SELECT id FROM notes WHERE parent_id = ?", (folder_id,))
        note_ids = [row[0] for row in cursor.fetchall()]

        # Delete all notes in this folder
        if note_ids:
            self.delete_notes(note_ids)

        # Finally delete the folder itself
        cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        self.db_connection.commit()
        self.refreshed.emit()

    def copy_folder_recursive(
        self, folder_id: str, new_parent_id: Optional[str] = None
    ) -> str:
        """Copy a folder and all its contents recursively

        Args:
            folder_id: ID of the folder to copy
            new_parent_id: ID of the parent folder for the copy (None for root)

        Returns:
            ID of the new folder
        """
        # Get the original folder
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Folder {folder_id} not found")

        # Convert tuple to dictionary using cursor description
        columns = [col[0] for col in cursor.description]
        original_folder = dict(zip(columns, row))

        # Create new folder with same title
        new_folder_id = self.create_id()
        cursor.execute(
            """
            INSERT INTO folders (id, title, created_time, updated_time, parent_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                new_folder_id,
                original_folder["title"] + " (Copy)",
                int(time.time()),
                int(time.time()),
                new_parent_id
                if new_parent_id is not None
                else original_folder["parent_id"],
            ),
        )

        # Copy all notes in this folder
        notes = self.get_notes_by_parent_id(folder_id)
        for note in notes:
            self.create_note(
                parent_folder_id=new_folder_id, title=note.title, body=note.body
            )

        # Copy all child folders recursively
        cursor.execute("SELECT id FROM folders WHERE parent_id = ?", (folder_id,))
        child_folders = [row[0] for row in cursor.fetchall()]
        for child_id in child_folders:
            self.copy_folder_recursive(child_id, new_folder_id)

        self.db_connection.commit()
        self.refreshed.emit()
        return new_folder_id

    def duplicate_note(self, note_id: str) -> str:
        """Duplicate an existing note with all its content

        Args:
            note_id: ID of the note to duplicate

        Returns:
            ID of the newly created note
        """
        # Get the original note
        original_note = self.find_note_by_id(note_id)
        if not original_note:
            raise ValueError(f"Note {note_id} not found")

        # Create new note with same content but "(Copy)" in title
        new_note_id = self.create_note(
            parent_folder_id=original_note.parent_id,
            title=f"{original_note.title} (Copy)",
            body=original_note.body,
        )

        self.refreshed.emit()
        return new_note_id

    def create_folder(self, title: str, parent_id: str = "") -> str:
        """Create a new folder

        Args:
            title: Title of the new folder
            parent_id: ID of the parent folder (empty string for root)

        Returns:
            ID of the newly created folder
        """
        folder_id = self.create_id()
        created_time = int(time.time())

        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO folders (id, title, created_time, updated_time, parent_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    folder_id,
                    title,
                    created_time,
                    created_time,
                    parent_id if parent_id is not None else "",
                ),
            )
            self.db_connection.commit()
            self.refreshed.emit()
        except Exception as e:
            print(e)
        return folder_id

    def upload_resource(
        self, file_path: Path, note_id: str | None = None, title: str | None = None
    ) -> str | None:
        """Upload a file as a resource attached to a note

        Args:
            file_path: Path to the file to upload
            note_id: ID of the note to attach the resource to
            title: Optional title for the resource (defaults to filename)

        Returns:
            ID of the newly created resource
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate resource ID
        resource_id = self.create_id()
        created_time = int(time.time())

        # Get file info
        file_size = file_path.stat().st_size
        file_ext = file_path.suffix.lower()[1:]  # Remove dot from extension
        mime_type = "application/octet-stream"  # Default MIME type

        # Try to get more specific MIME type
        try:
            import mimetypes

            mime_type = mimetypes.guess_type(str(file_path))[0] or mime_type
        except ImportError:
            print("Mimetypes module not found, using default MIME type")
            pass

        # Use filename as title if not provided
        if not title:
            title = file_path.name

        # Copy file to assets directory
        asset_path = self.asset_dir / f"{resource_id}.{file_ext}"
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(file_path.read_bytes())

        try:
            # Insert resource record
            cursor = self.db_connection.cursor()
            cursor.execute(
                """
                INSERT INTO resources (
                    id, title, mime, filename, created_time, updated_time,
                    file_extension, size, blob_updated_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resource_id,
                    title,
                    mime_type,
                    file_path.name,  # Original filename
                    created_time,
                    created_time,
                    file_ext,
                    file_size,
                    created_time,
                ),
            )

            if note_id is not None:
                posix_time = int(time.time())
                # Link resource to note
                # It's not clear what the is_associated field does, so we set it to 0
                # It is required though [fn_is_associated]
                cursor.execute(
                    """
                    INSERT INTO note_resources (note_id, resource_id, is_associated, last_seen_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    (note_id, resource_id, 0, posix_time),
                )
        except Exception as e:
            print(e)
            print("Model: Failed to upload resource")
            return None

        self.db_connection.commit()
        return resource_id

    def get_resource_title(self, resource_id: str) -> str | None:
        """Get the title of a resource by its ID

        Args:
            resource_id: ID of the resource to look up

        Returns:
            The resource title if found, None otherwise
        """
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT title FROM resources WHERE id = ?", (resource_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_resource_path(self, resource_id: str) -> Path | None:
        """Get the file path of a resource by its ID

        Args:
            resource_id: ID of the resource to look up

        Returns:
            The path to the resource file if found, None otherwise

        Notes:
            The filepath field does not appear to be used by Joplin
        """
        # Find the first matching file with this ID prefix
        for path in self.asset_dir.iterdir():
            if path.name.startswith(resource_id):
                return path
        return None

    def what_is_this(self, id: str) -> IdTable | None:
        """Determine the table a given ID belongs to, None if not found
        
        Args:
            id: The ID to look up
            
        Returns:
            IdTable enum indicating which table the ID belongs to, or None if not found
        """
        cursor = self.db_connection.cursor()
        
        # Check notes table
        cursor.execute("SELECT id FROM notes WHERE id = ?", (id,))
        if cursor.fetchone():
            return IdTable.NOTE
            
        # Check folders table
        cursor.execute("SELECT id FROM folders WHERE id = ?", (id,))
        if cursor.fetchone():
            return IdTable.FOLDER
            
        # Check resources table
        cursor.execute("SELECT id FROM resources WHERE id = ?", (id,))
        if cursor.fetchone():
            return IdTable.RESOURCE
            
        return None


# Footnotes
# [fn_is_associated]: https://discourse.joplinapp.org/t/is-associated-in-note-resource-0-at-what-time-orphaned-files-are-detectable/4443/3
