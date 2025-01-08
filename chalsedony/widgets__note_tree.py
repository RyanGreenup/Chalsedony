from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QTreeWidgetItem
from typing import Dict, List, cast, TypedDict
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



class TreeItems:
    """Wrapper class to store and access tree items with O(1) lookup"""

    def __init__(self) -> None:
        self.items: Dict[str, TreeWidgetItem] = {}

    @staticmethod
    def _make_id(item: TreeItemData) -> str:
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

class TreeState(TypedDict):
    """Type for tree widget state"""
    selected_items: List[TreeItemData]
    expanded_items: List[TreeItemData]


class StatefulTree(QTreeWidget):
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
    def create_tree_item_data(item: TreeWidgetItem) -> TreeItemData:
        return TreeItemData(type=item.get_type(), id=item.get_id())

    def get_selected_items_data(self) -> List[TreeItemData]:
        """Get TreeItemData for all selected items in the tree

        Returns:
            List of TreeItemData for each selected item
        """
        selected_items = self.selectedItems()
        return [self.create_tree_item_data(item) for item in selected_items]


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
        state = {'expanded_items': self.get_expanded_items_data(), 'selected_items': []}
        self.restore_state(state)


    def export_state(self) -> TreeState:
        """Export the current state of the tree

        Returns:
            Dictionary containing selected and expanded items
        """
        return {
            'selected_items': self.get_selected_items_data(),
            'expanded_items': self.get_expanded_items_data()
        }

    def restore_state(self, state: TreeState) -> None:
        """Restore a previously exported tree state

        Args:
            state: Dictionary containing selected and expanded items to restore
        """
        # First restore expanded state
        self.collapseAll()
        for item_data in state['expanded_items']:
            item = self.tree_items.get_item(item_data)
            item.setExpanded(True)

        # Then restore selection
        self.clearSelection()
        for item_data in state['selected_items']:
            item = self.tree_items.get_item(item_data)
            item.setSelected(True)


