from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QTreeWidgetItem
from widgets__kbd_widgets import KbdTreeWidget


from PySide6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QTreeWidget,
    QWidget,
    QMenu,
    QApplication,
    QInputDialog,
)
from note_model import NoteModel
from db_api import FolderTreeItem, ItemType

from widgets__stateful_tree import StatefulTree, TreeItemData


class NoteTree(StatefulTree, KbdTreeWidget):
    note_created = Signal(int)
    folder_rename_requested = Signal(str, str)  # (folder_id, new_title)
    folder_moved = Signal(str, str)  # (folder_id, new_parent_id)
    note_moved = Signal(str, str)  # (note_id, new_parent_folder_id)
    status_bar_message = Signal(str)  # Signal to send messages to status bar

    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.note_model = note_model
        self._hover_item: QTreeWidgetItem | None = None
        self._dragged_item: QTreeWidgetItem | None = None
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setAnimated(True)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Enable drag and drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        # Initialize hover tracking
        self._hover_item = None
        self._dragged_item = None

    def populate_tree(self) -> None:
        """Populate the tree widget with folders and notes from the model."""
        self.clear()

        # Get the tree structure from the model
        tree_data = self.note_model.get_note_tree_structure()

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
            folder_item = self.create_and_store_tree_item(
                parent_widget,
                folder_data.folder.title,
                ItemType.FOLDER,
                folder_data.folder.id,
            )
            folder_items[folder_data.folder.id] = folder_item

            # Add notes for this folder
            for note in folder_data.notes:
                # NOTE must use this method to create items so they are stored and the tree state can be tracked.
                # This maintains a hashmap of items and is more performant.
                self.create_and_store_tree_item(
                    folder_item, note.title, ItemType.NOTE, note.id
                )

            # Recursively add child folders
            for child_folder in folder_data.children:
                add_folder_to_tree(folder_item, child_folder)

        # Add all root folders and their children recursively
        for folder_id, folder_data in tree_data.items():
            _ = folder_id
            # TODO can this use types in some way?
            if folder_data.type == "folder":
                add_folder_to_tree(self, folder_data)

        # Collapse all folders by default
        self.collapseAll()

    def show_context_menu(self, position: QPoint) -> None:
        """Show context menu with create action and ID display"""
        item = self.itemAt(position)
        if not item:
            return

        menu = QMenu()

        # Add ID display as clickable menu item that copies to clipboard
        item_data: TreeItemData = item.data(0, Qt.ItemDataRole.UserRole)
        item_type_enum = item_data.type
        id_action = QAction(
            f"Copy {item_type_enum.name.capitalize()} ID: {item_data.id}", self
        )
        id_action.triggered.connect(lambda: self.copy_to_clipboard(str(item_data.id)))
        menu.addAction(id_action)

        # Add separator
        menu.addSeparator()

        # Add Create Note action
        create_action = QAction("Create Note", self)
        create_action.triggered.connect(lambda: self.create_note(item))
        menu.addAction(create_action)

        # Add Rename action for folders
        if item_type_enum == ItemType.FOLDER:
            rename_action = QAction("Rename Folder", self)
            rename_action.triggered.connect(lambda: self.request_folder_rename(item))
            menu.addAction(rename_action)

        menu.exec(self.viewport().mapToGlobal(position))

    def request_folder_rename(self, item: QTreeWidgetItem) -> None:
        """Handle folder rename request"""
        item_data: TreeItemData = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data.type == ItemType.FOLDER:
            new_title, ok = QInputDialog.getText(
                self, "Rename Folder", "Enter new folder name:", text=item.text(0)
            )
            if ok and new_title:
                self.folder_rename_requested.emit(item_data.id, new_title)

    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to the system clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def create_note(self, clicked_item: QTreeWidgetItem) -> None:
        """Create a new note under the selected folder"""
        print("TODO implement this")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event"""
        self._dragged_item = self.currentItem()
        if self._dragged_item:
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move event with hover highlighting"""
        if not self._dragged_item:
            event.ignore()
            return

        # Get item under mouse
        item = self.itemAt(event.position().toPoint())

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
                self._hover_item.setBackground(0, self.palette().base())
            if item:
                item.setBackground(0, self.palette().highlight())
            self._hover_item = item

        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event to move folders"""
        if not self._dragged_item:
            event.ignore()
            return

        # Clear hover highlight
        if self._hover_item:
            self._hover_item.setBackground(0, self.palette().base())
            self._hover_item = None

        # Get the target item under the mouse
        target_item = self.itemAt(event.position().toPoint())
        if not target_item:
            event.ignore()
            return

        # Get item types and IDs
        dragged_data: TreeItemData = self._dragged_item.data(
            0, Qt.ItemDataRole.UserRole
        )
        target_data: TreeItemData = target_item.data(0, Qt.ItemDataRole.UserRole)

        # Handle invalid operations
        if target_data.type != ItemType.FOLDER:
            if (
                dragged_data.type == ItemType.FOLDER
                and target_data.type == ItemType.NOTE
            ):
                self.send_status_message("Cannot drop folders onto notes")
            elif (
                dragged_data.type == ItemType.NOTE and target_data.type == ItemType.NOTE
            ):
                self.send_status_message("Cannot drop notes onto other notes")
            event.ignore()
            return

        if dragged_data.type == ItemType.FOLDER:
            # Remove the dragged item from its current position
            parent = self._dragged_item.parent()
            if parent:
                parent.removeChild(self._dragged_item)
            else:
                self.takeTopLevelItem(self.indexOfTopLevelItem(self._dragged_item))

            # Add the dragged item to the target folder
            target_item.addChild(self._dragged_item)
            target_item.setExpanded(True)  # Expand to show the moved item

            # Emit signal to update model
            self.folder_moved.emit(dragged_data.id, target_data.id)
            event.acceptProposedAction()
        elif dragged_data.type == ItemType.NOTE:
            # Remove the dragged note from its current position
            parent = self._dragged_item.parent()
            if parent:
                parent.removeChild(self._dragged_item)
            else:
                self.takeTopLevelItem(self.indexOfTopLevelItem(self._dragged_item))

            # Add the note to the target folder
            target_item.addChild(self._dragged_item)
            target_item.setExpanded(True)

            # Emit signal to update model
            self.note_moved.emit(dragged_data.id, target_data.id)
            event.acceptProposedAction()
        else:
            event.ignore()

        # Reset dragged item
        self._dragged_item = None

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
