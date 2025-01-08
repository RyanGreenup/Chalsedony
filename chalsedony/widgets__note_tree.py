from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QTreeWidgetItem
from typing import Dict, List, cast
from widgets__kbd_widgets import KbdTreeWidget
from typing import List, Optional, NamedTuple


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


class TreeItemData(NamedTuple):
    """Represents data stored in a tree widget item"""

    type: ItemType
    id: str


class TreeWidgetItem(QTreeWidgetItem):
    """Custom QTreeWidgetItem that properly types the UserRole data"""

    def data(self, column: int, role: int) -> TreeItemData:
        """Override data method to return properly typed TreeItemData"""
        return cast(TreeItemData, super().data(column, role))

    def setData(self, column: int, role: int, value: TreeItemData) -> None:
        super().setData(column, role, value)

    def get_id(self) -> str:
        """Get the ID of the item"""
        return self.data(0, Qt.ItemDataRole.UserRole).id

    def get_type(self) -> ItemType:
        """Get the type of the item"""
        return self.data(0, Qt.ItemDataRole.UserRole).type

    def get_tree_item_data(self) -> TreeItemData:
        """Get the TreeItemData for the item"""
        return self.data(0, Qt.ItemDataRole.UserRole)


class TreeItems:
    """Wrapper class to store and access tree items with O(1) lookup"""

    def __init__(self) -> None:
        self.items: Dict[str, TreeWidgetItem] = {}

    def _make_id(self, item: TreeItemData) -> str:
        """Create a unique ID for an item based on its type and text"""
        return f"{item.type}-{item.id}"

    def add_item(self, item: TreeWidgetItem) -> None:
        """Add an item to the dict

        Args:
            item: The tree widget item to store
        """
        tree_item_data = TreeItemData( type=item.get_type(), id=item.get_id())
        id = self._make_id(tree_item_data)
        self.items[id] = item

    def get_item(self, tree_item: TreeItemData) -> TreeWidgetItem:
        """Get an item from the dict

        Args:
            item_id: The ID of the item to retrieve

        Returns:
            The corresponding TreeWidgetItem
        """
        item_id = self._make_id(tree_item)
        return self.items[item_id]


class NoteTreeWidget(KbdTreeWidget):
    """
    A TreeWidget to display notes and folders in a tree structure.

    Ensures the type and ID of items are stored and retrieved correctly.


    Usage:
        Get an item's ID and type:
            item = tree_widget.currentItem()
            item_data: TreeItemData = item.data(0, Qt.ItemDataRole.UserRole)
            item_id = item_data.id
            item_type = item_data.type
        Select an item by ID:
            item = tree_widget.tree_items.get_item(item_id)
            tree_widget.setCurrentItem(item)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tree_items = TreeItems()

    def clear(self) -> None:
        super().clear()
        # Reset the stored hashmap
        self.tree_items = TreeItems()


    def _create_and_store_tree_item(
        self,
        parent: QTreeWidget | QTreeWidgetItem,
        title: str,
        item_type: ItemType,
        item_id: str,
    ) -> TreeWidgetItem:
        """Create an item for the tree with proper type safety and store it in tree_items

        Args:
            parent: The parent widget/item to add to
            title: The display text for the item
            item_type: The type of item (FOLDER or NOTE)
            item_id: The unique ID for the item

        Returns:
            The created TreeWidgetItem
        """
        item = TreeWidgetItem(parent)
        item.setText(0, title)
        item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            TreeItemData(type=item_type, id=item_id),
        )
        self.tree_items.add_item(item)
        return item

    @staticmethod
    def create_tree_item_data(item: QTreeWidgetItem | TreeWidgetItem) -> TreeItemData:
        assert isinstance(item, TreeWidgetItem), "NoteTreeWidget should only contain TreeWidgetItem"
        return TreeItemData(type=item.get_type(), id=item.get_id())

    def get_selected_items_data(self) -> List[TreeItemData]:
        """Get TreeItemData for all selected items in the tree
        
        Returns:
            List of TreeItemData for each selected item
        """
        selected_items = self.selectedItems()
        return [self.create_tree_item_data(item) for item in selected_items]

    def set_selected_items(self, items_data: List[TreeItemData]) -> None:
        """Set the selected items in the tree based on TreeItemData
        
        Args:
            items_data: List of TreeItemData for items to select
        """
        self.clearSelection()
        for item_data in items_data:
            item = self.tree_items.get_item(item_data)
            item.setSelected(True)

    def get_expanded_items_data(self) -> List[TreeItemData]:
        """Get TreeItemData for all expanded items in the tree
        
        Returns:
            List of TreeItemData for each expanded item
        """
        expanded_items = []
        
        def collect_expanded(item: QTreeWidgetItem | None = None):
            if item and item.isExpanded():
                expanded_items.append(self.create_tree_item_data(item))
                
            # Recursively check children
            for i in range(item.childCount() if item else self.topLevelItemCount()):
                child = item.child(i) if item else self.topLevelItem(i)
                collect_expanded(child)
        
        collect_expanded()
        return expanded_items

    def collapse_and_restore_expanded(self) -> None:
        """Collapses all items in the tree and then restores previously expanded items"""
        # Store currently expanded items before collapsing
        expanded_items_data = self.get_expanded_items_data()
        
        # Collapse all items
        self.collapseAll()
        
        # Re-expand the previously expanded items
        for item_data in expanded_items_data:
            item = self.tree_items.get_item(item_data)
            item.setExpanded(True)

    # Write a method to export the state of the tree as a typed dictionary and another metod to set the state from that dictionary AI!


class NoteTree(NoteTreeWidget):
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
            folder_item = self._create_and_store_tree_item(
                parent_widget,
                folder_data.folder.title,
                ItemType.FOLDER,
                folder_data.folder.id,
            )
            folder_items[folder_data.folder.id] = folder_item

            # Add notes for this folder
            for note in folder_data.notes:
                self._create_and_store_tree_item(
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
