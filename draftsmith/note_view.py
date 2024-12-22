from PySide6.QtWidgets import (
    QPlainTextEdit,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
)
from PySide6.QtCore import Qt
from note_model import NoteModel, Folder
from PySide6.QtWebEngineWidgets import QWebEngineView
import markdown
from markdown.extensions.wikilinks import WikiLinkExtension
from PySide6.QtCore import Signal


class NoteView(QWidget):
    note_content_changed = Signal(str)
    def __init__(
        self, parent: QWidget | None = None, model: NoteModel | None = None
    ) -> None:
        super().__init__(parent)
        self.model = model or NoteModel()
        self.current_note_id: int | None = None
        self.setup_ui()
        self.populate_tree()
        self._emit_signals()
        self._receive_signals()

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
        self.tree_widget = QTreeWidget()
        self.tree_widget.setAnimated(True)
        self.tree_widget.setHeaderHidden(True)
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

    def populate_tree(self) -> None:
        """Populate the tree widget with folders and notes from the model"""
        self.tree_widget.clear()
        root_folders = self.model.get_root_folders()
        for folder in root_folders:
            self._add_folder_to_tree(folder, self.tree_widget)

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


    def _emit_signals(self) -> None:
        """Connect UI signals to handlers"""
        self.tree_widget.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.note_content_changed.connect(self.model.update_note_content)

    def _receive_signals(self) -> None:
        """
        Connect the signals
        """
        self.content_area.editor.textChanged.connect(self._on_editor_text_changed)


    def _on_editor_text_changed(self) -> None:
        """
        Handle the text changed signal from the editor
        """
        self.note_content_changed.emit(self.content_area.editor.toPlainText())

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
        css_includes = "" # self._get_css_resources()
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
