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

import subprocess
import platform
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
        html = self.preview.rewrite_html_links(html)
        html = html.replace('src=":', 'src="note:/')
        # Allow direct file:// URLs to pass through
        css_includes = self._get_css_resources()
        return f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <link rel="stylesheet" href="qrc:/katex/katex.min.css">
            <script src="qrc:/js/jquery.min.js"></script>
            <script src="qrc:/js/dataTables.js"></script>
            <script src="qrc:/js/pdfjs.js"></script>
            <script src="qrc:/js/datatables_init.js"></script>


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
            <script src="qrc:/js/my_pdfjs_init.js"></script>
            <script src="qrc:/js/asciinema-player.min.js"></script>
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
                # Allow md in html
                "md_in_html",
            ]
        )

        html = md.convert(self.editor.toPlainText())
        # Use note:// as base URL so relative paths are resolved correctly
        html = self._apply_html_template(html)
        print(html)
        self.preview.setHtml(html, QUrl("note://"))

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
                        print(
                            f"Request is a note: {resource_id}, this isn't handled yet, in the future it may transclude the note"
                        )
                        note_id = resource_id
                        _ = note_id
                    case IdTable.FOLDER:
                        print(
                            f"Request is a folder: {resource_id}, this isn't handled yet, in the future it may include a list of the folder contents "
                        )
                        folder_id = resource_id
                        _ = folder_id
                    case IdTable.RESOURCE:
                        if filepath := self.note_model.get_resource_path(resource_id):
                            # Allow direct access to resource files
                            url = QUrl.fromLocalFile(str(filepath))
                            print(f"---> Redirecting to resource file: {url}")
                            if str(filepath).endswith((".mp4")):
                                print(
                                    "Proprietary video file, this may not display correctly, try converting to webm"
                                )
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
            # Extract ID from URL by removing scheme and host
            id = url.toString().replace("note://", "").strip("/")

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
                        resource_path = self.note_model.get_resource_path(resource_id)
                        print(f"Resource link clicked! ID: {resource_id}")

                        def try_open(resource_path: Path | None) -> None:
                            if resource_path is not None:
                                from PySide6.QtWidgets import QApplication

                                clipboard = QApplication.clipboard()
                                clipboard.setText(str(resource_path))
                                open_file(resource_path)
                            else:
                                print(f"Resource ID: {resource_id} does not exist")

                        match self.note_model.get_resource_mime_type(resource_id)[
                            1
                        ]:  # Get just the ResourceType
                            case ResourceType.IMAGE:
                                print(f"Image resource clicked: {resource_id}")
                                try_open(resource_path)
                            case ResourceType.VIDEO:
                                try_open(resource_path)
                            case ResourceType.AUDIO:
                                try_open(resource_path)
                            case ResourceType.DOCUMENT:
                                try_open(resource_path)
                            case ResourceType.ARCHIVE:
                                try_open(resource_path)
                            case ResourceType.CODE:
                                try_open(resource_path)
                            case ResourceType.OTHER:
                                try_open(resource_path)

            else:
                # This would depend if we can safely create a new note with the ID, not sure on the impact of changing note ids
                print(
                    f"Note ID: {id} does not exist, in the future this may create a new note with that ID"
                )
            return False  # Prevent default navigation

        # Allow normal navigation for other links
        return True

    def requestedUrl(self) -> QUrl:
        return QUrl("note://")


class WebPreview(QWebEngineView):
    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPage(NoteLinkPage(parent=self, note_model=note_model))
        self.note_model = note_model

    def rewrite_html_links(self, html: str) -> str:
        """Rewrite HTML links to use the note:// scheme based on their target type.

        Args:
            html: The input HTML containing links in the format <a href=":/{id}">{title}</a>

        Returns:
            HTML with rewritten links using appropriate schemes based on target type
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith(":/"):
                resource_id = href[2:]  # Remove the :/ prefix
                if (id_type := self.note_model.what_is_this(resource_id)) is not None:
                    match id_type:
                        case IdTable.NOTE:
                            link["href"] = f"note://{resource_id}"
                        case IdTable.FOLDER:
                            link["href"] = f"note://{resource_id}"
                        case IdTable.RESOURCE:
                            if filepath := self.note_model.get_resource_path(
                                resource_id
                            ):
                                # Filepath isn't used, but it may be useful in the future
                                _ = filepath
                                # Handle different resource types appropriately
                                mime_type = self.note_model.get_resource_mime_type(
                                    resource_id
                                )[1]
                                match mime_type:
                                    case ResourceType.IMAGE:
                                        link["href"] = f"note://{resource_id}"
                                    case ResourceType.VIDEO:
                                        # Get the link text and title
                                        link_text = link.string or "Video"
                                        title = link.get("title", "")
                                        mime_type_string = (
                                            self.note_model.get_resource_mime_type(
                                                resource_id
                                            )[0]
                                        )

                                        # Create details/summary structure
                                        details_tag = soup.new_tag("details", open="")
                                        summary_tag = soup.new_tag("summary")

                                        # Create the link for the summary
                                        summary_link = soup.new_tag("a")
                                        summary_link.string = link_text
                                        summary_link["href"] = f"note://{resource_id}"
                                        summary_link["title"] = title
                                        summary_link["data-from-md"] = ""
                                        summary_link["data-resource-id"] = resource_id
                                        summary_link["type"] = (
                                            f"video/{mime_type_string}"
                                        )

                                        # Create video element
                                        video_tag = soup.new_tag(
                                            "video",
                                            **{
                                                "class": "media-player media-video",
                                                "controls": "",
                                            },
                                        )
                                        source_tag = soup.new_tag(
                                            "source",
                                            src=f":/{resource_id}",
                                            type=f"{mime_type_string}",
                                        )
                                        video_tag.append(source_tag)

                                        # Build the structure
                                        summary_tag.append(summary_link)
                                        details_tag.append(summary_tag)
                                        details_tag.append(video_tag)

                                        # Replace the original link with the new structure
                                        link.replace_with(details_tag)
                                    case ResourceType.AUDIO:
                                        link["href"] = f"note://{resource_id}"
                                    case ResourceType.DOCUMENT:
                                        link["href"] = f"note://{resource_id}"
                                    case ResourceType.ARCHIVE:
                                        link["href"] = f"note://{resource_id}"
                                    case ResourceType.CODE:
                                        link["href"] = f"note://{resource_id}"
                                    case ResourceType.OTHER:
                                        link["href"] = f"note://{resource_id}"

        return str(soup)


def open_file(file_path: Path | str) -> None:
    if isinstance(file_path, Path):
        file_path = str(file_path)
    """Open a file with the system's default application"""
    if platform.system() == "Windows":
        os.startfile(file_path)  # type:ignore [attr-defined]
    elif platform.system() == "Darwin":  # macOS
        subprocess.run(["open", file_path])
    else:  # Linux and other Unix systems
        subprocess.run(["xdg-open", file_path])


SVG_VIDEO = """
<svg
        xmlns="http://www.w3.org/2000/svg"
        fill="currentColor"
        class="bi bi-globe"
        viewBox="0 0 16 16"
      >
        <path
          d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8zm7.5-6.923c-.67.204-1.335.82-1.887 1.855A7.97 7.97 0 0 0 5.145 4H7.5V1.077zM4.09 4a9.267 9.267 0 0 1 .64-1.539 6.7 6.7 0 0 1 .597-.933A7.025 7.025 0 0 0 2.255 4H4.09zm-.582 3.5c.03-.877.138-1.718.312-2.5H1.674a6.958 6.958 0 0 0-.656 2.5h2.49zM4.847 5a12.5 12.5 0 0 0-.338 2.5H7.5V5H4.847zM8.5 5v2.5h2.99a12.495 12.495 0 0 0-.337-2.5H8.5zM4.51 8.5a12.5 12.5 0 0 0 .337 2.5H7.5V8.5H4.51zm3.99 0V11h2.653c.187-.765.306-1.608.338-2.5H8.5zM5.145 12c.138.386.295.744.468 1.068.552 1.035 1.218 1.65 1.887 1.855V12H5.145zm.182 2.472a6.696 6.696 0 0 1-.597-.933A9.268 9.268 0 0 1 4.09 12H2.255a7.024 7.024 0 0 0 3.072 2.472zM3.82 11a13.652 13.652 0 0 1-.312-2.5h-2.49c.062.89.291 1.733.656 2.5H3.82zm6.853 3.472A7.024 7.024 0 0 0 13.745 12H11.91a9.27 9.27 0 0 1-.64 1.539 6.688 6.688 0 0 1-.597.933zM8.5 12v2.923c.67-.204 1.335-.82 1.887-1.855.173-.324.33-.682.468-1.068H8.5zm3.68-1h2.146c.365-.767.594-1.61.656-2.5h-2.49a13.65 13.65 0 0 1-.312 2.5zm2.802-3.5a6.959 6.959 0 0 0-.656-2.5H12.18c.174.782.282 1.623.312 2.5h2.49zM11.27 2.461c.247.464.462.98.64 1.539h1.835a7.024 7.024 0 0 0-3.072-2.472c.218.284.418.598.597.933zM10.855 4a7.966 7.966 0 0 0-.468-1.068C9.835 1.897 9.17 1.282 8.5 1.077V4h2.355z"
        ></path></svg>
"""
