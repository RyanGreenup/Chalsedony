from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QMenu
from note_model import NoteModel


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
        # AI: The get_note_tree_structure() is used here to get the tree data from the model
        tree_data = self.note_model.get_note_tree_structure()
        
        # Create a dict to store folder items for quick lookup
        folder_items = {}
        
        # First pass: Create all folder items
        for folder_id, folder_data in tree_data.items():
            if folder_data['type'] == 'folder':
                folder_item = QTreeWidgetItem(self)
                folder_item.setText(0, folder_data['title'])
                folder_item.setData(0, Qt.ItemDataRole.UserRole, ('folder', folder_id))
                folder_items[folder_id] = folder_item
                
                # If it has a parent, add it under the parent
                if folder_data['parent_id'] and folder_data['parent_id'] in folder_items:
                    folder_items[folder_data['parent_id']].addChild(folder_item)
        
        # Second pass: Add notes under their folders
        for folder_id, folder_data in tree_data.items():
            if folder_data['type'] == 'folder':
                for note in folder_data['notes']:
                    note_item = QTreeWidgetItem(folder_items[folder_id])
                    note_item.setText(0, note['title'])
                    note_item.setData(0, Qt.ItemDataRole.UserRole, ('note', note['id']))
        
        # Expand all folders by default
        self.expandAll()


    def show_context_menu(self, position: QPoint) -> None:
        """Show context menu with create action"""
        item = self.itemAt(position)
        if not item:
            return

        menu = QMenu()
        create_action = QAction("Create Note", self)
        create_action.triggered.connect(lambda: self.create_note(item))
        menu.addAction(create_action)

        menu.exec(self.viewport().mapToGlobal(position))

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



# AI:
# This implementation:
# 
#  1 Uses a two-pass approach for better performance:
#     • First pass creates all folder items and stores them in a dict for O(1) lookup
#     • Second pass adds notes under their respective folders
#  2 Uses QTreeWidgetItem's setData to store metadata:
#     • For folders: ('folder', folder_id)
#     • For notes: ('note', note_id)
#  3 Handles nested folder structure by checking parent_id
#  4 Expands all folders by default for better UX
# 
# The implementation assumes the note model's get_note_tree_structure() will return a dictionary like:
# 
# 
#  {
#      "folder_id_1": {
#          "type": "folder",
#          "title": "Folder 1",
#          "parent_id": None,  # or another folder ID
#          "notes": [
#              {"id": "note_id_1", "title": "Note 1"},
#              {"id": "note_id_2", "title": "Note 2"}
#          ]
#      },
#      "folder_id_2": {
#          "type": "folder",
#          "title": "Folder 2",
#          "parent_id": "folder_id_1",
#          "notes": []
#      }
#  }
# 
# 
# We'll need to implement the get_note_tree_structure() method in the note model next. Would you like me to help with that?
