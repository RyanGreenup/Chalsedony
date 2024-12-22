from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QMenu
from note_model import NoteModel, Folder


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
