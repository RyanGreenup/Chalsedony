from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QListWidget, QWidget
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
