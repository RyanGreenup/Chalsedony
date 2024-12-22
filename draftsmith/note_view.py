from PySide6.QtWidgets import (
    QPlainTextEdit,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QSplitter,
)
from PySide6.QtCore import Qt
from note_model import NoteModel
from PySide6.QtWebEngineWidgets import QWebEngineView
import markdown
from markdown.extensions.wikilinks import WikiLinkExtension
from PySide6.QtCore import Signal
from utils__tree_handler import TreeStateHandler
from widgets__note_tree import NoteTree


class NoteView(QWidget):
    note_content_changed = Signal(int, str)  # (note_id, content)
    note_saved = Signal(int, str)  # (note_id)

    def __init__(
        self, parent: QWidget | None = None, model: NoteModel | None = None
    ) -> None:
        super().__init__(parent)
        self.model = model or NoteModel()
        self.current_note_id: int | None = None
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
        tree_state_handler = TreeStateHandler(self.tree_widget)
        tree_state_handler.save_state()

        # Populate the UI
        self._populate_ui()

        # Restore the fold state
        tree_state_handler.restore_state(self.tree_widget)

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


class EditPreview(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self) -> None:
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(15)

        self.editor = QPlainTextEdit()
        self.preview = QWebEngineView()

        # The background should be transparent to match the UI
        self.preview.setStyleSheet("background: transparent;")
        self.preview.page().setBackgroundColor(Qt.GlobalColor.transparent)

        # Connect the edit widget to update preview
        self.editor.textChanged.connect(self.update_preview_local)

        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)

        # Add splitter to layout
        layout.addWidget(splitter)

        # Set initial sizes after adding to layout
        splitter.setSizes([300, 300])

    def _apply_html_template(self, html: str) -> str:
        css_includes = ""  # self._get_css_resources()
        return f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <link rel="stylesheet" href="qrc:/katex/katex.min.css">
            {css_includes}
            <style>
                body {{
                    background-color: transparent !important;
                }}
                .markdown {{
                    background-color: transparent !important;
                }}

                :root,
                [data-theme] {{
                  background-color: transparent !important;
                }}

                .prose :where(code):not(:where([class~="not-prose"] *)) {{
                  background-color: transparent !important;
                }}
            </style>
        </head>
        <body><div class="markdown">
            {html}
            </div>
            <script src="qrc:/katex/katex.min.js"></script>
            <script src="qrc:/katex/contrib/auto-render.min.js"></script>
            <script src="qrc:/katex/config.js"></script>
        </body>
        </html>
        """

    def update_preview_local(self) -> None:
        """
        Converts the editor from markdown to HTML and sets the preview HTML content.
        """
        # Convert markdown to HTML
        md = markdown.Markdown(
            extensions=[
                "fenced_code",
                "tables",
                "footnotes",
                WikiLinkExtension(
                    base_url=""
                ),  # TODO this is inconsistent, consider using scheme handler and prefixing with a url
            ]
        )

        html = md.convert(self.editor.toPlainText())
        self.preview.setHtml(self._apply_html_template(html))
