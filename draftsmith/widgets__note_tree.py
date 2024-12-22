from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QMenu, QAction

class NoteTree(QTreeWidget):
    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.note_model = note_model
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setAnimated(True)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def populate_tree(self) -> None:
        """Populate the tree widget with folders and notes from the model"""
        self.clear()
        root_folders = self.note_model.get_root_folders()
        for folder in root_folders:
            self._add_folder_to_tree(folder, self)

    def _add_folder_to_tree(
        self, folder: Folder, parent: QTreeWidget | QTreeWidgetItem
    ) -> None:
        """Recursively add a folder and its contents to the tree"""
        folder_item = QTreeWidgetItem(parent)
        folder_item.setText(0, folder.name)
        folder_item.setData(0, Qt.ItemDataRole.UserRole, ("folder", folder.id))

        # Add notes in this folder
        for note in folder.notes:
            note_item = QTreeWidgetItem(folder_item)
            note_item.setText(0, note.title)
            note_item.setData(0, Qt.ItemDataRole.UserRole, ("note", note.id))

        # Recursively add subfolders
        for subfolder in folder.children:
            self._add_folder_to_tree(subfolder, folder_item)

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

    def create_note(self, parent_item: QTreeWidgetItem) -> None:
        """Create a new note under the selected folder"""
        if parent_item.data(0, Qt.ItemDataRole.UserRole)[0] == "folder":
            # Logic to create a new note
            print("Creating a new note in:", parent_item.text(0))
            # You can add your logic here to actually create and add the note
