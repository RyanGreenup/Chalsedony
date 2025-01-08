from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QListWidget, QTreeWidget, QWidget
from PySide6.QtCore import Qt


class KbdListWidget(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle custom key bindings for vim-like navigation"""
        current = self.currentRow()

        match event.key():
            case Qt.Key.Key_J if current < self.count() - 1:
                # Move down one item
                self.setCurrentRow(current + 1)
            case Qt.Key.Key_K if current > 0:
                # Move up one item
                self.setCurrentRow(current - 1)

            # NOTE: THese don't trigger the context menu in the correct location, reconsider these.
            case Qt.Key.Key_F10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Trigger context menu at current position
                self._trigger_context_menu()
            case Qt.Key.Key_Space:
                # Trigger context menu at current position
                self._trigger_context_menu()
            case _:
                # Default behavior for other keys
                super().keyPressEvent(event)

    def _trigger_context_menu(self) -> None:
        self.customContextMenuRequested.emit(self.visualItemRect(self.currentItem()))


class KbdTreeWidget(QTreeWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for custom keybindings"""
        current = self.currentItem()
        if not current:
            super().keyPressEvent(event)
            return

        match event.key():
            case Qt.Key.Key_J:
                # Move to next item
                if next_item := self.itemBelow(current):
                    self.setCurrentItem(next_item)
            case Qt.Key.Key_K:
                # Move to previous item
                if prev_item := self.itemAbove(current):
                    self.setCurrentItem(prev_item)
            case Qt.Key.Key_H if current.isExpanded():
                # Collapse current folder
                current.setExpanded(False)
            case Qt.Key.Key_L if not current.isExpanded():
                # Expand current folder
                current.setExpanded(True)
            case Qt.Key.Key_Space:
                # Toggle fold state
                current.setExpanded(not current.isExpanded())
            case _:
                super().keyPressEvent(event)
