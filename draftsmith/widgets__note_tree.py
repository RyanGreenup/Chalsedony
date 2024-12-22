from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget
from note_model import NoteModel, Folder


class NoteTree(QTreeWidget):
    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.note_model = note_model
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setAnimated(True)
        self.setHeaderHidden(True)

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
