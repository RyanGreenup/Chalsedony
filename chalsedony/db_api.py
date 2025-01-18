from pydantic import BaseModel
from enum import Enum
from decimal import Decimal
from typing import NamedTuple


class Note(BaseModel):
    id: str
    parent_id: str = ""
    title: str = ""
    body: str = ""
    created_time: int | None = None
    updated_time: int | None = None
    is_conflict: int = 0
    latitude: Decimal = Decimal(0)
    longitude: Decimal = Decimal(0)
    altitude: Decimal = Decimal(0)
    author: str = ""
    source_url: str = ""
    is_todo: int = 0
    todo_due: int = 0
    todo_completed: int = 0
    source: str = ""
    source_application: str = ""
    application_data: str = ""
    order: Decimal = Decimal(0)
    user_created_time: int | None = None
    user_updated_time: int | None = None
    encryption_cipher_text: str = ""
    encryption_applied: int = 0
    markup_language: int = 1
    is_shared: int = 0
    share_id: str = ""
    conflict_original_id: str = ""
    master_key_id: str = ""
    user_data: str = ""
    deleted_time: int = 0


class Folder(BaseModel):
    id: str
    title: str = ""
    created_time: int
    updated_time: int
    user_created_time: int = 0
    user_updated_time: int = 0
    encryption_cipher_text: str = ""
    encryption_applied: int = 0
    parent_id: str = ""
    is_shared: int = 0
    share_id: str = ""
    master_key_id: str = ""
    icon: str = ""
    user_data: str = ""
    deleted_time: int = 0


class FolderTreeItem(BaseModel):
    type: str
    folder: Folder
    parent_id: str | None
    notes: list[Note]
    children: list["FolderTreeItem"] = []


class NoteSearchResult(NamedTuple):
    """Represents a search result containing note ID and title"""

    id: str
    title: str


class ItemType(Enum):
    """Enum representing types of items in the note tree"""

    NOTE = "note"
    FOLDER = "folder"


class IdTable(Enum):
    """Enum representing the table an ID belongs to"""

    NOTE = "note"
    FOLDER = "folder"
    RESOURCE = "resource"


class Resource(BaseModel):
    """Model representing a resource/asset in the database"""

    id: str
    title: str = ""
    mime: str
    # This is not used for compatability with the Joplin API
    filename: str = ""
    created_time: int
    updated_time: int
    user_created_time: int = 0
    user_updated_time: int = 0
    file_extension: str = ""
    encryption_cipher_text: str = ""
    encryption_applied: int = 0
    encryption_blob_encrypted: int = 0
    size: int = -1
    is_shared: int = 0
    share_id: str = ""
    master_key_id: str = ""
    user_data: str = ""
    blob_updated_time: int = 0
    ocr_text: str = ""
    ocr_details: str = ""
    ocr_status: int = 0
    ocr_error: str = ""
