from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QSplitter,
)
from PySide6.QtCore import Qt


class NoteView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setup_ui()

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
        self.left_sidebar.setLayout(QVBoxLayout())
        self.left_sidebar.layout().setContentsMargins(0, 0, 0, 0)

        # Main content area
        self.content_area = QFrame()
        self.content_area.setObjectName("contentArea")
        self.content_area.setFrameShape(QFrame.Shape.StyledPanel)
        self.content_area.setLayout(QVBoxLayout())
        self.content_area.layout().setContentsMargins(0, 0, 0, 0)

        # Right sidebar
        self.right_sidebar = QFrame()
        self.right_sidebar.setObjectName("rightSidebar")
        self.right_sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        self.right_sidebar.setLayout(QVBoxLayout())
        self.right_sidebar.layout().setContentsMargins(0, 0, 0, 0)

        # Add frames to splitter
        self.main_splitter.addWidget(self.left_sidebar)
        self.main_splitter.addWidget(self.content_area)
        self.main_splitter.addWidget(self.right_sidebar)

        # Set initial sizes (similar proportions to the previous stretch factors)
        self.main_splitter.setSizes([100, 300, 100])
