from note_model import NoteModel
from widgets__search_tab import NoteListWidget


class BackLinksWidget(NoteListWidget):
    """Widget for displaying backlinks in the sidebar"""

    def __init__(self, note_model: NoteModel) -> None:
        super().__init__()
        self.note_model = note_model

    def populate(self, note_id: str) -> None:
        """Populate the list with backlinks for the given note"""
        backlinks = self.note_model.get_backlinks(note_id)
        self.populate_notes_list(backlinks)
