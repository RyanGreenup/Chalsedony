from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
)
from PySide6.QtCore import Qt
from .note_model import NoteModel, Folder, Note


class NoteView(QWidget):
    def __init__(self, parent: QWidget | None = None, model: NoteModel | None = None) -> None:
        super().__init__(parent)
        self.model = model or NoteModel()
        self.setup_ui()
        self.populate_tree()

    def setup_ui(self):
        # Main layout to hold the splitter
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create main horizontal splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)

        # Left sidebar
        self.left_sidebar = QFrame()
        self.left_sidebar.setObjectName("leftSidebar")
        self.left_sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        left_layout.addWidget(self.tree_widget)
        self.left_sidebar.setLayout(left_layout)

        # Main content area
        self.content_area = QFrame()
        self.content_area.setObjectName("contentArea")
        self.content_area.setFrameShape(QFrame.Shape.StyledPanel)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_area.setLayout(content_layout)

        # Right sidebar
        self.right_sidebar = QFrame()
        self.right_sidebar.setObjectName("rightSidebar")
        self.right_sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_sidebar.setLayout(right_layout)

        # Add frames to splitter
        self.main_splitter.addWidget(self.left_sidebar)
        self.main_splitter.addWidget(self.content_area)
        self.main_splitter.addWidget(self.right_sidebar)

        # Set initial sizes (similar proportions to the previous stretch factors)
        self.main_splitter.setSizes([100, 300, 100])

    def populate_tree(self) -> None:
        """Populate the tree widget with folders and notes from the model"""
        self.tree_widget.clear()
        root_folders = self.model.get_root_folders()
        for folder in root_folders:
            self._add_folder_to_tree(folder, self.tree_widget)

    def _add_folder_to_tree(self, folder: Folder, parent: QTreeWidget | QTreeWidgetItem) -> None:
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
