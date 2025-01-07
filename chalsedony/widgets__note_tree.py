from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QMenu,
    QApplication,
    QInputDialog,
)
from note_model import NoteModel
from db_api import FolderTreeItem


class NoteTree(QTreeWidget):
    note_created = Signal(int)
    folder_rename_requested = Signal(str, str)  # (folder_id, new_title)
    folder_moved = Signal(str, str)  # (folder_id, new_parent_id)
    note_moved = Signal(str, str)  # (note_id, new_parent_folder_id)

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
        """Populate the tree widget with folders and notes from the model"""
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
            folder_item = QTreeWidgetItem(parent_widget)
            folder_item.setText(0, folder_data.folder.title)
            folder_item.setData(
                0, Qt.ItemDataRole.UserRole, ("folder", folder_data.folder.id)
            )
            folder_items[folder_data.folder.id] = folder_item

            # Add notes for this folder
            for note in folder_data.notes:
                note_item = QTreeWidgetItem(folder_item)
                note_item.setText(0, note.title)
                note_item.setData(0, Qt.ItemDataRole.UserRole, ("note", note.id))

            # Recursively add child folders
            for child_folder in folder_data.children:
                add_folder_to_tree(folder_item, child_folder)

        # Add all root folders and their children recursively
        for folder_id, folder_data in tree_data.items():
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
        item_type, item_id = item.data(0, Qt.ItemDataRole.UserRole)
        id_action = QAction(f"Copy {item_type.capitalize()} ID: {item_id}", self)
        id_action.triggered.connect(lambda: self.copy_to_clipboard(str(item_id)))
        menu.addAction(id_action)

        # Add separator
        menu.addSeparator()

        # Add Create Note action
        create_action = QAction("Create Note", self)
        create_action.triggered.connect(lambda: self.create_note(item))
        menu.addAction(create_action)

        # Add Rename action for folders
        if item_type == "folder":
            rename_action = QAction("Rename Folder", self)
            rename_action.triggered.connect(lambda: self.request_folder_rename(item))
            menu.addAction(rename_action)

        menu.exec(self.viewport().mapToGlobal(position))

    def request_folder_rename(self, item: QTreeWidgetItem) -> None:
        """Handle folder rename request"""
        item_type, folder_id = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type == "folder":
            new_title, ok = QInputDialog.getText(
                self, "Rename Folder", "Enter new folder name:", text=item.text(0)
            )
            if ok and new_title:
                self.folder_rename_requested.emit(folder_id, new_title)

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
            item_type, _ = item.data(0, Qt.ItemDataRole.UserRole)
            if item_type != "folder":
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
        dragged_type, dragged_id = self._dragged_item.data(0, Qt.ItemDataRole.UserRole)
        target_type, target_id = target_item.data(0, Qt.ItemDataRole.UserRole)

        # Handle both folder and note moves
        if target_type != "folder":
            event.ignore()
            return

        if dragged_type == "folder":
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
            self.folder_moved.emit(dragged_id, target_id)
            event.acceptProposedAction()
        else:
            event.ignore()

        # Reset dragged item
        self._dragged_item = None

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
