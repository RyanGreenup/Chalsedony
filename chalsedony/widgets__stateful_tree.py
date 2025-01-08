from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem
from typing import Dict, List, cast, TypedDict
from typing import NamedTuple


from PySide6.QtWidgets import (
    QTreeWidget,
    QWidget,
)
from db_api import ItemType


class TreeItemData(NamedTuple):
    """Represents data stored in a tree widget item"""

    type: ItemType
    id: str


class TreeWidgetItem(QTreeWidgetItem):
    """Custom QTreeWidgetItem that properly types the UserRole data"""

    def __init__(
        self,
        parent: QTreeWidget | QTreeWidgetItem,
        title: str,
        item_type: ItemType,
        item_id: str,
    ):
        super().__init__(parent)
        self.setText(0, title)
        self.item_data = TreeItemData(type=item_type, id=item_id)

    def data(self, column: int, role: int) -> TreeItemData:
        """Override data method to return properly typed TreeItemData"""
        return cast(TreeItemData, super().data(column, role))

    def setData(self, column: int, role: int, value: TreeItemData) -> None:
        super().setData(column, role, value)

    @property
    def item_data(self) -> TreeItemData:
        """Get the TreeItemData directly"""
        return self.data(0, Qt.ItemDataRole.UserRole)

    @item_data.setter
    def item_data(self, value: TreeItemData) -> None:
        """Set the TreeItemData directly"""
        self.setData(0, Qt.ItemDataRole.UserRole, value)


class TreeItems:
    """Wrapper class to store and access tree items with O(1) lookup"""

    def __init__(self) -> None:
        self.items: Dict[tuple[ItemType, str], TreeWidgetItem] = {}

    def add_item(self, item: TreeWidgetItem) -> None:
        """Add an item to the dict"""
        data = item.item_data
        self.items[(data.type, data.id)] = item

    def get_item(self, item_data: TreeItemData) -> TreeWidgetItem:
        """Get an item from the dict"""
        return self.items[(item_data.type, item_data.id)]


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

    def create_tree_item(
        self,
        parent: QTreeWidget | QTreeWidgetItem,
        title: str,
        item_type: ItemType,
        item_id: str,
    ) -> TreeWidgetItem:
        """Create and store a tree item"""
        item = TreeWidgetItem(parent, title, item_type, item_id)
        self.tree_items.add_item(item)
        return item

    def get_expanded_items_data(self) -> List[TreeItemData]:
        """Get TreeItemData for all expanded items in the tree

        Returns:
            List of TreeItemData for each expanded item
        """
        expanded_items = []

        def collect_expanded(item: QTreeWidgetItem | None = None) -> None:
            if item and item.isExpanded():
                expanded_items.append(cast(TreeWidgetItem, item).item_data)

            items = (
                [item.child(i) for i in range(item.childCount())]
                if item
                else [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
            )
            for child in items:
                collect_expanded(child)

        collect_expanded()
        return expanded_items

    def export_state(self) -> TreeState:
        """Export the current state of the tree"""
        return {
            "selected_items": [
                cast(TreeWidgetItem, item).item_data for item in self.selectedItems()
            ],
            "expanded_items": self.get_expanded_items_data(),
        }

    def restore_state(self, state: TreeState) -> None:
        """Restore a previously exported tree state"""
        self.collapseAll()
        self.clearSelection()

        for item_data in state["expanded_items"]:
            self.tree_items.get_item(item_data).setExpanded(True)

        for item_data in state["selected_items"]:
            self.tree_items.get_item(item_data).setSelected(True)
