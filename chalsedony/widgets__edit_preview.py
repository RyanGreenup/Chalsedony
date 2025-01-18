from pathlib import Path
from typing import Callable, final, override
import json
from PySide6.QtWidgets import (
    QApplication,
    QTextEdit,
    QWidget,
    QVBoxLayout,
    QSplitter,
)
from PySide6.QtGui import QFont, QImage, QWheelEvent
from PySide6.QtCore import Signal
import tempfile
import os
from .syntax_highlighter import MarkdownHighlighter
from .note_model import NoteModel

from typing import cast
from .widgets__textedit__vim_bindings import VimTextEdit
from .widgets__stateful_tree import TreeItemData
from .utils_html_to_markdown import html_to_markdown
from PySide6.QtWebEngineCore import (
    QWebEngineUrlScheme,
    QWebEnginePage,
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestInfo,
)
from PySide6.QtCore import (
    QDir,
    QDirIterator,
    Qt,
    Property,
    QPropertyAnimation,
    QEasingCurve,
    QUrl,
    QMimeData,
    QPoint,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from bs4 import BeautifulSoup, Tag
import markdown
from .utils__markdown_extensions import CustomWikiLinkExtension
import pymdownx.superfences

from .db_api import IdTable, ItemType
from .note_model import ResourceType

import subprocess
import platform
from . import katex_resources_rc  # pyright: ignore [reportUnusedImport]  # noqa
from . import katex_fonts_rc  # pyright: ignore [reportUnusedImport] # noqa


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


@final
class EditPreview(QWidget):
    ANIMATION_DURATION = 300  # Animation duration in milliseconds
    status_bar_message = Signal(str)  # Signal to send messages to status bar

    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._splitter_animation: QPropertyAnimation | None = None
        self.note_model = note_model
        self.asset_dir = note_model.asset_dir
        self.setup_ui()
        self._md: markdown.Markdown | None = None

    def setup_ui(self) -> None:
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(15)

        self.editor = MDTextEdit()
        self.preview = WebPreview(note_model=self.note_model)

        if not self.editor.request_copy_md_as_html.connect(self.copy_md_as_html):
            # TODO set status message
            print("Failed to connect request_copy_md_as_html signal")

        # The background should be transparent to match the UI
        self.preview.setStyleSheet("background: transparent;")
        self.preview.page().setBackgroundColor(Qt.GlobalColor.transparent)

        # Connect the edit widget to update preview and scroll
        _ = self.editor.textChanged.connect(self.update_preview_local)
        _ = self.editor.verticalScrollBar().valueChanged.connect(
            self._sync_preview_scroll
        )

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)

        # Add splitter to layout
        layout.addWidget(self.splitter)

        # Set initial sizes after adding to layout
        self.splitter.setSizes([300, 300])

        if app := QApplication.instance():
            self.apply_dark_theme(
                app.property("darkMode") or False
            )  # Don't Flash at Night

    def copy_md_as_html(self, md_text: str) -> None:
        clipboard = QApplication.clipboard()
        html = self.convert_md_to_html(md_text)
        clipboard = QApplication.clipboard()
        clipboard.setText(html)
        self.status_bar_message.emit("HTML copied to clipboard")

    @property
    def md(self) -> markdown.Markdown:
        if self._md:
            return self._md
        else:
            extension_configs = {  # pyright: ignore [reportUnknownVariableType]
                "pymdownx.superfences": {
                    "custom_fences": [
                        {
                            "name": "mermaid",
                            "class": "mermaid",
                            "format": pymdownx.superfences.fence_div_format,  # pyright: ignore [reportUnknownMemberType]
                        }
                    ]
                },
                # "pymdownx.highlight": {
                #     "auto_title": True,
                #     "auto_title_map": {"Python Console Session": "Python"},
                #     "linenums_style": "inline",
                #     "line_spans": "__codeline",
                # },
            }
            self._md = markdown.Markdown(
                extensions=[
                    "fenced_code",
                    "tables",
                    "footnotes",
                    "pymdownx.emoji",
                    # Allow md in html
                    # "md_in_html",
                    "pymdownx.extra",  # Replaces md_in_html?
                    "pymdownx.blocks.html",
                    "pymdownx.magiclink",
                    # "pymdownx.escapeall",  # Breaks math without the arithmatex extension # TODO
                    "pymdownx.blocks.admonition",
                    "pymdownx.blocks.details",
                    "pymdownx.blocks.tab",
                    "pymdownx.highlight",
                    "pymdownx.tasklist",
                    "attr_list",
                    "pymdownx.superfences",
                    "pymdownx.blocks.caption",
                    "pymdownx.progressbar",
                    CustomWikiLinkExtension(
                        note_model=self.note_model, base_url="note://"
                    ),
                ],
                extension_configs=extension_configs,  # pyright: ignore [reportUnknownArgumentType] # type: ignore [arg-type]
            )
            return self._md

    def convert_md_to_html(self, md_text: str | None = None) -> str:
        if not md_text:
            md_text = self.editor.toPlainText()
        html = self.md.convert(md_text)
        # Replace image URLs to use note: scheme
        html = self.preview.rewrite_html_links(html)
        html = html.replace('src=":', 'src="note:/')
        return html

    def update_preview_local(self) -> None:
        """
        Converts the editor from markdown to HTML and sets the preview HTML content.
        Preserves the current scroll position during updates.
        """
        # Get current scroll position before updating
        scroll_fraction = self.editor.verticalScrollFraction()

        # Convert markdown to HTML
        html = self.convert_md_to_html()

        # Connect to load finished signal to ensure scroll happens after content loads
        def restore_scroll(success: bool) -> None:
            if success:
                js = f"window.scrollTo(0, document.documentElement.scrollHeight * {scroll_fraction});"
                self.preview.page().runJavaScript(js)

        # Disconnect any previous connections to avoid multiple handlers
        try:
            if not self.preview.page().loadFinished.disconnect():
                print("Failed to disconnect loadFinished signal")
        except Exception:
            pass

        if not self.preview.page().loadFinished.connect(restore_scroll):
            print("Failed to connect loadFinished signal")

        self.preview.set_html(html)

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

    def refresh_preview(self) -> None:
        """Refresh the preview content"""
        # Reset the HTML base template to ensure the preview is updated
        self.preview.content_already_set = False
        self.preview.set_html(self.convert_md_to_html())


class MyTextEdit(QTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_font_size: int = self.font().pointSize()
        self.current_scale: float = 1.0

    @override
    def wheelEvent(self, e: QWheelEvent) -> None:
        """Handle mouse wheel events for zooming when Ctrl is pressed"""
        event = e
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom(1.1)  # Zoom in
            elif delta < 0:
                self.zoom(0.9)  # Zoom out
            event.accept()
        else:
            super().wheelEvent(event)

    def zoom(self, factor: float) -> None:
        """Change the font size by the given factor.

        Args:
            factor: Scale multiplier (e.g., 1.1 for 10% increase, 0.9 for 10% decrease)
        """
        # Update the current scale
        self.current_scale *= factor

        # Calculate new size based on base size and total scale
        new_size = max(6, round(self.base_font_size * self.current_scale))

        # Update font size
        font = self.font()
        font.setPointSize(new_size)
        self.setFont(font)


class MDTextEdit(MyTextEdit, VimTextEdit):
    # Signal emitted when an image is pasted: (filepath, title)
    imageUploadRequested: Signal = Signal(str)  # Filepath
    # Signal emitted with HTML content when copied
    request_copy_md_as_html: Signal = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Enable rich text paste handling
        self.setAcceptRichText(True)
        # Create context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        # Create a persistent temp directory for pasted images
        self.temp_dir: str = tempfile.mkdtemp(prefix="chalsedony_")
        self.highlighter: MarkdownHighlighter = MarkdownHighlighter(self.document())

    # This is needed to paste HTML but copy plain text
    @override
    def createMimeDataFromSelection(self) -> QMimeData:
        """Override to ensure copied text is plain text only while preserving newlines"""
        mime_data = QMimeData()
        cursor = self.textCursor()
        # Get the full selected text including formatting
        text = cursor.selection().toPlainText()
        mime_data.setText(text)
        return mime_data

    def insert_text_at_cursor(self, text: str, copy: bool = False) -> None:
        # Get the cursor position and insert markdown link
        cursor = self.textCursor()
        pos = cursor.position()

        if copy:
            # Copy markdown link to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

        # Insert at cursor position
        cursor.insertText(text)

        # Move cursor after the inserted text
        cursor.setPosition(pos + len(text))
        self.setTextCursor(cursor)

    @override
    def insertFromMimeData(self, source: QMimeData) -> None:
        """Handle paste events and transform HTML content using markdownify"""
        if source.hasImage():
            image = QImage(source.imageData())  # pyright: ignore [reportAny]
            if not image.isNull():
                # Save image to temp file
                temp_path = os.path.join(self.temp_dir, f"pasted_image_{id(image)}.png")
                if image.save(temp_path):
                    # Emit signal for upload
                    self.imageUploadRequested.emit(temp_path)
                return

        elif source.hasHtml():
            # Get the HTML content
            html = source.html()

            try:
                # Convert HTML to markdown
                markdown_text = html_to_markdown(html)
                # Insert the transformed text
                self.insertPlainText(markdown_text)
            except Exception:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, "html.parser")
                self.insertPlainText(soup.get_text())
        else:
            # Fall back to default behavior for non-HTML content
            super().insertFromMimeData(source)

    def verticalScrollFraction(self) -> float:
        """Return the current vertical scroll position as a fraction (0-1)"""
        scrollbar = self.verticalScrollBar()
        if scrollbar.maximum() == 0:
            return 0
        return scrollbar.value() / scrollbar.maximum()

    def _show_context_menu(self, pos: QPoint) -> None:
        """Show custom context menu with HTML copy option"""
        menu = self.createStandardContextMenu()

        # Add "Copy as HTML" action if there's a selection
        if self.textCursor().hasSelection():
            copy_html_action = menu.addAction("Copy Selection as HTML")
            copy_html_action.triggered.connect(self._copy_selection_as_html)

        menu.exec(self.mapToGlobal(pos))

    def _copy_selection_as_html(self) -> None:
        """Copy selected text as HTML to clipboard while preserving formatting"""
        cursor = self.textCursor()
        if cursor.hasSelection():
            # Get the HTML content
            html = cursor.selection().toHtml()
            # Emit signal with HTML content
            self.request_copy_md_as_html.emit(html)


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
        self.note_model: NoteModel = note_model

    @override
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

            # Start debugging around here
            # print(f"Intercepted request for resource: {resource_id}")

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
                            # Start debugging around here
                            # print(f"---> Redirecting to resource file: {url}")
                            if str(filepath).endswith((".mp4")):
                                print(
                                    "Proprietary video file, this may not display correctly, try converting to webm"
                                )
                            info.redirect(url)
                            return


class WebPreview(QWebEngineView):
    note_selected: Signal = Signal(TreeItemData)  # TreeItemData: Note ID and type

    def __init__(self, note_model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # TODO Refactor this so the WebPreview sets the content on construction
        self.content_already_set: bool = False  # Has the content been set?
        self._content_div: str = "markdown"
        self.setPage(NoteLinkPage(parent=self, note_model=note_model))
        self.note_model: NoteModel = note_model
        self.setZoomFactor(1.0)  # Initialize zoom factor

        # Connect to application font changes
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                app.fontChanged.connect(self._update_zoom_from_font)

        # Make it transparent
        self.reset_transparency()

        # Enable search functionality
        self._search_text = ""
        self._search_flags = cast(QWebEnginePage.FindFlag, 0)

    def update_content_div(self, div_class: str, content: str) -> None:
        """
        Set the inner HTML content of a div with the specified class using JavaScript.
        This is the appropriate way to set the content to avoid flickering and scrolling of the content.

        This will not evaluate Javascript, so only use this for updating content.

        When the user refreshes the page, the javascript will run.
        The set_div_content_and_eval function runs some javascript
        which is useful, e.g. mermaid and katex.

        Args:
            div_class: The CSS class name of the div to update
            content: The HTML content to set inside the div

        Returns:
            bool: True if the div was found and updated, False otherwise
        """
        # First check if the div exists
        check_js = f"""
            (function() {{
                return document.querySelector(".{div_class}") !== null;
            }})();
        """

        # Define callback to handle the result
        def handle_result(result: bool) -> None:
            if result:
                # Div exists, update its content
                # Improve this to perserve the state of
                update_js = f"""
                try {{
                    // Code that may throw an error
                    set_div_content_and_eval("{div_class}", {json.dumps(content)});
                }} catch (error) {{
                    // Code to handle the error
                    console.error("set_div_content does not exist (yet)", error.message);
                }}
                    """
                self.page().runJavaScript(update_js)
            else:
                # If there is no matching div, set from scratch
                self.content_already_set = False
                self.set_html(content)

        # Run the check and handle result
        self.page().runJavaScript(check_js, resultCallback=handle_result)
        self.content_already_set = True

    def set_html(self, html: str) -> None:
        if self.content_already_set:
            self.update_content_div(self._content_div, html)
        else:
            content = self.get_html_template(html)
            self.setHtml(content, QUrl("note://"))
            self.content_already_set = True

    def _get_css_resources(self) -> str:
        """Generate CSS link tags for all CSS files in resources

        If the file:

        ./static/static.qrc

        picked up the static css asset, then it will be included.

        """
        css_links: list[str] = []
        it = QDirIterator(
            ":/css", QDir.Filter.Files, QDirIterator.IteratorFlag.Subdirectories
        )
        while it.hasNext():
            file_path = it.next()
            if "vector" in file_path:
                continue
            css_links.append(f'<link rel="stylesheet" href="qrc{file_path}">')

        # If needed to debug
        # print(css_links)
        # sys.exit()

        return "\n".join(css_links)

    def get_html_template(self, html: str = "PLACEHOLDER_CONTENT") -> str:
        # Allow direct file:// URLs to pass through
        css_includes = self._get_css_resources()
        html = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <link rel="stylesheet" href="qrc:/katex/katex.min.css">
            <script src="qrc:/js/jquery.min.js"></script>
            <script src="qrc:/js/dataTables.js"></script>
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
            <script src="qrc:/js/pdfjs.js"></script>
            <script src="qrc:/js/my_pdfjs_init.js"></script>
            <script src="qrc:/js/asciinema-player.min.js"></script>
            <script src="qrc:/js/mermaid.min.js"></script>
            <script src="qrc:/js/set_div_content.js"></script>
        </body>
        </html>
        """
        # self.setHtml(html, QUrl("note://"))
        return html

    def get_csrf_token(self) -> str | None:
        """Get the CSRF token from the page's JavaScript context.

        Returns:
            The CSRF token as a string if found, None otherwise
        """
        token = None

        def callback(result) -> None:
            nonlocal token
            token = result

        self.page().runJavaScript(
            "document.querySelector('meta[name=\"csrf-token\"]')?.content",
            resultCallback=callback,
        )
        return token

    def reset_transparency(self) -> None:
        self.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.setStyleSheet("background: transparent;")

    def findText(
        self,
        subString: str,
        options: QWebEnginePage.FindFlag = QWebEnginePage.FindFlag(0),
        resultCallback: Callable | None = None,  # type:ignore [type-arg]
    ) -> None:
        """Search for text in the preview with browser-like functionality"""
        _ = resultCallback  # Unused
        self._search_text = subString
        self._search_flags = options
        self.page().findText(subString, options)

    def clear_search(self) -> None:
        """Clear the current search highlights"""
        # This is the method advised in the docs
        # https://doc.qt.io/qtforpython-6/PySide6/QtWebEngineCore/QWebEnginePage.html#PySide6.QtWebEngineCore.QWebEnginePage.findText
        self.page().findText("")

    def findNext(self, search_text: str) -> None:
        """Find next match of current search"""
        if search_text:
            flag = QWebEnginePage.FindFlag(0x0)  # Forward Search
            if search_text != search_text.lower():
                flag = QWebEnginePage.FindFlag.FindCaseSensitively
            self.page().findText(search_text, flag)
        else:
            self.clear_search()

    def findPrevious(self, search_text: str) -> None:
        """Find previous match of current search"""
        flags = QWebEnginePage.FindFlag.FindBackward
        if search_text:
            if search_text != search_text.lower():
                flags = flags | QWebEnginePage.FindFlag.FindCaseSensitively
            self.page().findText(search_text, flags)
        else:
            self.clear_search()

    def _update_zoom_from_font(self, font: QFont) -> None:
        """Update zoom factor based on application font size changes"""
        base_size = 10.0  # Match the base font size from MainWindow
        current_size = font.pointSize()
        zoom_factor = current_size / base_size
        self.setZoomFactor(zoom_factor)

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

                                        # Replace the original link with the new structure
                                        link.replace_with(
                                            wrap_in_details(
                                                soup, summary_link, video_tag
                                            )
                                        )
                                    case ResourceType.PDF:
                                        # Get the link text and title
                                        link_text = link.string or "PDF Document"
                                        title = link.get("title", "")
                                        mime_type_string = (
                                            self.note_model.get_resource_mime_type(
                                                resource_id
                                            )[0]
                                        )

                                        # Create the link for the summary
                                        summary_link = soup.new_tag("a")
                                        summary_link.string = link_text
                                        summary_link["href"] = f"note://{resource_id}"
                                        summary_link["title"] = title
                                        summary_link["data-from-md"] = ""
                                        summary_link["data-resource-id"] = resource_id
                                        if mime_type_string:
                                            summary_link["type"] = mime_type_string

                                        # Create PDF preview container
                                        pdf_container = soup.new_tag(
                                            "div",
                                            **{
                                                "class": "pdfjs_preview",
                                                "data-src": f":/{resource_id}",
                                            },
                                        )
                                        placeholder = soup.new_tag(
                                            "div", **{"class": "placeholder"}
                                        )
                                        placeholder.string = "Loading PDF preview..."
                                        pdf_container.append(placeholder)

                                        # Replace the original link with the new structure
                                        link.replace_with(
                                            wrap_in_details(
                                                soup, summary_link, pdf_container
                                            )
                                        )
                                    case ResourceType.AUDIO:
                                        # Get the link text and title
                                        link_text = link.string or "Audio"
                                        title = link.get("title", "")
                                        mime_type_string = (
                                            self.note_model.get_resource_mime_type(
                                                resource_id
                                            )[0]
                                        )

                                        # Create the link for the summary
                                        summary_link = soup.new_tag("a")
                                        summary_link.string = link_text
                                        summary_link["href"] = f"note://{resource_id}"
                                        summary_link["title"] = title
                                        summary_link["data-from-md"] = ""
                                        summary_link["data-resource-id"] = resource_id
                                        if mime_type_string:
                                            summary_link["type"] = mime_type_string

                                        # Create audio element
                                        audio_tag = soup.new_tag(
                                            "audio",
                                            **{
                                                "class": "media-player media-audio",
                                                "controls": "",
                                            },
                                        )
                                        source_tag = soup.new_tag(
                                            "source",
                                            src=f":/{resource_id}",
                                            type=f"{mime_type_string}",
                                        )
                                        audio_tag.append(source_tag)

                                        # Replace the original link with the new structure
                                        link.replace_with(
                                            wrap_in_details(
                                                soup, summary_link, audio_tag
                                            )
                                        )
                                    case ResourceType.CODE:
                                        # Get the link text and title
                                        link_text = link.string or "Code File"
                                        title = link.get("title", "")
                                        mime_type_string = (
                                            self.note_model.get_resource_mime_type(
                                                resource_id
                                            )[0]
                                        )

                                        # Create the link for the summary
                                        summary_link = soup.new_tag("a")
                                        summary_link.string = link_text
                                        summary_link["href"] = f"note://{resource_id}"
                                        summary_link["title"] = title
                                        summary_link["data-from-md"] = ""
                                        summary_link["data-resource-id"] = resource_id
                                        if mime_type_string:
                                            summary_link["type"] = mime_type_string

                                        # Create code block container
                                        code_container = soup.new_tag(
                                            "pre",
                                            **{
                                                "class": "code-block",
                                                "data-src": f":/{resource_id}",
                                            },
                                        )
                                        # TODO syntax highlighting isn't working, fix this
                                        # Get file extension for syntax highlighting
                                        filepath = self.note_model.get_resource_path(
                                            resource_id
                                        )
                                        ext = filepath.suffix[1:] if filepath else None
                                        lang_class = (
                                            get_language_class(ext) if ext else None
                                        )

                                        code_tag = soup.new_tag("code")
                                        if lang_class:
                                            code_tag["class"] = lang_class

                                        if filepath:
                                            try:
                                                with open(
                                                    filepath, "r", encoding="utf-8"
                                                ) as f:
                                                    code_content = f.read()
                                                code_tag.string = code_content
                                            except Exception as e:
                                                error_div = soup.new_tag(
                                                    "div", **{"class": "error"}
                                                )
                                                error_div.string = (
                                                    f"Error loading code: {str(e)}"
                                                )
                                                code_tag.append(error_div)
                                        else:
                                            error_div = soup.new_tag(
                                                "div", **{"class": "error"}
                                            )
                                            error_div.string = "Code file not found"
                                            code_tag.append(error_div)

                                        code_container.append(code_tag)

                                        # Replace the original link with the new structure
                                        link.replace_with(
                                            wrap_in_details(
                                                soup, summary_link, code_container
                                            )
                                        )
                                    case ResourceType.DOCUMENT:
                                        link["href"] = f"note://{resource_id}"
                                    case ResourceType.ARCHIVE:
                                        link["href"] = f"note://{resource_id}"
                                    case ResourceType.OTHER:
                                        link["href"] = f"note://{resource_id}"

        return str(soup)


class NoteLinkPage(QWebEnginePage):
    def __init__(self, note_model: NoteModel, parent: WebPreview) -> None:
        super().__init__(parent)
        # Create and set the URL interceptor
        self.interceptor = NoteUrlRequestInterceptor(note_model)
        self.setUrlRequestInterceptor(self.interceptor)
        self.note_model = note_model
        self._parent: WebPreview = parent

    def parent(self) -> WebPreview:
        return self._parent

    def acceptNavigationRequest(
        self, url: QUrl | str, type: QWebEnginePage.NavigationType, isMainFrame: bool
    ) -> bool:
        """Handle link clicks in the preview"""
        _ = isMainFrame  # Unused
        _ = type  # Unused
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
                        item_data = TreeItemData(
                            ItemType.NOTE, note_id, "Title Omitted, not needed Here"
                        )
                        self.parent().note_selected.emit(item_data)
                        print(f"Note link clicked! ID: {note_id}")
                    case IdTable.FOLDER:
                        folder_id = id
                        print(f"Folder link clicked! ID: {folder_id}")
                    case IdTable.RESOURCE:
                        resource_id = id
                        resource_path = self.note_model.get_resource_path(resource_id)
                        # DEBUG
                        # print(f"Resource link clicked! ID: {resource_id}")

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
                            case ResourceType.PDF:
                                try_open(resource_path)
                            case ResourceType.OTHER:
                                try_open(resource_path)
                            case ResourceType.HTML:
                                try_open(resource_path)
                            case _:  # pyright: ignore [reportUnnecessaryComparison]
                                print(
                                    f"Resource type not recognized: {self.note_model.get_resource_mime_type(resource_id)[1]}"
                                )
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


def get_language_class(ext: str) -> str | None:
    ext = ext.lower()
    lang_string = None
    match ext:
        case "py" | "python":
            lang_string = "python"
        case "js" | "javascript":
            lang_string = "javascript"
        case "html":
            lang_string = "html"
        case "r" | "rmd":
            lang_string = "r"
        case "sh":
            lang_string = "bash"
        case "css":
            lang_string = "css"
        case "cpp" | "c":
            lang_string = "cpp"
        case "java":
            lang_string = "java"
        case "json":
            lang_string = "json"
        case "sql":
            lang_string = "sql"
        case "yaml" | "yml":
            lang_string = "yaml"
        case "xml":
            lang_string = "xml"
        case "md":
            lang_string = "markdown"
        case "tex":
            lang_string = "latex"

    return f"language-{lang_string}"


def wrap_in_details(soup: BeautifulSoup, summary_link: Tag, content_tag: Tag) -> Tag:
    details_tag = soup.new_tag("details", open="")
    summary_tag = soup.new_tag("summary")
    summary_tag.append(summary_link)
    details_tag.append(summary_tag)
    details_tag.append(content_tag)
    return details_tag


def open_file(file_path: Path | str) -> None:
    if isinstance(file_path, Path):
        file_path = str(file_path)
    """Open a file with the system's default application"""
    if platform.system() == "Windows":
        os.startfile(file_path)  # type:ignore [attr-defined]
    elif platform.system() == "Darwin":  # macOS
        out = subprocess.run(["open", file_path])
        if out.returncode != 0:
            print(f"Error opening file: {out.stderr}")
    else:  # Linux and other Unix systems
        out = subprocess.run(["xdg-open", file_path])
        if out.returncode != 0:
            print(f"Error opening file: {out.stderr}")


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
