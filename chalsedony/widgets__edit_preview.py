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
from note_model import NoteModel
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
        print(html)
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


# TODO Refactor this so it simply talks to the model rather than looking at the filesystem
# Consider using signals instead of talking to the model directly? Not sure on that
# This will need the model anyway, it needs to get the resource_type to handle the link (e.g. open vs display image etc.)
# handling all that with signals won't be ideal
# Also need to handle note selection with signals for backlinks etc.
class NoteUrlRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, note_model: NoteModel) -> None:
        super().__init__()
        self.note_model = note_model

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        if info.requestUrl().scheme() == "note":
            # Extract the resource ID without any leading slashes
            resource_id = info.requestUrl().toString().replace("note://", "")
            print(f"Intercepted request for resource: {resource_id}")  # Debug print

            # Find the first matching file with this ID prefix
            if table := self.note_model.what_is_this(resource_id):
                match table:
                    case IdTable.NOTE:
                        if filepath := self.note_model.get_resource_path(resource_id) is not None:
                            info.redirect(QUrl(f"file://{filepath}"))
                            print(f"Redirecting to: {filepath}")  # Debug print
                            return
                        else:
                            print(
                                f"No matching file found for resource ID: {resource_id}"
                            )  # Debug print
                    case IdTable.FOLDER:
                        print(f"clicked a link to a folder ({resource_id}), should decide what to do with that, probably focus on clicked")
                    case IdTable.RESOURCE:
                        print("Clicked a link to a resource ({resource_id})")
                        match self.note_model.get_resource_mime_type(resource_id):
                            # Finish this match statement by checking the ResourceType (we don't care aobut the string) AI!


class NoteLinkPage(QWebEnginePage):
    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Create and set the URL interceptor
        self.interceptor = NoteUrlRequestInterceptor(note_model)
        self.setUrlRequestInterceptor(self.interceptor)

    def acceptNavigationRequest(
        self, url: QUrl | str, type: QWebEnginePage.NavigationType, isMainFrame: bool
    ) -> bool:
        """Handle link clicks in the preview"""
        # Handle string input
        if isinstance(url, str):
            url = QUrl(url)

        # Handle the navigation request
        if url.scheme() == "note":
            note_id = url.path().strip("/")
            print(f"Note link clicked! ID: {note_id}")
            return False  # Prevent default navigation

        # Allow normal navigation for other links
        return True

    def requestedUrl(self) -> QUrl:
        return QUrl("note://")


class WebPreview(QWebEngineView):
    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPage(NoteLinkPage(parent=self, note_model = note_model))
