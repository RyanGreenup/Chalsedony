from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from widgets__stateful_tree import TreeItemData, ItemType


class DragDropHandler:
    """Handles drag and drop operations for tree widgets"""
    
    def __init__(self, tree_widget: QTreeWidget) -> None:
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
                    self.tree_widget.send_status_message("Cannot drop folders onto notes")
                case (ItemType.NOTE, ItemType.NOTE):
                    self.tree_widget.send_status_message("Cannot drop notes onto other notes")
            event.ignore()
            return

        # Handle valid moves
        match dragged_data.type:
            case ItemType.FOLDER:
                self.tree_widget.folder_moved.emit(dragged_data.id, target_data.id)
                event.acceptProposedAction()
            case ItemType.NOTE:
                self.tree_widget.note_moved.emit(dragged_data.id, target_data.id)
                event.acceptProposedAction()
            case _:
                event.ignore()

        # Reset dragged item
        self._dragged_item = None
