from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QListWidgetItem,
    QMenu,
    QWidget,
    QVBoxLayout,
    QLineEdit,
)
from PySide6.QtCore import QPoint, Signal, Qt

from note_model import NoteModel
from db_api import NoteSearchResult
from widgets__kbd_widgets import KbdListWidget


class SearchSidebar(QWidget):
    search_text_changed = Signal(str)  # Emits search query text
    note_selected = Signal(str)  # Emits selected note ID

    def __init__(self, model: NoteModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = model
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search notes...")
        layout.addWidget(self.search_input)

        # List view
        self.search_sidebar_list = NoteListWidget()
        layout.addWidget(self.search_sidebar_list)

        self.setLayout(layout)
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect internal signals"""
        self.search_input.textChanged.connect(self.search_text_changed)
        self.search_sidebar_list.itemSelectionChanged.connect(
            self._on_list_selection_changed
        )

    def _on_list_selection_changed(self) -> None:
        """Handle selection from the all notes list"""
        selected = self.search_sidebar_list.selectedItems()
        if selected:
            note_id = selected[0].data(Qt.ItemDataRole.UserRole)
            if note_id:
                self.note_selected.emit(note_id)

    def populate_notes_list(self, search_query: str = "") -> None:
        """Populate the all notes list view with optional search filtering"""
        self.search_sidebar_list.clear()

        if search_query:
            # Use full text search
            results = self.model.search_notes(search_query)
            for result in results:
                self.search_sidebar_list.add_text_item(result)
        else:
            # Show all notes
            notes = self.model.get_all_notes()
            for note in notes:
                self.search_sidebar_list.add_text_item(note)


class NoteListWidget(KbdListWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu with note ID copy option"""
        item = self.itemAt(position)
        if not item:
            return

        note_id = item.data(Qt.ItemDataRole.UserRole)
        if not note_id:
            return

        menu = QMenu(self)

        # Create action to copy note ID
        copy_action = QAction(f"Copy Note ID: {note_id}", self)
        copy_action.triggered.connect(lambda: self._copy_to_clipboard(note_id))
        menu.addAction(copy_action)

        menu.exec(self.mapToGlobal(position))

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def add_text_item(self, search_result: NoteSearchResult) -> QListWidgetItem:
        """Add a new text item to the list using NoteSearchResult and return the created item"""
        item = QListWidgetItem(search_result.title)
        item.setData(Qt.ItemDataRole.UserRole, search_result.id)
        super().addItem(item)
        return item
