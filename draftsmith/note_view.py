from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QSplitter,
)
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve
from note_model import NoteModel
from utils__tree_handler import TreeStateHandler
from widgets__note_tree import NoteTree
from widgets__edit_preview import EditPreview


class NoteView(QWidget):
    note_content_changed = Signal(int, str)  # (note_id, content)
    note_saved = Signal(int, str)  # (note_id)

    ANIMATION_DURATION = 300  # Animation duration in milliseconds
    DEFAULT_SIDEBAR_WIDTH = 200  # Default sidebar width

    def __init__(
        self, parent: QWidget | None = None, model: NoteModel | None = None
    ) -> None:
        super().__init__(parent)
        self.model = model or NoteModel()
        self.current_note_id: int | None = None
        self._left_animation = None
        self._right_animation = None
        self._sidebar_width = self.DEFAULT_SIDEBAR_WIDTH
        self.setup_ui()
        self._populate_ui()
        self._connect_signals()

    def _populate_ui(self) -> None:
        self.tree_widget.populate_tree()

    def setup_ui(self) -> None:
        # Main layout to hold the splitter
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create main horizontal splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(15)  # Increase grab area
        main_layout.addWidget(self.main_splitter)

        # Left sidebar
        self.left_sidebar = QFrame()
        self.left_sidebar.setObjectName("leftSidebar")
        self.left_sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        # TODO should I instantiate the widgets earlier?
        # then simply add them in the layout here?
        self.tree_widget = NoteTree(self.model)
        left_layout.addWidget(self.tree_widget)
        self.left_sidebar.setLayout(left_layout)

        # Main content area
        self.content_area = EditPreview()
        self.content_area.setObjectName("contentArea")

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

    def _connect_signals(self) -> None:
        """Connect UI signals to handlers"""
        # Internal Signals
        self.tree_widget.itemSelectionChanged.connect(self._on_tree_selection_changed)

        # Emit Signals
        # Emit signals to Model
        self.content_area.editor.textChanged.connect(self._on_editor_text_changed)
        self.note_saved.connect(self.model.save)
        self.tree_widget.note_created.connect(
            lambda folder_id: self._on_note_created(folder_id)
        )

        # Receive signals
        # Receive signals from Model
        self.model.refreshed.connect(self._refresh)

    def _on_note_created(self, folder_id: int) -> None:
        try:
            self.model.create_note(folder_id)
        except ValueError as e:
            print(e)

    def _refresh(self) -> None:
        """
        Refresh the view after the model has been updated.

        This is private, as it should only be triggered by a signal,
        typically from the model.
        """
        # Save current animation state and disable animation
        is_animated = self.tree_widget.isAnimated()
        self.tree_widget.setAnimated(False)

        try:
            tree_state_handler = TreeStateHandler(self.tree_widget)
            tree_state_handler.save_state()

            # Populate the UI
            self._populate_ui()

            # Restore the fold state
            tree_state_handler.restore_state(self.tree_widget)
        finally:
            # Restore original animation state
            self.tree_widget.setAnimated(is_animated)

    def save(self) -> None:
        """Emit a signal to save the current note"""
        if id := self.current_note_id:
            # Save the note
            self.note_saved.emit(id, self.content_area.editor.toPlainText())

    def _on_editor_text_changed(self) -> None:
        """
        Handle the text changed signal from the editor
        """
        if id := self.current_note_id:
            try:
                self.model.on_note_content_changed(
                    id, self.content_area.editor.toPlainText()
                )
            except ValueError as e:
                print(e)

    def _on_tree_selection_changed(self) -> None:
        items = self.tree_widget.selectedItems()
        if not items:
            return

        item = items[0]
        item_type, item_id = item.data(0, Qt.ItemDataRole.UserRole)

        if item_type == "note":
            self.current_note_id = item_id
            note = self.model.find_note_by_id(item_id)
            if note:
                self.content_area.editor.setPlainText(note.content)
        else:
            self.current_note_id = None
            self.content_area.editor.clear()

    def _get_left_sidebar_width(self) -> float:
        return float(self.left_sidebar.width())

    def _set_left_sidebar_width(self, width: float) -> None:
        if self.left_sidebar:
            self.left_sidebar.setFixedWidth(int(width))

    def _get_right_sidebar_width(self) -> float:
        return float(self.right_sidebar.width())

    def _set_right_sidebar_width(self, width: float) -> None:
        if self.right_sidebar:
            self.right_sidebar.setFixedWidth(int(width))

    # Properties for animation
    leftSidebarWidth = Property(
        float,
        _get_left_sidebar_width,
        _set_left_sidebar_width,
        freset=None,
        doc="Property for animating left sidebar width",
    )
    rightSidebarWidth = Property(
        float,
        _get_right_sidebar_width,
        _set_right_sidebar_width,
        freset=None,
        doc="Property for animating right sidebar width",
    )

    def toggle_left_sidebar(self) -> None:
        """Toggle the visibility of the left sidebar with animation"""
        if (
            self._left_animation
            and self._left_animation.state() == QPropertyAnimation.State.Running
        ):
            self._left_animation.stop()

        self._left_animation = QPropertyAnimation(self, b"leftSidebarWidth")
        self._left_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._left_animation.setDuration(self.ANIMATION_DURATION)

        if self.left_sidebar.isVisible():
            self._left_animation.setStartValue(self.left_sidebar.width())
            self._left_animation.setEndValue(0)
            self._left_animation.finished.connect(self.left_sidebar.hide)
        else:
            self.left_sidebar.show()
            self._left_animation.setStartValue(0)
            self._left_animation.setEndValue(self._sidebar_width)

        self._left_animation.start()

    def toggle_right_sidebar(self) -> None:
        """Toggle the visibility of the right sidebar with animation"""
        if (
            self._right_animation
            and self._right_animation.state() == QPropertyAnimation.State.Running
        ):
            self._right_animation.stop()

        self._right_animation = QPropertyAnimation(self, b"rightSidebarWidth")
        self._right_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._right_animation.setDuration(self.ANIMATION_DURATION)

        if self.right_sidebar.isVisible():
            self._right_animation.setStartValue(self.right_sidebar.width())
            self._right_animation.setEndValue(0)
            self._right_animation.finished.connect(self.right_sidebar.hide)
        else:
            self.right_sidebar.show()
            self._right_animation.setStartValue(0)
            self._right_animation.setEndValue(self._sidebar_width)

        self._right_animation.start()

    # Alias for backward compatibility
    toggle_sidebar = toggle_left_sidebar
