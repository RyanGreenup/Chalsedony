from typing import override
import sys
from PySide6.QtWidgets import QWidget, QListWidgetItem
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from .db_api import NoteSearchResult
from .selection_dialog import SelectionDialog
from .utils__ngram_filter import text_matches_filter


class CommandPalette(SelectionDialog):
    command_selected: Signal = Signal(QAction)

    def __init__(self, parent: QWidget, actions: dict[str, QAction]) -> None:
        super().__init__(parent, "Command Palette")
        self._actions: dict[str, QAction] = actions
        self.search.setPlaceholderText("Type to search commands...")
        self.populate_commands()

    def populate_commands(self) -> None:
        """Populate the list with all commands"""
        self.list.clear()
        for action_id, action in self._actions.items():
            if not action.text():
                continue
            text = f"{action.text().replace('&', '')} "
            if shortcut := action.shortcut().toString():
                text += f"({shortcut})"
            self.list.addItem(text)

        # Select first item
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    @override
    def on_item_selected(self, item: QListWidgetItem) -> None:
        """Handle command selection"""
        text = item.text().split(" (")[0].strip()  # Remove shortcut and whitespace
        for action in self._actions.values():
            if action.text().replace("&", "") == text:
                self.command_selected.emit(action)
                if not self.close():
                    print("Failed to close command palette", file=sys.stderr)
                break


class NotePalette(SelectionDialog):
    note_selected: Signal = Signal(str)  # Emits note ID when selected

    def __init__(self, parent: QWidget, notes: list[NoteSearchResult]) -> None:
        super().__init__(parent, "Note Selection")
        self._notes: list[NoteSearchResult] = notes
        self.search.setPlaceholderText("Type to search notes...")
        self.populate_notes()

    def populate_notes(self) -> None:
        """Populate the list with all notes"""
        self.list.clear()
        for note in self._notes:
            self.list.addItem(note.title)

        # Select first item
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    @override
    def filter_items(self, text: str) -> None:
        """Filter items based on search text"""
        had_visible = False
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item:
                is_visible = text_matches_filter(text, item.text(), match_all=True)
                item.setHidden(not is_visible)
                if is_visible and not had_visible:
                    self.list.setCurrentItem(item)
                    had_visible = True


class NoteSelectionPalette(NotePalette):
    note_selected: Signal = Signal(str)  # Emits note ID when selected

    def __init__(self, parent: QWidget, notes: list[NoteSearchResult]) -> None:
        super().__init__(parent=parent, notes=notes)

    @override
    def on_item_selected(self, item: QListWidgetItem) -> None:
        """Handle note selection"""
        selected_title = item.text()
        for note in self._notes:
            if note.title == selected_title:
                self.note_selected.emit(note.id)
                if not self.close():
                    print("Failed to close note selection palette", file=sys.stderr)
                break


# TODO these should both be ordered by modified time
class NoteLinkPalette(NotePalette):
    insert_note_link: Signal = Signal(str)  # Emits note ID when selected

    def __init__(self, parent: QWidget, notes: list[NoteSearchResult]) -> None:
        super().__init__(parent=parent, notes=notes)

    @override
    def on_item_selected(self, item: QListWidgetItem) -> None:
        """Handle note selection"""
        selected_title = item.text()
        for note in self._notes:
            if note.title == selected_title:
                self.insert_note_link.emit(note.id)
                if not self.close():
                    print("Failed to close note link palette", file=sys.stderr)
                break
