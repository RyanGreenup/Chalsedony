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

    def __init__(self, asset_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._splitter_animation: QPropertyAnimation | None = None
        self.asset_dir = asset_dir
        self.setup_ui()

    def setup_ui(self) -> None:
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(15)

        self.editor = MDTextEdit()
        self.preview = WebPreview(asset_dir=self.asset_dir)

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
    def __init__(self, asset_dir: Path) -> None:
        super().__init__()
        self.ASSET_DIR = str(asset_dir)

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        if info.requestUrl().scheme() == "note":
            # Extract the resource ID without any leading slashes
            resource_id = info.requestUrl().toString().replace("note://", "")
            print(f"Intercepted request for resource: {resource_id}")  # Debug print

            # Find the first matching file with this ID prefix
            for filename in os.listdir(self.ASSET_DIR):
                if filename.startswith(resource_id):
                    filepath = os.path.join(self.ASSET_DIR, filename)
                    info.redirect(QUrl(f"file://{filepath}"))
                    print(f"Redirecting to: {filepath}")  # Debug print
                    return

            print(
                f"No matching file found for resource ID: {resource_id}"
            )  # Debug print


class NoteLinkPage(QWebEnginePage):
    def __init__(self, asset_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.asset_dir = asset_dir
        # Create and set the URL interceptor
        self.interceptor = NoteUrlRequestInterceptor(self.asset_dir)
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
    def __init__(self, asset_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPage(NoteLinkPage(parent=self, asset_dir=asset_dir))
