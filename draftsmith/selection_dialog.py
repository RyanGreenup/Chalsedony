from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QWidget,
)
from PySide6.QtCore import Signal, Qt, QEvent, QObject
from PySide6.QtGui import QKeyEvent
from typing import cast


class SelectionDialog(QDialog):
    """Base class for selection dialogs with search functionality"""
    
    selection_made = Signal(object)  # Generic signal for selection

    def __init__(self, parent: QWidget, title: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        # Create layout
        layout = QVBoxLayout(self)

        # Create search box
        self.search = QLineEdit(self)
        self.search.installEventFilter(self)
        self.search.setPlaceholderText("Type to search...")
        self.search.textChanged.connect(self.filter_items)
        layout.addWidget(self.search)

        # Create list widget
        self.list = QListWidget(self)
        self.list.itemActivated.connect(self.on_item_selected)
        layout.addWidget(self.list)

        # Set size and focus
        self.resize(400, 300)
        self.search.setFocus()

        # Connect return/enter key
        self.search.returnPressed.connect(self.trigger_selected_item)

    def filter_items(self, text: str) -> None:
        """Filter items based on search text"""
        had_visible = False
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item:
                is_visible = text.lower() in item.text().lower()
                item.setHidden(not is_visible)
                if is_visible and not had_visible:
                    self.list.setCurrentItem(item)
                    had_visible = True

    def trigger_selected_item(self) -> None:
        """Trigger the currently selected item"""
        if current_item := self.list.currentItem():
            self.on_item_selected(current_item)

    def on_item_selected(self, item: QListWidgetItem) -> None:
        """Handle item selection - to be implemented by subclasses"""
        raise NotImplementedError

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Handle keyboard events in search box"""
        if obj is self.search and event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            key = key_event.key()

            # Check for Ctrl+N/P
            if key_event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                match key:
                    case Qt.Key.Key_N:
                        self._select_next_visible()
                        return True
                    case Qt.Key.Key_P:
                        self._select_previous_visible()
                        return True

            # Check for arrow keys
            match key:
                case Qt.Key.Key_Up:
                    self._select_previous_visible()
                    return True
                case Qt.Key.Key_Down:
                    self._select_next_visible()
                    return True

        return super().eventFilter(obj, event)

    def _select_previous_visible(self) -> None:
        """Select the previous visible item in the list"""
        current = self.list.currentRow()
        for i in range(current - 1, -1, -1):
            item = self.list.item(i)
            if item and not item.isHidden():
                self.list.setCurrentRow(i)
                return
        # Wrap around to bottom if at top
        for i in range(self.list.count() - 1, current, -1):
            item = self.list.item(i)
            if item and not item.isHidden():
                self.list.setCurrentRow(i)
                return

    def _select_next_visible(self) -> None:
        """Select the next visible item in the list"""
        current = self.list.currentRow()
        for i in range(current + 1, self.list.count()):
            item = self.list.item(i)
            if item and not item.isHidden():
                self.list.setCurrentRow(i)
                return
        # Wrap around to top if at bottom
        for i in range(0, current):
            item = self.list.item(i)
            if item and not item.isHidden():
                self.list.setCurrentRow(i)
                return
