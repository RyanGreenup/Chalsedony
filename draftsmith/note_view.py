from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
)


class NoteView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left sidebar
        self.left_sidebar = QFrame()
        self.left_sidebar.setObjectName("leftSidebar")
        self.left_sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        left_sidebar_layout = QVBoxLayout(self.left_sidebar)
        left_sidebar_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.left_sidebar)

        # Main content area
        self.content_area = QFrame()
        self.content_area.setObjectName("contentArea")
        self.content_area.setFrameShape(QFrame.Shape.StyledPanel)
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.content_area)

        # Right sidebar
        self.right_sidebar = QFrame()
        self.right_sidebar.setObjectName("rightSidebar")
        self.right_sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        right_sidebar_layout = QVBoxLayout(self.right_sidebar)
        right_sidebar_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.right_sidebar)

        # Set stretch factors
        main_layout.setStretch(0, 1)  # Left sidebar
        main_layout.setStretch(1, 3)  # Content area
        main_layout.setStretch(2, 1)  # Right sidebar
