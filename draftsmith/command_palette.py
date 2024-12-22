from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QWidget,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from typing import Dict


class CommandPalette(QDialog):
    command_selected = Signal(QAction)

    def __init__(self, parent: QWidget, actions: dict[str, QAction]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setModal(True)

        # Store actions
        self._actions: Dict[str, QAction] = actions

        # Create layout
        layout = QVBoxLayout(self)

        # Create search box
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Type to search commands...")
        self.search.textChanged.connect(self.filter_commands)
        layout.addWidget(self.search)

        # Create list widget
        self.list = QListWidget(self)
        self.list.itemActivated.connect(self.on_command_selected)
        layout.addWidget(self.list)

        # Populate initial list
        self.populate_commands()

        # Set size
        self.resize(400, 300)

        # Set focus to search box
        self.search.setFocus()
        
        # Connect return/enter key in search to select first visible item
        self.search.returnPressed.connect(self.select_first_visible)

    def populate_commands(self) -> None:
        """Populate the list with all commands"""
        self.list.clear()
        for action_id, action in self._actions.items():
            if not action.text():
                continue
            text = f"{action.text().replace('&', '')} "
            if shortcut := action.shortcut().toString():
                text += f"({shortcut})"
            self.list.addItem(text)
        
        # Select first item
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def filter_commands(self, text: str) -> None:
        """Filter commands based on search text"""
        had_visible = False
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item:
                is_visible = text.lower() in item.text().lower()
                item.setHidden(not is_visible)
                if is_visible and not had_visible:
                    self.list.setCurrentItem(item)
                    had_visible = True

    def select_first_visible(self) -> None:
        """Select the first visible item in the list"""
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item and not item.isHidden():
                self.on_command_selected(item)
                break

    def on_command_selected(self, item: QListWidgetItem) -> None:
        """Handle command selection"""
        text = item.text().split(" (")[0]  # Remove shortcut from display text
        for action in self._actions.values():
            if action.text().replace("&", "") == text:
                action.trigger()
                self.close()
                break
