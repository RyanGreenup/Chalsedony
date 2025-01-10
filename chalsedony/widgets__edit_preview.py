from pathlib import Path
from PySide6.QtWidgets import (
    QTextEdit,
    QWidget,
    QVBoxLayout,
    QSplitter,
)
from PySide6.QtWebEngineCore import (
    QWebEngineUrlScheme,
    QWebEnginePage,
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestInfo,
)
import os
from PySide6.QtCore import (
    QDir,
    QDirIterator,
    Qt,
    Property,
    QPropertyAnimation,
    QEasingCurve,
    QUrl,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
import markdown

from db_api import IdTable
from note_model import NoteModel, ResourceType
import static_resources_rc  # pyright: ignore # noqa
import katex_resources_rc  # pyright: ignore   # noqa
import katex_fonts_rc  # pyright: ignore # noqa


# Register custom schemes for the Web Engine Preview
def register_scheme(
    scheme_name: str,
    scheme_flags: QWebEngineUrlScheme.Flag = (
        QWebEngineUrlScheme.Flag.LocalAccessAllowed
        | QWebEngineUrlScheme.Flag.CorsEnabled
    ),
) -> None:
    scheme = QWebEngineUrlScheme(scheme_name.encode())
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
    scheme.setFlags(scheme_flags)
    QWebEngineUrlScheme.registerScheme(scheme)


register_scheme("note")
register_scheme("qrc")


class EditPreview(QWidget):
    ANIMATION_DURATION = 300  # Animation duration in milliseconds

    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._splitter_animation: QPropertyAnimation | None = None
        self.note_model = note_model
        self.asset_dir = note_model.asset_dir
        self.setup_ui()

    def setup_ui(self) -> None:
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(15)

        self.editor = MDTextEdit()
        self.preview = WebPreview(note_model=self.note_model)

        # The background should be transparent to match the UI
        self.preview.setStyleSheet("background: transparent;")
        self.preview.page().setBackgroundColor(Qt.GlobalColor.transparent)

        # Connect the edit widget to update preview and scroll
        self.editor.textChanged.connect(self.update_preview_local)
        self.editor.verticalScrollBar().valueChanged.connect(self._sync_preview_scroll)

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)

        # Add splitter to layout
        layout.addWidget(self.splitter)

        # Set initial sizes after adding to layout
        self.splitter.setSizes([300, 300])

    def _get_css_resources(self) -> str:
        """Generate CSS link tags for all CSS files in resources

        If the file:

        ./static/static.qrc

        picked up the static css asset, then it will be included.

        """
        css_links = []
        it = QDirIterator(
            ":/css", QDir.Filter.Files, QDirIterator.IteratorFlag.Subdirectories
        )
        while it.hasNext():
            file_path = it.next()
            css_links.append(f'<link rel="stylesheet" href="qrc{file_path}">')

        # If needed to debug
        # print(css_links)
        # sys.exit()

        return "\n".join(css_links)

    def _apply_html_template(self, html: str) -> str:
        # Replace image URLs to use note: scheme
        html = html.replace('src=":', 'src="note:/')
        # Allow direct file:// URLs to pass through
        css_includes = self._get_css_resources()
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
                "pymdownx.tasklist",
            ]
        )

        html = md.convert(self.editor.toPlainText())
        # Use note:// as base URL so relative paths are resolved correctly
        self.preview.setHtml(self._apply_html_template(html), QUrl("note://"))

    def _get_editor_width(self) -> float:
        return float(self.editor.width())

    def _set_editor_width(self, width: float) -> None:
        if self.editor:
            total_width = self.splitter.width()
            preview_width = total_width - int(width)
            self.splitter.setSizes([int(width), preview_width])

    # Property for animation
    editorWidth = Property(
        float,
        _get_editor_width,
        _set_editor_width,
        freset=None,
        doc="Property for animating editor width",
    )

    def _animate_splitter(self, target_ratio: float) -> None:
        """
        Animate the splitter to a target ratio.
        target_ratio: float between 0 and 1 representing editor width proportion
        """
        if (
            self._splitter_animation
            and self._splitter_animation.state() == QPropertyAnimation.State.Running
        ):
            self._splitter_animation.stop()

        total_width = self.splitter.width()
        target_width = int(total_width * target_ratio)

        animation = QPropertyAnimation(self, b"editorWidth")
        self._splitter_animation = animation
        self._splitter_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._splitter_animation.setDuration(self.ANIMATION_DURATION)
        self._splitter_animation.setStartValue(float(self.editor.width()))
        self._splitter_animation.setEndValue(float(target_width))
        self._splitter_animation.start()

    def maximize_editor(self) -> None:
        """Maximize the editor panel"""
        self._animate_splitter(1.0)

    def maximize_preview(self) -> None:
        """Maximize the preview panel"""
        self._animate_splitter(0.0)

    def equal_split(self) -> None:
        """Split editor and preview equally"""
        self._animate_splitter(0.5)

    def _sync_preview_scroll(self) -> None:
        """Synchronize the preview scroll position with the editor"""
        scroll_fraction = self.editor.verticalScrollFraction()
        js = f"window.scrollTo(0, document.documentElement.scrollHeight * {scroll_fraction});"
        self.preview.page().runJavaScript(js)

    def apply_dark_theme(self, dark_mode: bool) -> None:
        self.preview.settings().setAttribute(
            self.preview.settings().WebAttribute.ForceDarkMode, dark_mode
        )


class MDTextEdit(QTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def verticalScrollFraction(self) -> float:
        """Return the current vertical scroll position as a fraction (0-1)"""
        scrollbar = self.verticalScrollBar()
        if scrollbar.maximum() == 0:
            return 0
        return scrollbar.value() / scrollbar.maximum()


class NoteUrlRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Intercepts and handles resource requests in the markdown preview.

    This class processes requests for resources referenced in markdown content,
    such as images, videos, and audio files. It handles the special 'note://'
    scheme used to reference resources within the application's note system.

    The interceptor:
    - Redirects image/video/audio requests to their actual file paths
    - Blocks requests for unsupported resource types
    - Handles note and folder links appropriately
    - Uses the NoteModel to resolve resource IDs to actual file paths
    """
    def __init__(self, note_model: NoteModel) -> None:
        super().__init__()
        self.note_model = note_model

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        url = info.requestUrl()

        # Handle local file URLs
        if url.scheme() == "file":
            file_path = url.toLocalFile()
            if os.path.exists(file_path):
                # Allow direct access to local files
                return
            else:
                info.block(True)
                return

        # Handle note:// URLs
        if url.scheme() == "note":
            resource_id = url.toString().replace("note://", "")
            print(f"Intercepted request for resource: {resource_id}")

            if table := self.note_model.what_is_this(resource_id):
                match table:
                    case IdTable.NOTE:
                        print(f"Request is a note: {resource_id}, this isn't handled yet, in the future it may transclude the note")
                        note_id = resource_id
                        _ = note_id
                    case IdTable.FOLDER:
                        print(f"Request is a folder: {resource_id}, this isn't handled yet, in the future it may include a list of the folder contents ")
                        folder_id = resource_id
                        _ = folder_id
                    case IdTable.RESOURCE:
                        if filepath := self.note_model.get_resource_path(resource_id):
                            # Allow direct access to resource files
                            url = QUrl.fromLocalFile(str(filepath))
                            print(f"---> Redirecting to resource file: {url}")
                            if str(filepath).endswith(('.mp4')):
                                print("Proprietary video file, this may not display correctly, try converting to webm")
                            info.redirect(url)
                            return
                    case _:
                        info.block(True)


class NoteLinkPage(QWebEnginePage):
    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Create and set the URL interceptor
        self.interceptor = NoteUrlRequestInterceptor(note_model)
        self.setUrlRequestInterceptor(self.interceptor)
        self.note_model = note_model

    def acceptNavigationRequest(
        self, url: QUrl | str, type: QWebEnginePage.NavigationType, isMainFrame: bool
    ) -> bool:
        """Handle link clicks in the preview"""
        # Handle string input
        if isinstance(url, str):
            url = QUrl(url)

        # Handle the navigation request
        if url.scheme() == "note":
            id = url.path().strip("/")
            if (id_type := self.note_model.what_is_this(id)) is not None:
                match id_type:
                    case IdTable.NOTE:
                        note_id = id
                        print(f"Note link clicked! ID: {note_id}")
                    case IdTable.FOLDER:
                        folder_id = id
                        print(f"Folder link clicked! ID: {folder_id}")
                    case IdTable.RESOURCE:
                        resource_id = id
                        print(f"Resource link clicked! ID: {resource_id}")
                        match self.note_model.get_resource_mime_type(resource_id)[1]:  # Get just the ResourceType
                            case ResourceType.IMAGE:
                                print(f"Image resource clicked: {resource_id}")
                            case ResourceType.VIDEO:
                                print(f"Video resource clicked: {resource_id}")
                            case ResourceType.AUDIO:
                                print(f"Audio resource clicked: {resource_id}")
                            case ResourceType.DOCUMENT:
                                print(f"Document resource clicked: {resource_id}")
                            case ResourceType.ARCHIVE:
                                print(f"Archive resource clicked: {resource_id}")
                            case ResourceType.CODE:
                                print(f"Code resource clicked: {resource_id}")
                            case ResourceType.OTHER:
                                print(f"Other resource clicked: {resource_id}")

            else:
                # This would depend if we can safely create a new note with the ID, not sure on the impact of changing note ids
                print(f"Note ID: {id} does not exist, in the future this may create a new note with that ID")
            return False  # Prevent default navigation

        # Allow normal navigation for other links
        return True

    def requestedUrl(self) -> QUrl:
        return QUrl("note://")


class WebPreview(QWebEngineView):
    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPage(NoteLinkPage(parent=self, note_model = note_model))


import subprocess
import platform


# Finish this function AI!
def open_file(file_path):
    if platform.system() == 'Windows':
        # Open the file with the default application
    elif platform.system() == 'Darwin':  # macOS
        # Open the file with the default application
    else:  # Linux and other Unix systems
        # Open the file with the default application
