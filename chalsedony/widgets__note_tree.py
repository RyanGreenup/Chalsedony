from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QTreeWidgetItem, QStyle
from widgets__kbd_widgets import KbdTreeWidget

from PySide6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
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
    note_created = Signal(str)  # folder_id
    note_deleted = Signal(str)  # note_id
    folder_rename_requested = Signal(str, str)  # (folder_id, new_title)
    folder_moved = Signal(str, str)  # (folder_id, new_parent_id)
    folder_duplicated = Signal(str)  # folder_id
    note_moved = Signal(str, str)  # (note_id, new_parent_folder_id)
    status_bar_message = Signal(str)  # Signal to send messages to status bar
    # Create a signal for creating a new note

    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.note_model = note_model
        self._hover_item: QTreeWidgetItem | None = None
        self._dragged_item: QTreeWidgetItem | None = None
        self._cut_items: list[QTreeWidgetItem] = []
        self.setup_ui()
        self.create_keybinings()

    def create_keybinings(self) -> None:
        self.key_actions = {
            Qt.Key.Key_X: self.cut_selected_items,
            Qt.Key.Key_P: lambda: self.paste_items(self.currentItem()),
            Qt.Key.Key_Escape: self.clear_cut_items if self._cut_items else None,
        }

    def setup_ui(self) -> None:
        self.setAnimated(True)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Initialize drag and drop handler
        self.drag_drop_handler = DragDropHandler(self)

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

    def delete_note(self, item: QTreeWidgetItem) -> None:
        """Delete a note from the tree and database

        Args:
            item: The tree item representing the note to delete
        """
        item_data: TreeItemData = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data.type == ItemType.NOTE:
            self.note_model.delete_note(item_data.id)
            self.note_deleted.emit(item_data.id)
            self.send_status_message(f"Deleted note: {item_data.title}")

    # Create a context menu event for folders to emit the folder_duplicated signal AI!
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
        create_action.setShortcut("Ctrl+N")
        menu.addAction(create_action)

        # Add folder-specific actions
        if item_type_enum == ItemType.FOLDER:
            # Rename action
            rename_action = QAction("Rename Folder", self)
            rename_action.triggered.connect(lambda: self.request_folder_rename(item))
            rename_action.setShortcut("F2")
            menu.addAction(rename_action)

            # Move to root action
            if item.parent():  # Only show if folder has a parent
                move_to_root_action = QAction("Move to Root", self)
                move_to_root_action.triggered.connect(
                    lambda: self.note_model.set_folder_to_root(item_data.id)
                )
                menu.addAction(move_to_root_action)

            # Add Duplicate Folder action
            duplicate_action = QAction("Duplicate Folder", self)
            duplicate_action.triggered.connect(
                lambda: self.duplicate_folder(item)
            )
            menu.addAction(duplicate_action)

            # Delete folder
            duplicate_action = QAction("Duplicate Folder", self)
            duplicate_action.triggered.connect(
                lambda: self.duplicate_folder(item)
            )
            menu.addAction(duplicate_action)

        # Add Cut action
        cut_action = QAction("Cut", self)
        cut_action.triggered.connect(self.cut_selected_items)
        cut_action.setShortcut("Ctrl+X")
        menu.addAction(cut_action)

        # Add Paste action if we have cut items
        if self._cut_items:
            paste_action = QAction("Paste", self)
            paste_action.triggered.connect(lambda: self.paste_items(item))
            paste_action.setShortcut("Ctrl+V")
            menu.addAction(paste_action)

            # Add Clear Cut action
            clear_cut_action = QAction("Clear Cut", self)
            clear_cut_action.triggered.connect(self.clear_cut_items)
            clear_cut_action.setShortcut("Esc")
            menu.addAction(clear_cut_action)

        # Add Delete action for notes
        if item_type_enum == ItemType.NOTE:
            delete_action = QAction("Delete Note", self)
            delete_action.triggered.connect(lambda: self.delete_note(item))
            delete_action.setShortcut("Del")
            menu.addAction(delete_action)

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
        item_data: TreeItemData = clicked_item.data(0, Qt.ItemDataRole.UserRole)
        match item_data.type:
            case ItemType.NOTE:
                folder_id = self.note_model.get_folder_id_from_note(item_data.id)
            case ItemType.FOLDER:
                folder_id = item_data.id
        self.note_created.emit(folder_id)
        full_title = self.note_model.get_folder_path(folder_id)
        self.send_status_message(f"Created new note in folder: {full_title}")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard shortcuts for cut/paste operations"""
        if self.currentItem():
            key = Qt.Key(event.key())
            action = self.key_actions.get(key)
            if action:
                action()
                event.accept()
                return

        # Let parent class handle other keys
        super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        self.drag_drop_handler.dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        self.drag_drop_handler.dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.drag_drop_handler.dropEvent(event)

    def send_status_message(self, message: str) -> None:
        """Send a message to the status bar"""
        self.status_bar_message.emit(message)

    def duplicate_folder(self, item: QTreeWidgetItem) -> None:
        """Duplicate a folder and its contents"""
        item_data: TreeItemData = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data.type == ItemType.FOLDER:
            new_folder_id = self.note_model.copy_folder_recursive(item_data.id)
            self.folder_duplicated.emit(new_folder_id)
            self.send_status_message(f"Duplicated folder: {item_data.title}")

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
        self._cut_items = self.selectedItems()
        for item in self._cut_items:
            item.setBackground(0, self.palette().highlight())

    def clear_cut_items(self) -> None:
        """Clear the cut items selection"""
        try:
            for item in self._cut_items:
                item.setBackground(0, self.palette().base())
        except RuntimeError:
            pass  # Ignore errors when items are already removed
        self._cut_items.clear()

    def paste_items(self, target_item: QTreeWidgetItem) -> None:
        """Paste cut items to the target folder"""
        if not target_item:
            return

        # Verify target is a folder
        target_data: TreeItemData = target_item.data(0, Qt.ItemDataRole.UserRole)
        if target_data.type != ItemType.FOLDER:
            self.send_status_message("Can only paste into folders")
            return

        # Move each cut item to the target folder
        for item in self._cut_items:
            item_data: TreeItemData = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data.type == ItemType.FOLDER:
                self.folder_moved.emit(item_data.id, target_data.id)
            elif item_data.type == ItemType.NOTE:
                self.note_moved.emit(item_data.id, target_data.id)

        # Clear cut items after paste
        self.clear_cut_items()


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
