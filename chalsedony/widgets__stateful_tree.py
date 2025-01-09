from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QTreeWidgetItem
from typing import Dict, List, cast, TypedDict
from typing import NamedTuple


from PySide6.QtWidgets import (
    QTreeWidget,
    QWidget,
    QApplication,
)
from db_api import ItemType


class TreeItemData(NamedTuple):
    """Represents data stored in a tree widget item"""

    type: ItemType
    id: str
    title: str


class DeferredSelectionEvent(QEvent):
    """Custom event for deferred selection restoration"""

    def __init__(
        self, item_data_list: List[TreeItemData], current_item: TreeItemData | None
    ) -> None:
        super().__init__(QEvent.Type.User)
        self.item_data_list = item_data_list
        self.current_item = current_item


class TreeWidgetItem(QTreeWidgetItem):
    """
    Custom QTreeWidgetItem that properly types the UserRole data

    Implementation Details:

    Even though the title is stored in the item text, we store it again in the
    UserRole data because the text is merely a C++ pointer which can be invalidated
    when the item is moved or deleted.

    This allows us to retrieve the title and other data using typical python
    memory behaviour without unexpected:

        RuntimeError: Internal C++ object (TreeWidgetItem)
    """

    def __init__(
        self,
        parent: QTreeWidget | QTreeWidgetItem,
        title: str,
        item_type: ItemType,
        item_id: str,
    ):
        super().__init__(parent)
        self.setText(0, title)
        # Store data directly in the Qt UserRole
        self.setData(
            0,
            Qt.ItemDataRole.UserRole,
            TreeItemData(type=item_type, id=item_id, title=title),
        )

    @property
    def item_data(self) -> TreeItemData:
        """Get the TreeItemData directly"""
        return cast(TreeItemData, self.data(0, Qt.ItemDataRole.UserRole))


class TreeItems:
    """Wrapper class to store and access tree items with O(1) lookup"""

    def __init__(self) -> None:
        self.items: Dict[str, TreeWidgetItem] = {}  # Use f"{type}:{id}" as key

    def add_item(self, item: TreeWidgetItem) -> None:
        """Add an item to the dict"""
        data = item.item_data
        self.items[f"{data.type}:{data.id}"] = item

    def get_item(self, item_data: TreeItemData) -> TreeWidgetItem:
        """Get an item from the dict"""
        return self.items[f"{item_data.type}:{item_data.id}"]


class TreeState(TypedDict):
    """Type for tree widget state"""

    selected_items: List[TreeItemData]
    expanded_items: List[TreeItemData]
    current_item: TreeItemData | None


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

    def highlight_item(self, item_data: TreeItemData) -> None:
        """Highlight an item in the tree using TreeItemData
        
        Args:
            item_data: The TreeItemData containing the item's type and ID
        """
        try:
            item = self.tree_items.get_item(item_data)
            item.setBackground(0, QApplication.palette().highlight())
            item.setForeground(0, QApplication.palette().highlightedText())
        except KeyError:
            # Item was deleted or doesn't exist, skip silently
            pass

    def unhighlight_item(self, item_data: TreeItemData) -> None:
        """Remove highlight from an item in the tree using TreeItemData
        
        Args:
            item_data: The TreeItemData containing the item's type and ID
        """
        try:
            item = self.tree_items.get_item(item_data)
            item.setBackground(0, QApplication.palette().base())
            item.setForeground(0, QApplication.palette().text())
        except KeyError:
            # Item was deleted or doesn't exist, skip silently
            pass

    # Create a method to get the selected items as a list of TreeItemData AI!

    def get_expanded_items_data(self) -> List[TreeItemData]:
        """Get TreeItemData for all expanded items in the tree

        Returns:
            List of TreeItemData for each expanded item
        """

        def collect_expanded(items: List[QTreeWidgetItem]) -> List[TreeItemData]:
            result = []
            for item in items:
                if item.isExpanded():
                    result.append(cast(TreeWidgetItem, item).item_data)
                result.extend(
                    collect_expanded([item.child(i) for i in range(item.childCount())])
                )
            return result

        return collect_expanded(
            [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        )

    def export_state(self) -> TreeState:
        """Export the current state of the tree"""
        current = self.currentItem()
        return {
            "selected_items": [
                cast(TreeWidgetItem, item).item_data for item in self.selectedItems()
            ],
            "expanded_items": self.get_expanded_items_data(),
            "current_item": cast(TreeWidgetItem, current).item_data
            if current
            else None,
        }

    def restore_state(self, state: TreeState) -> None:
        """Restore a previously exported tree state"""
        self.collapseAll()
        self.clearSelection()

        # Restore expanded state first
        for item_data in state["expanded_items"]:
            self.tree_items.get_item(item_data).setExpanded(True)

        # Create and post custom event for deferred selection
        # This is required for drag and drop to work correctly
        # Without it, items will be removed from the tree instead of selected
        event = DeferredSelectionEvent(state["selected_items"], state["current_item"])
        if app := QApplication.instance():
            app.postEvent(self, event)

    def set_current_item_by_data(self, item_data: TreeItemData) -> None:
        """Set the current item using TreeItemData

        Args:
            item_data: The TreeItemData containing the item's type and ID
        """
        try:
            item = self.tree_items.get_item(item_data)
            self.setCurrentItem(item)
        except KeyError:
            # Item was deleted or doesn't exist, skip silently
            pass

    def event(self, e: QEvent) -> bool:
        """Handle custom events"""
        event = e
        if isinstance(event, DeferredSelectionEvent):
            # Handle our deferred selection event
            for item_data in event.item_data_list:
                try:
                    item = self.tree_items.get_item(item_data)
                    item.setSelected(True)
                except KeyError:
                    # Item was deleted, skip it
                    continue
            if event.current_item:
                try:
                    self.setCurrentItem(self.tree_items.get_item(event.current_item))
                except KeyError:
                    # Current item was deleted, skip it
                    pass
            return True
        return super().event(event)



