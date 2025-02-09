import time
import os
import sqlite3
from PySide6.QtCore import QObject, Signal
from .utils__get_first_markdown_heading import get_markdown_heading
from sqlite3 import Connection
from pathlib import Path
from enum import Enum
from typing import final
from .db_api import Note, Folder, FolderTreeItem, NoteSearchResult, IdTable
from datetime import date, timedelta

# TODO consider using pydantic to deal with Any values on Database.
# pyright: reportAny=false


class ResourceType(Enum):
    """Enum representing different types of resources that can be embedded in HTML"""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"  # For general documents like Word files
    ARCHIVE = "archive"
    CODE = "code"
    OTHER = "other"
    PDF = "pdf"  # Specifically for PDF files
    HTML = "html"  # For HTML files


class OrderField(Enum):
    """Enum representing different types of ordering for notes"""

    TITLE = "title"
    CREATED_TIME = "created_time"
    UPDATED_TIME = "updated_time"
    USER_ORDER = "order"
    USER_CREATED_TIME = "user_created_time"
    USER_UPDATED_TIME = "user_updated_time"


class OrderType(Enum):
    """Enum representing different types of ordering for notes"""

    ASC = "ASC"
    DESC = "DESC"


@final
class NoteModel(QObject):
    refreshed = Signal()  # Notify view to refresh

    def __init__(self, db_connection: Connection, assets: Path) -> None:
        super().__init__()
        self.db_connection = db_connection
        self.asset_dir = assets
        self._order_by = OrderField.USER_ORDER
        self.ensure_fts_table()
        self._order_type = OrderType.ASC
        self._tree_data: list[FolderTreeItem] | None = None

    @property
    def order_by(self) -> OrderField:
        return self._order_by

    @order_by.setter
    def order_by(self, value: OrderField) -> None:
        self._order_by = value
        self.refresh()

    @property
    def order_type(self) -> OrderType:
        return self._order_type

    @order_type.setter
    def order_type(self, value: OrderType) -> None:
        self._order_type = value
        self.refresh()

    @property
    def tree_data(self) -> list[FolderTreeItem]:
        """Get the tree data, refreshing if necessary"""
        if self._tree_data is None:
            self._tree_data = self.get_note_tree_structure()
        return self._tree_data

    def rebuild_tree_data(self) -> None:
        """Rebuild the tree data from the database"""
        self._tree_data = None
        _ = self.tree_data  # Trigger Invalidation

    def find_note_by_id(self, note_id: str) -> None | Note:
        """Find a note by its ID in the entire tree"""
        cursor = self.db_connection.cursor()
        _ = cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()

        if row:
            # Convert tuple to dictionary using cursor description
            columns = [col[0] for col in cursor.description]
            row_dict = dict(zip(columns, row))
            return Note(**row_dict)
        return None

    def get_all_notes(self) -> list[NoteSearchResult]:
        """Get all notes from all folders

        Returns:
            List of NoteSearchResult containing note IDs and titles
        """
        cursor = self.db_connection.cursor()
        _ = cursor.execute("SELECT id, title FROM notes ORDER BY updated_time ASC")
        return [NoteSearchResult(id=row[0], title=row[1]) for row in cursor.fetchall()]

    def get_note_order_value(self, note_id: str) -> int:
        """Get the order value for a note

        Args:
            note_id: ID of the note to look up

        Returns:
            The order value for the note
        """
        cursor = self.db_connection.cursor()
        _ = cursor.execute("SELECT `order` FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_note_meta_by_id(self, note_id: str) -> NoteSearchResult | None:
        """Get note metadata by ID

        Args:
            note_id: ID of the note to look up

        Returns:
            NoteSearchResult containing the note's ID and title
        """
        cursor = self.db_connection.cursor()
        _ = cursor.execute("SELECT id, title FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return NoteSearchResult(id=row[0], title=row[1])

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
            self.refresh()

    def get_note_tree_structure(self) -> list[FolderTreeItem]:
        """Get the folder/note tree structure from the database using a recursive CTE.

        Returns:
            A list of root FolderTreeItem objects containing:
            - type: "folder"
            - folder: Folder model instance
            - parent_id: parent folder ID or None
            - notes: list of Note model instances in this folder
            - children: list of child FolderTreeItems
        """
        cursor = self.db_connection.cursor()
        # Use lambda to create type-safe row factory
        # Ensure that we get dict-like rows
        cursor.row_factory = lambda cursor, row: sqlite3.Row(cursor, row)  # pyright: ignore [reportArgumentType]

        # Build the recursive CTE to get the folder hierarchy
        cte_query = """
        WITH RECURSIVE folder_hierarchy(id, title, parent_id, created_time, updated_time, level) AS (
            SELECT id, title, parent_id, created_time, updated_time, 0 as level
            FROM folders
            WHERE parent_id IS NULL OR parent_id = ''
            UNION ALL
            SELECT f.id, f.title, f.parent_id, f.created_time, f.updated_time, h.level + 1
            FROM folders f
            INNER JOIN folder_hierarchy h ON f.parent_id = h.id
        )
        SELECT *
        FROM folder_hierarchy
        ORDER BY level ASC, title COLLATE NOCASE ASC
        """

        cursor.execute(cte_query)
        folder_rows = cursor.fetchall()

        # Build a mapping of folder IDs to FolderTreeItem instances
        folders = {
            row["id"]: FolderTreeItem(
                type="folder",
                folder=Folder(**dict(row)),  # Convert Row to dict for constructor
                parent_id=row["parent_id"] or "",
                notes=[],
                children=[],
            )
            for row in folder_rows
        }

        # Build the hierarchy using the parent_id relationships
        root_folders = [
            folder_item
            for folder_item in folders.values()
            if not folder_item.parent_id or folder_item.parent_id not in folders
        ]

        # Add child folders to their parents
        for folder_item in folders.values():
            if folder_item.parent_id and folder_item.parent_id in folders:
                folders[folder_item.parent_id].children.append(folder_item)

        # Fetch notes and assign them to folders
        print(self.order_by.value)
        notes_query = f"""
        SELECT *
        FROM notes
        ORDER BY
            parent_id,
            "{self.order_by.value}" {self.order_type.value},
            title COLLATE NOCASE ASC,
            updated_time DESC,
            created_time DESC
        """

        cursor.execute(notes_query)
        notes_rows = cursor.fetchall()

        # Assign notes to their respective folders
        for row in notes_rows:
            note = Note(
                id=row["id"],
                title=row["title"],
                body=row["body"],
                parent_id=row["parent_id"],
                created_time=row["created_time"],
                updated_time=row["updated_time"],
                user_created_time=row["user_created_time"],
                user_updated_time=row["user_updated_time"],
                is_todo=row["is_todo"],
                todo_completed=row["todo_completed"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                altitude=row["altitude"],
                source_url=row["source_url"],
                todo_due=row["todo_due"],
            )
            folder_id = note.parent_id
            if folder_id in folders:
                folders[folder_id].notes.append(note)

        return root_folders

    def refresh(self) -> None:
        """Refresh the model"""
        self.rebuild_tree_data()
        self.refreshed.emit()

    class Stemmer(Enum):
        """Enum representing FTS5 tokenizer options"""

        PORTER = "porter ascii"
        TRIGRAM = "trigram"

    @classmethod
    def get_fts_table_name(cls, stemmer: Stemmer) -> str:
        """Get the FTS table name corresponding to the stemmer type"""
        return {
            cls.Stemmer.PORTER: "notes_fts5_porter",
            cls.Stemmer.TRIGRAM: "notes_fts5_trigram",
        }[stemmer]

    def ensure_fts_table(self, stemmer: Stemmer = Stemmer.PORTER) -> None:
        """Ensure the FTS5 virtual table exists and is populated"""
        cursor = self.db_connection.cursor()

        table_name = self.get_fts_table_name(stemmer)
        # Check if table exists
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        )
        if not cursor.fetchone():
            # Create FTS5 virtual table and triggers
            cursor.executescript(f"""
                CREATE VIRTUAL TABLE {table_name} USING fts5(
                    id,
                    title,
                    body,
                    content='notes',
                    content_rowid='rowid',
                    tokenize = '{stemmer.value}'
                );

                -- Populate the FTS table with existing data
                INSERT INTO {table_name}(rowid, title, body)
                SELECT rowid, title, body FROM notes;

                -- Triggers to keep FTS updated
                CREATE TRIGGER notes_ai AFTER INSERT ON notes
                BEGIN
                    INSERT INTO {table_name}(rowid, title, body)
                    VALUES (new.rowid, new.title, new.body);
                END;

                CREATE TRIGGER notes_ad AFTER DELETE ON notes
                BEGIN
                    INSERT INTO {table_name}({table_name}, rowid, title, body)
                    VALUES ('delete', old.rowid, old.title, old.body);
                END;

                CREATE TRIGGER notes_au AFTER UPDATE ON notes
                BEGIN
                    INSERT INTO {table_name}({table_name}, rowid, title, body)
                    VALUES ('delete', old.rowid, old.title, old.body);
                    INSERT INTO {table_name}(rowid, title, body)
                    VALUES (new.rowid, new.title, new.body);
                END;
            """)
            self.db_connection.commit()

    def search_notes(
        self, query: str, stemmer: Stemmer = Stemmer.PORTER
    ) -> list[NoteSearchResult]:
        """Perform full text search on notes

        Args:
            query: The search query string

        Returns:
            List of NoteSearchResult containing note IDs and titles
        """
        table_name = self.get_fts_table_name(stemmer)
        # https://sqlite.org/fts5.html#the_bm25_function
        # Joplin is still using fts4, but we want the bm25 so we make another table
        self.ensure_fts_table(stemmer)
        cursor = self.db_connection.cursor()
        _ = cursor.execute(
            f"""
            SELECT id, title
            FROM {table_name}
            WHERE {table_name} MATCH ?
            ORDER BY bm25({table_name}) DESC
        """,
            (query,),
        )

        return [NoteSearchResult(id=row[0], title=row[1]) for row in cursor.fetchall()]

    def get_note_from_search_result(self, result: NoteSearchResult) -> None | Note:
        """Get full note details from a search result

        Args:
            result: The NoteSearchResult to get full details for

        Returns:
            The full Note object if found, None otherwise
        """
        return self.find_note_by_id(result.id)

    def update_note_id(self, note_id: str, new_note_id: str) -> None:
        """Update a note's ID while maintaining all relationships

        Args:
            note_id: Current ID of the note
            new_note_id: New ID to assign to the note
        """
        cursor = self.db_connection.cursor()

        # Check if the new ID is already in use
        _ = cursor.execute("SELECT id FROM notes WHERE id = ?", (new_note_id,))
        if cursor.fetchone():
            raise ValueError(f"Note ID {new_note_id} is already in use")

        # Update the note ID in the notes table
        _ = cursor.execute(
            "UPDATE notes SET id = ? WHERE id = ?", (new_note_id, note_id)
        )

        # Update any note_resources relationships
        _ = cursor.execute(
            "UPDATE note_resources SET note_id = ? WHERE note_id = ?",
            (new_note_id, note_id),
        )

        def joplin_link(id: str) -> str:
            return f"](:/{id})"

        def wikilink(id: str) -> str:
            return f"[[{id}]]"

        # Update both Joplin-style and wiki-style links
        for link_fn in [joplin_link, wikilink]:
            old_pattern = link_fn(note_id)
            new_pattern = link_fn(new_note_id)
            _ = cursor.execute(
                "UPDATE notes SET body = REPLACE(body, ?, ?)",
                (old_pattern, new_pattern),
            )

        self.db_connection.commit()
        self.refresh()

    def update_note(
        self,
        note_id: str,
        *,
        title: None | str = None,
        body: None | str = None,
        parent_id: None | str = None,
    ) -> None:
        """Update specific fields of a note

        Args:
            note_id: ID of the note to update
            title: New title (optional)
            body: New body content (optional)
            parent_id: New parent folder ID (optional)
        """
        updates: list[str] = []
        params: list[str] = []

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
        _ = cursor.execute(query, params)
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
        self.refresh()

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
        _ = cursor.execute(
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
        self.refresh()
        return note_id

    def delete_note(self, note_id: str) -> None:
        """Delete a note from the database

        Args:
            note_id: ID of the note to delete
        """
        cursor = self.db_connection.cursor()
        _ = cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.db_connection.commit()
        self.refresh()

    def update_folder(
        self,
        folder_id: str,
        *,
        title: None | str = None,
        parent_id: None | str = None,
    ) -> None:
        """Update specific fields of a folder

        Args:
            folder_id: ID of the folder to update
            title: New title (optional)
            parent_id: New parent folder ID (optional)

            set parent_id as an empty (`""`) string to set the parent to None
        """
        updates: list[str] = []
        params: list[str] = []

        if folder_id == parent_id:
            raise ValueError("Cannot set parent folder to itself")

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
        _ = cursor.execute(query, params)
        self.db_connection.commit()

        self.refresh()

    def get_relative_path(self, start_folder_id: str, target_folder_id: str) -> list[str]:
        """
        Get the Relative path of a folder from root to the specified folder.

        This only looks down so the returned results will not have, e.g. "../"

        Args:
            start_folder_id: ID of the starting folder
            target_folder_id: ID of the target folder

        Returns:
            List of folder titles representing the path from start to target,
            or empty list if target is not a descendant of start
        """
        start_path = self.get_folder_path_components(start_folder_id)
        target_path = self.get_folder_path_components(target_folder_id)

        # Find the first divergent folder
        common_prefix_len = 0
        for s, t in zip(start_path, target_path):
            if s.id != t.id:
                break
            common_prefix_len += 1

        # If target is not a descendant of start, return absolute path
        if common_prefix_len < len(start_path):
            return [f.title for f in target_path]

        # Return the remaining path components after the common prefix
        return [f.title for f in target_path[common_prefix_len:]]

    def get_folder_path_components(self, folder_id: str) -> list[Folder]:
        """Get the materialized path of a folder from root to the specified folder

        Args:
            folder_id: ID of the target folder

        Returns:
            List of Folder objects representing the path from root to target folder

        Example Output:
            [Journals, January]
        """
        path: list[Folder] = []
        current_id: str | None = folder_id

        while current_id:
            cursor = self.db_connection.cursor()
            _ = cursor.execute("SELECT * FROM folders WHERE id = ?", (current_id,))
            row = cursor.fetchone()

            if not row:
                break

            # Convert tuple to dictionary using cursor description
            columns = [col[0] for col in cursor.description]
            folder = Folder(**dict(zip(columns, row)))
            path.insert(0, folder)  # Add to beginning to maintain root->child order

            current_id = folder.parent_id if folder.parent_id else None

        return path

    def get_folder_path(self, folder_id: str) -> str:
        """Get the materialized path of a folder from root to the specified folder

        Args:
            folder_id: ID of the target folder

        Returns:
            List of Folder objects representing the path from root to target folder

        Example Output:
            "Journals/January/"
        """
        folders = self.get_folder_path_components(folder_id)
        return "/".join([f.title for f in folders])

    def get_folder_id_from_note(self, note_id: str) -> str:
        """Get the parent folder ID for a given note ID

        Args:
            note_id: The ID of the note to look up

        Returns:
            The parent folder ID if found, None otherwise
        """
        cursor = self.db_connection.cursor()
        _ = cursor.execute("SELECT parent_id FROM notes WHERE id = ?", (note_id,))
        result = cursor.fetchone()
        assert (
            result is not None
        ), "Notes at root level (without parent folder) are not supported"
        return str(result[0])

    def get_notes_by_parent_id(self, parent_id: str) -> list[Note]:
        """Get all notes that belong to a specific folder

        Args:
            parent_id: The ID of the parent folder

        Returns:
            List of Note objects belonging to the specified folder
        """
        cursor = self.db_connection.cursor()
        _ = cursor.execute("SELECT * FROM notes WHERE parent_id = ?", (parent_id,))
        return [
            Note(**dict(zip([col[0] for col in cursor.description], row)))
            for row in cursor.fetchall()
        ]

    def delete_notes(self, note_ids: list[str]) -> None:
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
        _ = cursor.execute(query, note_ids)
        self.db_connection.commit()
        self.refresh()

    def delete_folder_recursive(self, folder_id: str) -> None:
        """Delete a folder and all its child folders and notes recursively

        Args:
            folder_id: ID of the folder to delete
        """
        # Get all child folders
        cursor = self.db_connection.cursor()
        _ = cursor.execute("SELECT id FROM folders WHERE parent_id = ?", (folder_id,))
        child_folders = [row[0] for row in cursor.fetchall()]

        # Recursively delete child folders
        for child_id in child_folders:
            self.delete_folder_recursive(child_id)

        # Get all notes in this folder
        _ = cursor.execute("SELECT id FROM notes WHERE parent_id = ?", (folder_id,))
        note_ids = [row[0] for row in cursor.fetchall()]

        # Delete all notes in this folder
        if note_ids:
            self.delete_notes(note_ids)

        # Finally delete the folder itself
        _ = cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        self.db_connection.commit()
        self.refresh()

    def copy_folder_recursive(
        self, folder_id: str, new_parent_id: None | str = None
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
        _ = cursor.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Folder {folder_id} not found")

        # Convert tuple to dictionary using cursor description
        columns = [col[0] for col in cursor.description]
        original_folder = dict(zip(columns, row))

        # Create new folder with same title
        new_folder_id = self.create_id()
        _ = cursor.execute(
            """
            INSERT INTO folders (id, title, created_time, updated_time, parent_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                new_folder_id,
                original_folder["title"] + " (Copy)",
                int(time.time()),
                int(time.time()),
                (
                    new_parent_id
                    if new_parent_id is not None
                    else original_folder["parent_id"]
                ),
            ),
        )

        # Copy all notes in this folder
        notes = self.get_notes_by_parent_id(folder_id)
        for note in notes:
            _ = self.create_note(
                parent_folder_id=new_folder_id, title=note.title, body=note.body
            )

        # Copy all child folders recursively
        _ = cursor.execute("SELECT id FROM folders WHERE parent_id = ?", (folder_id,))
        child_folders = [row[0] for row in cursor.fetchall()]
        for child_id in child_folders:
            _ = self.copy_folder_recursive(child_id, new_folder_id)

        self.db_connection.commit()
        self.refresh()
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

        self.refresh()
        return new_note_id

    def create_folder(self, title: str, parent_id: str | None = "") -> str:
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
            _ = cursor.execute(
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
            self.refresh()
        except Exception as e:
            print(e)
        return folder_id

    def upload_resource(
        self, file_path: Path, note_id: str | None = None, title: str | None = None
    ) -> str:
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
        _ = asset_path.write_bytes(file_path.read_bytes())

        try:
            # Insert resource record
            cursor = self.db_connection.cursor()
            _ = cursor.execute(
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
                _ = cursor.execute(
                    """
                    INSERT INTO note_resources (note_id, resource_id, is_associated, last_seen_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    (note_id, resource_id, 0, posix_time),
                )
        except Exception as e:
            print(e)
            print("Model: Failed to upload resource")

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
        _ = cursor.execute("SELECT title FROM resources WHERE id = ?", (resource_id,))
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
        _ = cursor.execute("SELECT id FROM notes WHERE id = ?", (id,))
        if cursor.fetchone():
            return IdTable.NOTE

        # Check folders table
        _ = cursor.execute("SELECT id FROM folders WHERE id = ?", (id,))
        if cursor.fetchone():
            return IdTable.FOLDER

        # Check resources table
        _ = cursor.execute("SELECT id FROM resources WHERE id = ?", (id,))
        if cursor.fetchone():
            return IdTable.RESOURCE

        return None

    def get_resource_mime_type(
        self, resource_id: str
    ) -> tuple[str | None, ResourceType]:
        """Get the MIME type and resource type by its ID

        Args:
            resource_id: ID of the resource to look up

        Returns:
            A tuple containing:
            - The MIME type string if found, None otherwise
            - The ResourceType enum indicating the type of resource
        """
        import mimetypes

        path = self.get_resource_path(resource_id)
        if not path:
            return None, ResourceType.OTHER

        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "application/octet-stream"

        # Determine resource type based on MIME type
        match mime_type.split("/")[0], mime_type:
            case ("image", _):
                return mime_type, ResourceType.IMAGE
            case (_, "text/html"):
                return mime_type, ResourceType.HTML
            case ("video", _):
                return mime_type, ResourceType.VIDEO
            case ("audio", _):
                return mime_type, ResourceType.AUDIO
            case (_, "application/pdf"):
                return mime_type, ResourceType.PDF
            case (
                _,
                "application/msword"
                | "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ):
                return mime_type, ResourceType.DOCUMENT
            case (
                _,
                "application/zip"
                | "application/x-tar"
                | "application/x-rar-compressed",
            ):
                return mime_type, ResourceType.ARCHIVE
            case ("text", _) | (_, "application/json" | "application/javascript"):
                return mime_type, ResourceType.CODE
            case _:
                return mime_type, ResourceType.OTHER

    def get_journal_page_for_today(self, offset: int = 0) -> NoteSearchResult | None:
        """Get a journal page note, identified by title matching a specific date

        Args:
            offset: Number of days offset from today (e.g. -1 for yesterday, 1 for tomorrow)

        Returns:
            NoteSearchResult containing the matching note's ID and title
        """
        target_date = date.today() + timedelta(days=offset)
        title = target_date.strftime("%Y-%m-%d")
        cursor = self.db_connection.cursor()
        _ = cursor.execute(
            "SELECT id, title FROM notes WHERE title = ? ORDER BY updated_time DESC LIMIT 1",
            (title,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return NoteSearchResult(id=row[0], title=row[1])

    def get_note_by_title(self, title: str) -> NoteSearchResult | None:
        """Get a note by its title, choosing the most recently updated if multiple exist

        Args:
            title: The title to search for

        Returns:
            NoteSearchResult containing the matching note's ID and title, or None if not found
        """
        cursor = self.db_connection.cursor()
        _ = cursor.execute(
            "SELECT id, title FROM notes WHERE title = ? ORDER BY updated_time DESC LIMIT 1",
            (title,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return NoteSearchResult(id=row[0], title=row[1])

    @staticmethod
    def format_as_markdown_link(note: NoteSearchResult) -> str:
        """Format a note as a markdown link

        Args:
            note: The note to format

        Returns:
            A markdown link to the note
        """
        return f"[{note.title}](:/{note.id})"

    def get_backlinks(self, note_id: str) -> list[NoteSearchResult]:
        """Get all notes that link to the specified note

        Args:
            note_id: The ID of the target note

        Returns:
            List of NoteSearchResult containing note IDs and titles

        Implememenation Notes:
            - This looks for the id, not for a markdown link or a prefix of `:/`, this may be changed in the future
              for now this simplicity is perferable
        """
        cursor = self.db_connection.cursor()
        _ = cursor.execute(
            """
            SELECT id, title
            FROM notes
            WHERE body LIKE '%' || ? || '%';
            """,
            (note_id,),
        )
        return [NoteSearchResult(id=row[0], title=row[1]) for row in cursor.fetchall()]

    def get_forwardlinks(self, note_id: str) -> list[NoteSearchResult]:
        """Get all notes that this note links to

        A forward link is represented by text in the body field of the form ":/{id}"

        Args:
            note_id: The ID of the source note

        Returns:
            List of NoteSearchResult containing note IDs and titles of linked notes
        """
        # First get the note body
        cursor = self.db_connection.cursor()
        _ = cursor.execute("SELECT body FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return []

        body = row[0]

        # Find all instances of ":/ID" pattern
        import re

        linked_ids = re.findall(r":/([a-zA-Z0-9]+)", body)

        if not linked_ids:
            return []

        # Get titles for all valid note IDs found
        placeholders = ",".join("?" * len(linked_ids))
        _ = cursor.execute(
            f"SELECT id, title FROM notes WHERE id IN ({placeholders})", linked_ids
        )

        return [NoteSearchResult(id=row[0], title=row[1]) for row in cursor.fetchall()]

    def fix_things(self) -> None:
        """Fix things in the database

        This is a utility method to fix things in the database. This can be used to
        perform cleanup operations or fix inconsistencies in the database.
        """
        # Example: Delete all notes with empty titles
        cursor = self.db_connection.cursor()
        _ = cursor.execute("UPDATE folders SET parent_id = '' where id == parent_id;")
        self.db_connection.commit()

    def swap_note_order(self, note_id1: str, note_id2: str) -> None:
        """Swap the order field values between two notes

        Args:
            note_id1: ID of the first note
            note_id2: ID of the second note
        """
        cursor = self.db_connection.cursor()

        # Get current order values
        _ = cursor.execute(
            "SELECT id, `order` FROM notes WHERE id IN (?, ?)", (note_id1, note_id2)
        )
        rows = cursor.fetchall()

        if len(rows) != 2:
            raise ValueError("One or both note IDs not found")

        # Create mapping of id to order
        orders = {row[0]: row[1] for row in rows}

        # If they're equal, just set one to the max, this could be improved
        # But simple is better than complex
        if orders[note_id1] == orders[note_id2]:
            orders[note_id2] = (
                self.get_max_order_value(self.get_folder_id_from_note(note_id2)) + 1
            )

        # Swap the values
        _ = cursor.execute(
            "UPDATE notes SET `order` = ? WHERE id = ?", (orders[note_id2], note_id1)
        )
        _ = cursor.execute(
            "UPDATE notes SET `order` = ? WHERE id = ?", (orders[note_id1], note_id2)
        )

        self.db_connection.commit()
        self.refresh()

    def get_max_order_value(self, parent_id: str) -> int:
        """Get the maximum order value for notes in a folder

        Args:
            parent_id: ID of the parent folder

        Returns:
            The maximum order value in the folder
        """
        cursor = self.db_connection.cursor()
        _ = cursor.execute(
            "SELECT MAX(`order`) FROM notes WHERE parent_id = ?", (parent_id,)
        )
        return cursor.fetchone()[0] or 0


# Footnotes
# [fn_is_associated]: https://discourse.joplinapp.org/t/is-associated-in-note-resource-0-at-what-time-orphaned-files-are-detectable/4443/3
