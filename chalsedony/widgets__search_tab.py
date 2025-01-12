from typing import Callable, List
from PySide6.QtGui import QAction, QKeyEvent
from utils__ngram_filter import text_matches_filter
from PySide6.QtWidgets import (
    QApplication,
    QListWidgetItem,
    QMenu,
    QWidget,
    QVBoxLayout,
    QLineEdit,
)
from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QPoint, Signal, Qt

from widgets__stateful_tree import TreeItemData
from note_model import NoteModel
from db_api import ItemType, NoteSearchResult
from widgets__kbd_widgets import KbdListWidget
from copy import deepcopy


class SearchSidebar(QWidget):
    search_text_changed = Signal(str)  # Emits search query text
    note_selected = Signal(TreeItemData)  # TreeItemData: Note ID and type

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
        self.search_sidebar_list.item_selection_changed.connect(self.note_selected.emit)

    def populate_notes_list(self, search_query: str = "") -> None:
        """Populate the all notes list view with optional search filtering"""
        if search_query:
            # Use full text search
            results = self.model.search_notes(search_query)
            self.search_sidebar_list.populate(results)
        else:
            # Show all notes
            notes = self.model.get_all_notes()
            self.search_sidebar_list.populate(notes)


class NoteListWidget(KbdListWidget):
    # This is used to select a note even when follow_mode is disabled, otherwise notes update when moving through the tree
    note_selected = Signal(TreeItemData)  # The selected Item,
    status_bar_message = Signal(str)  # Signal to send messages to status bar
    # This is the typical method used when moving between the items
    # Avoid this as the UI is bad, also MUST block signals when populating the list
    # otherwise the UI will update on every item added added and C++ will double free or sig fault
    item_selection_changed = Signal(TreeItemData)  # The selected Item,

    def __init__(self) -> None:
        super().__init__()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.create_keybinings()
        self._connect_signals()
        self.itemClicked.connect(self._on_item_clicked)
        # TODO this should store the widget like the tree for fast lookup
        # Not needed righ now though.
        self.current_note_items: dict[str, str] = dict()

    def _connect_signals(self) -> None:
        """Connect internal signals"""
        self.currentItemChanged.connect(self._on_list_selection_changed)

    def _on_list_selection_changed(self) -> None:
        """Handle selection from the all notes list"""
        selected = self.currentItem()
        if selected:
            note_id = deepcopy(selected.data(Qt.ItemDataRole.UserRole))
            del selected
            if note_id:
                item_data = TreeItemData(
                    ItemType.NOTE,
                    deepcopy(note_id),
                    title="Title omitted, not needed in the search_tab emission",
                )
                self.item_selection_changed.emit(item_data)

    def populate(self, note_items: List[NoteSearchResult]) -> None:
        """Populate the all notes list view with optional search filtering"""
        self.current_note_items = {id: deepcopy(note) for id, note in note_items}
        self.clear()
        # Block signals
        self.blockSignals(True)
        try:
            for result in note_items:
                self.add_item(result)
        finally:
            # Unblock signals
            self.blockSignals(False)


    def filter_items(self, filter_text: str) -> None:
        """Filter list items using n-gram comparison"""
        for i in range(self.count()):
            item = self.item(i)
            if item:
                matches = text_matches_filter(
                    filter_text, item.text(), n=2, match_all=True
                )
                item.setHidden(not matches)

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

    def add_item(self, search_result: NoteSearchResult) -> QListWidgetItem:
        """Add a new text item to the list using NoteSearchResult and return the created item"""
        item = QListWidgetItem(search_result.title)
        item.setData(Qt.ItemDataRole.UserRole, search_result.id)
        super().addItem(item)
        return item

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard shortcuts for cut/paste operations"""
        if self.currentItem():
            key = Qt.Key(event.key())
            action = self.key_actions.get(key)
            if action is not None:
                action()
                event.accept()
                return

        # Let parent class handle other keys
        super().keyPressEvent(event)

    def create_keybinings(self) -> None:
        """Create keyboard shortcuts for tree operations.

        Returns:
            None
        """

        def note_select() -> None:
            if item := self.currentItem():
                title = item.text()
                item_id = item.data(Qt.ItemDataRole.UserRole)
                self.note_selected.emit(
                    TreeItemData(ItemType.NOTE, item_id, title=title)
                )
            else:
                self.send_status_message("No item selected")

        self.key_actions: dict[Qt.Key, Callable[[], None]] = {
            Qt.Key.Key_Return: note_select,
        }

    def send_status_message(self, message: str) -> None:
        """Send a message to the status bar"""
        self.status_bar_message.emit(message)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle item click to emit note_selected signal"""
        if item:
            title = item.text()
            item_id = item.data(Qt.ItemDataRole.UserRole)
            self.note_selected.emit(TreeItemData(ItemType.NOTE, item_id, title=title))
