from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

class CommandPalette(QDialog):
    command_selected = Signal(QAction)
    
    def __init__(self, parent: QWidget, actions: dict[str, QAction]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setModal(True)
        
        # Store actions
        self.actions = actions
        
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
        
    def populate_commands(self) -> None:
        """Populate the list with all commands"""
        self.list.clear()
        for action_id, action in self.actions.items():
            if not action.text():
                continue
            text = f"{action.text().replace('&', '')} "
            if shortcut := action.shortcut().toString():
                text += f"({shortcut})"
            self.list.addItem(text)
            
    def filter_commands(self, text: str) -> None:
        """Filter commands based on search text"""
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item:
                item.setHidden(
                    text.lower() not in item.text().lower()
                )
                
    def on_command_selected(self, item: QListWidget.Item) -> None:
        """Handle command selection"""
        text = item.text().split(" (")[0]  # Remove shortcut from display text
        for action in self.actions.values():
            if action.text().replace("&", "") == text:
                action.trigger()
                self.close()
                break
