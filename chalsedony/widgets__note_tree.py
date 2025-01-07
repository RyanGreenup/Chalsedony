import sys
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QMenu, QApplication
from note_model import NoteModel
import yaml

class NoteTree(QTreeWidget):
    note_created = Signal(int)

    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.note_model = note_model
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setAnimated(True)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def populate_tree(self) -> None:
        """Populate the tree widget with folders and notes from the model"""
        self.clear()

        # Get the tree structure from the model
        tree_data = self.note_model.get_note_tree_structure()

        # Create a dict to store folder items for quick lookup
        folder_items = {}

        def add_folder_to_tree(parent_widget, folder_data):
            """Recursively add folders and their contents to the tree"""
            folder_item = QTreeWidgetItem(parent_widget)
            folder_item.setText(0, folder_data.folder.title)
            folder_item.setData(0, Qt.ItemDataRole.UserRole, ("folder", folder_data.folder.id))
            folder_items[folder_data.folder.id] = folder_item

            # Add notes for this folder
            for note in folder_data.notes:
                note_item = QTreeWidgetItem(folder_item)
                note_item.setText(0, note.title)
                note_item.setData(0, Qt.ItemDataRole.UserRole, ("note", note.id))

            # Recursively add child folders
            for child_folder in folder_data.children:
                add_folder_to_tree(folder_item, child_folder)

        # Add all root folders and their children recursively
        for folder_id, folder_data in tree_data.items():
            if folder_data.type == "folder":
                add_folder_to_tree(self, folder_data)

        # Expand all folders by default
        self.expandAll()

    def show_context_menu(self, position: QPoint) -> None:
        """Show context menu with create action and ID display"""
        item = self.itemAt(position)
        if not item:
            return

        menu = QMenu()
        
        # Add ID display as clickable menu item that copies to clipboard
        item_type, item_id = item.data(0, Qt.ItemDataRole.UserRole)
        id_action = QAction(f"Copy {item_type.capitalize()} ID: {item_id}", self)
        id_action.triggered.connect(lambda: self.copy_to_clipboard(str(item_id)))
        menu.addAction(id_action)
        
        # Add separator
        menu.addSeparator()
        
        # Add Create Note action
        create_action = QAction("Create Note", self)
        create_action.triggered.connect(lambda: self.create_note(item))
        menu.addAction(create_action)

        menu.exec(self.viewport().mapToGlobal(position))

    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to the system clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def create_note(self, clicked_item: QTreeWidgetItem) -> None:
        """Create a new note under the selected folder"""
        if clicked_item.data(0, Qt.ItemDataRole.UserRole)[0] == "folder":
            # Emit a signal to create a new note
            if parent_folder_id := clicked_item.data(0, Qt.ItemDataRole.UserRole)[1]:
                if isinstance(parent_folder_id, int):
                    self.note_created.emit(parent_folder_id)
            else:
                print("Parent folder ID is not an integer")
            # The Model will trigger the view to update by emitting a signal
        else:
            print("Cannot create a note under a note")
