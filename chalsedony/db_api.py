from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional


# AI THe Note model is defined here
class Note(BaseModel):
    id: str
    parent_id: str = ""
    title: str = ""
    body: str = ""
    created_time: Optional[int] = None
    updated_time: Optional[int] = None
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
    user_created_time: Optional[int] = None
    user_updated_time: Optional[int] = None
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
    parent_id: Optional[str]
    notes: List[Note]
    children: List["FolderTreeItem"] = []


# AI: The notes table looks like this:
# 
# ```sql
# CREATE TABLE `notes`(`id` TEXT PRIMARY KEY,`parent_id` TEXT NOT NULL DEFAULT "",`title` TEXT NOT NULL DEFAULT "",`body` TEXT NOT NULL DEFAULT "",`created_time` INT NOT NULL,`updated_time` INT NOT NULL,`is_conflict` INT NOT NULL DEFAULT 0,`latitude` NUMERIC NOT NULL DEFAULT 0,`longitude` NUMERIC NOT NULL DEFAULT 0,`altitude` NUMERIC NOT NULL DEFAULT 0,`author` TEXT NOT NULL DEFAULT "",`source_url` TEXT NOT NULL DEFAULT "",`is_todo` INT NOT NULL DEFAULT 0,`todo_due` INT NOT NULL DEFAULT 0,`todo_completed` INT NOT NULL DEFAULT 0,`source` TEXT NOT NULL DEFAULT "",`source_application` TEXT NOT NULL DEFAULT "",`application_data` TEXT NOT NULL DEFAULT "",`order` NUMERIC NOT NULL DEFAULT 0,`user_created_time` INT NOT NULL DEFAULT 0,`user_updated_time` INT NOT NULL DEFAULT 0,`encryption_cipher_text` TEXT NOT NULL DEFAULT "",`encryption_applied` INT NOT NULL DEFAULT 0,`markup_language` INT NOT NULL DEFAULT 1,`is_shared` INT NOT NULL DEFAULT 0, share_id TEXT NOT NULL DEFAULT "", conflict_original_id TEXT NOT NULL DEFAULT "", master_key_id TEXT NOT NULL DEFAULT "", `user_data` TEXT NOT NULL DEFAULT "", `deleted_time` INT NOT NULL DEFAULT 0);
# ```
