from typing import Callable, Dict, List, Optional
from pydantic import BaseModel
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QTreeWidgetItem, QStyle, QTreeWidget
from widgets__kbd_widgets import KbdTreeWidget

from PySide6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QWidget,
    QMenu,
    QApplication,
    QInputDialog,
)
from note_model import NoteModel
from db_api import FolderTreeItem, ItemType
from widgets__stateful_tree import StatefulTree, TreeItemData
from utils__ngram_filter import text_matches_filter


class TreeWithFilter(QTreeWidget):
    """Base tree widget class with filtering functionality"""

    def filter_tree(self, text: str) -> None:
        """Filter the tree view based on search text using n-gram comparison"""

        def show_all_items(item: QTreeWidgetItem) -> None:
            """Recursively show all items in the tree"""
            item.setHidden(False)
            for i in range(item.childCount()):
                child = item.child(i)
                show_all_items(child)

        def filter_items(item: QTreeWidgetItem) -> bool:
            # Get if this item matches using n-gram comparison
            item_matches = text_matches_filter(text, item.text(0), n=2, match_all=True)

            # Check all children
            child_matches = False
            visible_children = 0
            for i in range(item.childCount()):
                child = item.child(i)
                if filter_items(child):
                    child_matches = True
                    visible_children += 1

            # For folders (items with children), hide if no visible children and no match
            if item.childCount() > 0:
                item.setHidden(not (item_matches or visible_children > 0))
            else:
                # For notes (leaf items), hide if no match
                item.setHidden(not item_matches)

            return item_matches or child_matches

        # If empty show all items recursively
        if not text:
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                show_all_items(item)
            return

        # Filter from top level
        for i in range(self.topLevelItemCount()):
            filter_items(self.topLevelItem(i))


class NoteTree(StatefulTree, TreeWithFilter, KbdTreeWidget):
    note_created = Signal(str)  # folder_id
    note_deleted = Signal(str)  # note_id

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events, emitting note_selected on Enter"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if item := self.get_current_item_data():
                self.note_selected.emit(item)
                return
        # Only handle navigation keys, let others propagate
        super().keyPressEvent(event)

    # This is used to select a note even when follow_mode is disabled, otherwise notes update when moving through the tree
    update_note_id = Signal(str, str)  # note_id, new_note_id
    note_selected = Signal(TreeItemData)  # The selected Item,
    duplicate_note = Signal(str)  # note_id
    folder_rename_requested = Signal(str, str)  # (folder_id, new_title)
    folder_moved = Signal(str, str)  # (folder_id, new_parent_id)
    folder_duplicated = Signal(str)  # folder_id
    folder_create = Signal(str, str)  # title, parent_id
    folder_deleted = Signal(str)  # folder_id
    note_moved = Signal(str, str)  # (note_id, new_parent_folder_id)
    status_bar_message = Signal(str)  # Signal to send messages to status bar
    # Create a signal for creating a new note

    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.note_model = note_model
        self._hover_item: QTreeWidgetItem | None = None
        self._dragged_item: QTreeWidgetItem | None = None
        self._cut_items: list[TreeItemData] = []
        self.setup_ui()
        menu = self.build_context_menu_actions(None)
        self.addActions(menu.actions())
        # Store the tree_data because it's expensive to compute
        self.tree_data: Dict[str, FolderTreeItem] | None = None

    def move_folder_to_root(self, item_data: TreeItemData | None) -> None:
        item_data = item_data or self.get_current_item_data()
        if not item_data:
            return
        match item_data.type:
            case ItemType.FOLDER:
                if widget := self.tree_items.get_item(item_data):
                    id = item_data.id
                    if widget.parent():
                        self.note_model.set_folder_to_root(id)
            case _:
                self.send_status_message("Can only move folders to root")

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double click to select a note"""
        if item := self.get_current_item_data():
            self.note_selected.emit(item)
        super().mouseDoubleClickEvent(event)

    def setup_ui(self) -> None:
        self.setAnimated(True)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Initialize drag and drop handler
        self.drag_drop_handler = DragDropHandler(self)

    def populate_tree(self, tree_data: Dict[str, FolderTreeItem] | None = None) -> None:
        """
        Populate the tree widget with folders and notes from the model.

        params:
            tree_data: A dictionary containing the tree structure
                       this is used to populate the tree widget more quickly,
                       useful if the tree structure is already available
                       (e.g. from a previous tab)
        """
        self.clear()

        # Get the tree structure from the model
        tree_data = tree_data or self.note_model.get_note_tree_structure()
        self.tree_data = tree_data

        # Create a dict to store folder items for quick lookup
        folder_items = {}

        def add_folder_to_tree(
            parent_widget: QTreeWidget | QTreeWidgetItem, folder_data: FolderTreeItem
        ) -> None:
            """Recursively add folders and their contents to the tree

            Args:
                parent_widget: The parent widget to add items to (either the main tree or a folder item)
                folder_data: The folder data structure containing folder info and child items
            """
            folder_item = self.create_tree_item(
                parent_widget,
                folder_data.folder.title,
                ItemType.FOLDER,
                folder_data.folder.id,
            )
            # Set folder icon
            folder_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            folder_item.setIcon(0, folder_icon)
            folder_items[folder_data.folder.id] = folder_item

            # Add child folders first to ensure they appear above notes
            for child_folder in folder_data.children:
                add_folder_to_tree(folder_item, child_folder)

            # Add notes after folders
            for note in folder_data.notes:
                note_item = self.create_tree_item(
                    folder_item, note.title, ItemType.NOTE, note.id
                )
                # Move note items to the bottom of their parent folder
                folder_item.removeChild(note_item)
                folder_item.addChild(note_item)

        # Add all root folders and their children recursively
        for folder_id, folder_data in tree_data.items():
            _ = folder_id
            if folder_data.type == "folder":
                add_folder_to_tree(self, folder_data)

        # Collapse all folders by default
        self.collapseAll()

    def delete_item(self, item_data: TreeItemData | None) -> None:
        """Delete a note or folder from the tree and database

        Args:
            item: The tree item to delete
        """
        item_data = item_data or self.get_current_item_data()
        if not item_data:
            return
        item_above = self.get_item_data_above_current()

        match item_data.type:
            case ItemType.NOTE:
                self.note_model.delete_note(item_data.id)
                self.note_deleted.emit(item_data.id)
                self.send_status_message(f"Deleted note: {item_data.title}")
            case ItemType.FOLDER:
                self.folder_deleted.emit(item_data.id)
                self.send_status_message(f"Deleted folder: {item_data.title}")
        # Select the item above the deleted item
        if item_above:
            self.set_current_item_by_data(item_above)

    def duplicate_item(self, item_data: TreeItemData | None) -> None:
        """Duplicate a note or folder and its contents

        Args:
            item: The tree item to duplicate
        """
        item_data = item_data or self.get_current_item_data()
        if not item_data:
            return
        match item_data.type:
            case ItemType.FOLDER:
                self.folder_duplicated.emit(item_data.id)
                self.send_status_message(f"Duplicated folder: {item_data.title}")
            case ItemType.NOTE:
                # TODO: Implement note duplication
                self.duplicate_note.emit(item_data.id)
                self.send_status_message(f"Duplicated note: {item_data.title}")

    def create_folder(self, item_data: TreeItemData | None) -> None:
        item_data = item_data or self.get_current_item_data()
        if not item_data:
            return
        match item_data.type:
            case ItemType.FOLDER:
                parent_id = item_data.id
            case ItemType.NOTE:
                parent_id = self.note_model.get_folder_id_from_note(item_data.id)

        title, ok = QInputDialog.getText(self, "Create Folder", "Enter folder name:")
        if ok and title:
            self.folder_create.emit(title, parent_id)
            self.send_status_message(f"Created folder: {title}")

    def copy_id(self, maybe_item_data: TreeItemData | None) -> None:
        item_data = maybe_item_data or self.get_current_item_data()
        if not item_data:
            return

        id = item_data.id
        title = item_data.title
        self.copy_to_clipboard(f"[{title}](:/{id})")

    def request_folder_rename(self, item_data: TreeItemData | None) -> None:
        """
        Handle folder rename request

        I haven't implemented note rename, save a note and change the heading
        """
        item_data = item_data or self.get_current_item_data()
        if not item_data:
            return
        if item_data.type == ItemType.FOLDER:
            new_title, ok = QInputDialog.getText(
                self, "Rename Folder", "Enter new folder name:", text=item_data.title
            )
            if ok and new_title:
                self.folder_rename_requested.emit(item_data.id, new_title)

    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to the system clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def update_id(self, item_data: TreeItemData | None) -> None:
        """Update the ID of an item"""
        item_data = item_data or self.get_current_item_data()
        if not item_data:
            return

        def get_new_id() -> tuple[str, bool]:
            new_id, ok = QInputDialog.getText(
                self,
                "Update ID",
                "Enter new ID (WARNING: Breaks Links in Joplin):",
                text=item_data.id,
            )
            # Right now the logic for links in the web preview and model.backlinks /forwardlinks relies on this assumption:
            new_id = new_id.strip().lower().replace(" ", "_")
            return new_id, ok

        match item_data.type:
            case ItemType.NOTE:
                new_id, ok = QInputDialog.getText(
                    self,
                    "Update ID",
                    "Enter new ID (WARNING: Breaks Links in Joplin):",
                    text=item_data.id,
                )
                if ok and new_id:
                    self.update_note_id.emit(item_data.id, new_id)
                    self.send_status_message(f"Updated ID for {item_data.title}")
            case ItemType.FOLDER:
                self.send_status_message("Update ID for folders not yet implemented")

    def create_note(self, item_data: TreeItemData | None) -> None:
        """Create a new note under the selected folder"""
        item_data = item_data or self.get_current_item_data()
        if not item_data:
            return
        match item_data.type:
            case ItemType.NOTE:
                folder_id = self.note_model.get_folder_id_from_note(item_data.id)
            case ItemType.FOLDER:
                folder_id = item_data.id
        self.note_created.emit(folder_id)
        full_title = self.note_model.get_folder_path(folder_id)
        self.send_status_message(f"Created new note in folder: {full_title}")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        self.drag_drop_handler.dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        self.drag_drop_handler.dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.drag_drop_handler.dropEvent(event)

    def send_status_message(self, message: str) -> None:
        """Send a message to the status bar"""
        self.status_bar_message.emit(message)

    def _is_child_of(
        self, child_item: QTreeWidgetItem, parent_item: QTreeWidgetItem
    ) -> bool:
        """Check if an item is a child of another item"""
        current = child_item
        while current.parent():
            current = current.parent()
            if current == parent_item:
                return True
        return False

    def cut_selected_items(self) -> None:
        """Store the currently selected items for cutting"""
        self._cut_items += self.get_selected_items_data()
        for item in self._cut_items:
            self.highlight_item(item)

    def clear_cut_items(self) -> None:
        """Clear the cut items selection"""
        if not self._cut_items:
            return

        # Make a copy of the list since we're modifying it
        items_to_clear = list(self._cut_items)
        self._cut_items.clear()

        for item in items_to_clear:
            try:
                if item:  # Check if item still exists
                    self.unhighlight_item(item)
            except RuntimeError:
                continue  # Skip if item was deleted

    # TODO this should call an operation in the model that bulkd moves items
    # otherwise each item triggers a refresh which is needlessly slow
    def paste_items(self, target_item_data: TreeItemData | None) -> None:
        """Paste cut items to the target folder"""
        target_item_data = target_item_data or self.get_current_item_data()
        if not target_item_data:
            return

        # Verify target is a folder
        if target_item_data.type != ItemType.FOLDER:
            self.send_status_message("Can only paste into folders")
            return

        # Move each cut item to the target folder
        for item_data in self._cut_items:
            if item_data.type == ItemType.FOLDER:
                self.folder_moved.emit(item_data.id, target_item_data.id)
            elif item_data.type == ItemType.NOTE:
                self.note_moved.emit(item_data.id, target_item_data.id)

        # Clear cut items after paste
        self.clear_cut_items()

    class MenuAction(BaseModel):
        """Model for context menu actions"""

        label: str
        handler: Callable[[], None]
        shortcut: Optional[str] = None
        condition: Optional[Callable[[TreeItemData], bool]] = None

    def get_context_menu_actions(self, position: QPoint | None) -> List[MenuAction]:
        """Get list of context menu actions based on item type"""
        # If the user right-clicked on an empty area
        # We can't determine the item type
        # and our methods will default to current_item_data
        # This requires re-thinking
        # To block context Menu, consider returning an empty list

        if position and (item := self.itemAt(position)):
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
        else:
            item_data = self.get_current_item_data()

        item_type: str | None = None
        item_id: str | None = None
        if item_data:
            item_type = item_data.type.name.lower().capitalize()
            item_id = item_data.id

        return [
            self.MenuAction(
                label=f"Copy {item_type} ID: {item_id}",
                handler=lambda: self.copy_id(item_data),
                shortcut="C",
            ),
            self.MenuAction(
                label=f"Change {item_type} ID",
                handler=lambda: self.update_id(item_data),
                shortcut=None,
            ),
            self.MenuAction(
                label="Create Note",
                handler=lambda: self.create_note(item_data),
                shortcut="N",
            ),
            self.MenuAction(
                label="Create Folder",
                handler=lambda: self.create_folder(item_data),
                shortcut="Ctrl+Alt+N",
            ),
            self.MenuAction(
                label=f"Duplicate {item_type}",
                handler=lambda: self.duplicate_item(item_data),
                shortcut="Print",
            ),
            self.MenuAction(
                label=f"Delete {item_type}",
                handler=lambda: self.delete_item(item_data),
                shortcut="Delete",
            ),
            self.MenuAction(
                label="Rename Folder",
                handler=lambda: self.request_folder_rename(item_data),
                shortcut="F2",
            ),
            self.MenuAction(
                label="Move to Root",
                handler=lambda: self.move_folder_to_root(item_data),
                shortcut="0",
            ),
            self.MenuAction(label="Cut", handler=self.cut_selected_items, shortcut="X"),
            self.MenuAction(
                label="Paste",
                handler=lambda: self.paste_items(item_data),
                shortcut="P",
                condition=lambda _: bool(self._cut_items),
            ),
            self.MenuAction(
                label="Clear Cut",
                handler=self.clear_cut_items,
                shortcut="`",
                condition=lambda _: bool(self._cut_items),
            ),
        ]

    def build_context_menu_actions(self, position: QPoint | None) -> QMenu:
        """
        Build Context Menu actions for the selected item or use the function default (current item usually)
        """

        menu = QMenu()
        actions = self.get_context_menu_actions(position)

        # Add actions with conditions
        for action in actions:
            q_action = QAction(action.label, self)
            q_action.triggered.connect(action.handler)
            if action.shortcut:
                q_action.setShortcut(action.shortcut)
            menu.addAction(q_action)

            # Add separator after ID copy
            if action.label.startswith("Copy"):
                menu.addSeparator()

        return menu

    def show_context_menu(self, position: QPoint) -> None:
        menu = self.build_context_menu_actions(position)
        menu.exec(self.viewport().mapToGlobal(position))


class DragDropHandler:
    """Handles drag and drop operations for tree widgets"""

    def __init__(self, tree_widget: NoteTree) -> None:
        self.tree_widget = tree_widget
        self._hover_item: QTreeWidgetItem | None = None
        self._dragged_item: QTreeWidgetItem | None = None

        # Configure tree widget for drag and drop
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setAcceptDrops(True)
        self.tree_widget.setDropIndicatorShown(True)
        self.tree_widget.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.tree_widget.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event"""
        self._dragged_item = self.tree_widget.currentItem()
        if self._dragged_item:
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move event with hover highlighting"""
        if not self._dragged_item:
            event.ignore()
            return

        # Get item under mouse
        item = self.tree_widget.itemAt(event.position().toPoint())

        # Only allow dropping on folders
        if item:
            item_data: TreeItemData = item.data(0, Qt.ItemDataRole.UserRole)
            match item_data.type:
                case ItemType.FOLDER:
                    pass  # Allow drop on folders
                case _:
                    event.ignore()
                    return

        # Update hover highlight
        if item != self._hover_item:
            if self._hover_item:
                self._hover_item.setBackground(0, self.tree_widget.palette().base())
            if item:
                item.setBackground(0, self.tree_widget.palette().highlight())
            self._hover_item = item

        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event to move folders"""
        if not self._dragged_item:
            event.ignore()
            return

        # Clear hover highlight
        if self._hover_item:
            self._hover_item.setBackground(0, self.tree_widget.palette().base())
            self._hover_item = None

        # Get the target item under the mouse
        target_item = self.tree_widget.itemAt(event.position().toPoint())
        if not target_item:
            event.ignore()
            return

        # Get item types and IDs
        dragged_data: TreeItemData = self._dragged_item.data(
            0, Qt.ItemDataRole.UserRole
        )
        target_data: TreeItemData = target_item.data(0, Qt.ItemDataRole.UserRole)

        # Handle invalid operations
        # Recursion
        if target_data.id == dragged_data.id:
            self.tree_widget.send_status_message("Cannot drop onto itself")
            event.ignore()
            return None
        # Invalid assignment
        if target_data.type != ItemType.FOLDER:
            match (dragged_data.type, target_data.type):
                case (ItemType.FOLDER, ItemType.NOTE):
                    self.tree_widget.send_status_message(
                        "Cannot drop folders onto notes"
                    )
                case (ItemType.NOTE, ItemType.NOTE):
                    self.tree_widget.send_status_message(
                        "Cannot drop notes onto other notes"
                    )
            event.ignore()
            return

        # Handle valid moves
        match dragged_data.type:
            case ItemType.FOLDER:
                self._move_folder(dragged_data.id, target_data.id)
                event.acceptProposedAction()
            case ItemType.NOTE:
                self._move_note(dragged_data.id, target_data.id)
                event.acceptProposedAction()
            case _:
                event.ignore()

        # Reset dragged item
        self._dragged_item = None

    def _move_folder(self, folder_id: str, new_parent_id: str) -> None:
        """Move a folder to a new parent folder"""
        self.tree_widget.folder_moved.emit(folder_id, new_parent_id)

    def _move_note(self, note_id: str, new_parent_folder_id: str) -> None:
        """Move a note to a new parent folder"""
        self.tree_widget.note_moved.emit(note_id, new_parent_folder_id)
