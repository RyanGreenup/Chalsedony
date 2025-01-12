from typing import List, Optional
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QSplitter,
    QTabWidget,
    QLineEdit,
)

from command_palette import NoteSelectionPalette, NoteLinkPalette


from pathlib import Path
from db_api import ItemType
from PySide6.QtCore import (
    QItemSelection,
    QTimer,
    Qt,
    Signal,
    Property,
    QPropertyAnimation,
    QEasingCurve,
)
from note_model import NoteModel
from widgets__stateful_tree import TreeItemData
from widgets__note_tree import NoteTree
from widgets__edit_preview import EditPreview
from widgets__search_tab import NoteListWidget, SearchSidebar

HISTORY_TIME = 1000


class NoteView(QWidget):
    note_content_changed = Signal(int, str)  # (note_id, content)
    status_bar_message = Signal(str)  # Signal to send messages to status bar

    ANIMATION_DURATION = 300  # Animation duration in milliseconds
    DEFAULT_SIDEBAR_WIDTH = 200  # Default sidebar width

    def __init__(
        self,
        model: NoteModel,
        parent: QMainWindow,
        initial_note: Optional[str] = None,
        focus_journal: Optional[bool] = True,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.follow_mode = False
        self.current_note_id: str | None = None
        self._editor_maximized = False  # Track editor maximization state
        self._left_animation: QPropertyAnimation | None = None
        self._right_animation: QPropertyAnimation | None = None
        self._sidebar_width = self.DEFAULT_SIDEBAR_WIDTH
        self.setup_ui()
        self._populate_ui()
        self._connect_signals()
        self._setup_history()
        if focus_journal:
            self.focus_todays_journal()
        else:
            if initial_note:
                note = self.model.get_note_by_title(initial_note)
                if note is not None:
                    self._handle_note_selection(
                        TreeItemData(ItemType.NOTE, note.id, note.title)
                    )
                else:
                    self.send_status_message(f"Note '{initial_note}' not found")

    def _setup_history(self) -> None:
        self.history: List[TreeItemData] = []
        self.history_position = -1
        self._history_timer = QTimer()
        self._history_timer.setInterval(HISTORY_TIME)  # 5 seconds
        self._history_timer.setSingleShot(True)
        self._history_timer.timeout.connect(self._add_current_note_to_history)

    def focus_todays_journal(self) -> None:
        journal_page = self.model.get_journal_page_for_today()
        if journal_page is None:
            self.send_status_message("No journal page found for today")
            return
        item_data = TreeItemData(
            ItemType.NOTE, journal_page.id, title=journal_page.title
        )
        self._handle_note_selection(item_data)

    def send_status_message(self, message: str) -> None:
        """Send a message to the status bar"""
        self.status_bar_message.emit(message)

    def _populate_ui(self) -> None:
        self.tree_widget.populate_tree()
        self._populate_notes_list()

    def setup_ui(self) -> None:
        # Main layout to hold the splitter
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create main horizontal splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(15)  # Increase grab area
        main_layout.addWidget(self.main_splitter)

        # Left sidebar with tabs
        self.left_sidebar = QFrame()
        self.left_sidebar.setObjectName("leftSidebar")
        self.left_sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Add search bar above tabs
        self.note_filter = QLineEdit()
        self.note_filter.setPlaceholderText("Filter Items...")
        left_layout.addWidget(self.note_filter)

        # Create tab widget
        self.left_tabs = QTabWidget()

        # First tab - Tree view
        self.tree_widget = NoteTree(self.model)
        self.left_tabs.addTab(self.tree_widget, "Folders")

        # Second tab - Search and List view
        self.search_tab = SearchSidebar(model=self.model)
        self.left_tabs.addTab(self.search_tab, "All Notes")

        left_layout.addWidget(self.left_tabs)
        self.left_sidebar.setLayout(left_layout)

        # Main content area
        self.content_area = EditPreview(self.model)
        self.content_area.setObjectName("contentArea")

        # Right sidebar with three vertical note lists
        self.setup_ui_right_sidebar()

        # Add frames to splitter
        self.main_splitter.addWidget(self.left_sidebar)
        self.main_splitter.addWidget(self.content_area)
        self.main_splitter.addWidget(self.right_sidebar)

        # Set initial sizes (similar proportions to the previous stretch factors)
        self.main_splitter.setSizes([100, 300, 100])

    def setup_ui_right_sidebar(self) -> None:
        self.right_sidebar = QFrame()
        self.right_sidebar.setObjectName("rightSidebar")
        self.right_sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Create vertical splitter for note lists
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setHandleWidth(15)

        # Create three note list widgets
        self.backlinks_list = NoteListWidget()
        self.forwardlinks_list = NoteListWidget()
        # self.bottom_note_list = NoteListWidget()

        # Add them to the splitter
        self.right_splitter.addWidget(self.backlinks_list)
        self.right_splitter.addWidget(self.forwardlinks_list)
        # self.right_splitter.addWidget(self.bottom_note_list)

        # Set equal initial sizes
        self.right_splitter.setSizes([100, 100])

        right_layout.addWidget(self.right_splitter)
        self.right_sidebar.setLayout(right_layout)

    def _connect_signals(self) -> None:
        """Connect UI signals to handlers"""
        parent = self.parent()
        if hasattr(parent, "style_changed"):
            parent.style_changed.connect(self.content_area.apply_dark_theme)  # type: ignore[reportAttributeAccessIssue]  # parent is QMainWindow which has style_changed
        else:
            raise AttributeError(
                "Parent window must have a style_changed signal otherwise the dark theme will not be applied"
            )

        # Internal Signals
        self.tree_widget.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree_widget.note_selected.connect(
            lambda item: self._handle_note_selection(item, change_tree=False)
        )

        # Emit Signals
        # Emit signals to Model
        self.content_area.editor.textChanged.connect(self._on_editor_text_changed)
        self.tree_widget.note_created.connect(
            lambda folder_id: self._on_note_created(folder_id)
        )
        self.tree_widget.note_deleted.connect(self._on_note_deleted)

        # Receive signals
        # Receive signals from Model
        self.model.refreshed.connect(self._refresh)
        # Tree
        self.tree_widget.folder_rename_requested.connect(self.update_folder_title)
        self.tree_widget.folder_moved.connect(self.update_folder_parent)
        self.tree_widget.note_moved.connect(self.update_note_folder)
        self.tree_widget.status_bar_message.connect(self.send_status_message)
        self.tree_widget.folder_duplicated.connect(self.model.copy_folder_recursive)
        # TODO consider focusing the note, this returns the new id
        self.tree_widget.duplicate_note.connect(self.model.duplicate_note)
        self.tree_widget.folder_deleted.connect(self.model.delete_folder_recursive)
        self.tree_widget.folder_create.connect(self._on_create_folder_requested)
        self.content_area.preview.note_selected.connect(self._handle_note_selection)

        # Connect search tab signals
        self.search_tab.search_text_changed.connect(self._on_search_text_changed)
        # This needs to be reviewed for follow mode with Enter (already implemented in widget
        self.search_tab.note_selected.connect(self._handle_note_selection)
        self.search_tab.search_sidebar_list.status_bar_message.connect(
            self.send_status_message
        )

        # Connect tree search
        self.note_filter.textChanged.connect(self.tree_widget.filter_tree)
        self.note_filter.textChanged.connect(
            self.search_tab.search_sidebar_list.filter_items
        )

        self.backlinks_list.note_selected.connect(self._handle_note_selection)
        self.forwardlinks_list.note_selected.connect(self._handle_note_selection)

    def _handle_note_selection_from_list(self, item: QItemSelection | None) -> None:
        """Handle note selection from the list view"""
        if not item or item.isEmpty():
            return

        # Get the first selected index
        indexes = item.indexes()
        if not indexes:
            return

        # Get the TreeItemData from the first index
        item_data = indexes[0].data(Qt.ItemDataRole.UserRole)
        if isinstance(item_data, TreeItemData):
            self._handle_note_selection(item_data)

    def note_selection_palette(self) -> None:
        """Open a note selection palette dialog"""
        all_notes = self.model.get_all_notes()
        palette = NoteSelectionPalette(self, all_notes)
        palette.note_selected.connect(self._handle_note_selection_from_id)
        palette.show()

    def note_link_palette(self) -> None:
        """Open a note selection palette dialog"""
        all_notes = self.model.get_all_notes()
        palette = NoteLinkPalette(self, all_notes)
        palette.insert_note_link.connect(self.insert_note_link)
        palette.show()

    def _handle_note_selection_from_id(self, note_id: str) -> None:
        """Handle note selection from the palette by ID"""
        note = self.model.find_note_by_id(note_id)
        if note:
            self._handle_note_selection(
                TreeItemData(ItemType.NOTE, note.id, note.title)
            )

    def _on_create_folder_requested(self, title: str, parent_id: str) -> None:
        try:
            folder_id = self.model.create_folder(title, parent_id)
        except ValueError as e:
            status_message = f"Failed to create folder: {e}"
            print(status_message)
            self.send_status_message(status_message)
            return
        # Use processEvents to ensure signals are handled before selection
        from PySide6.QtCore import QCoreApplication

        QCoreApplication.processEvents()
        self._handle_note_selection(TreeItemData(ItemType.FOLDER, folder_id, title))

    def save_current_note(self) -> None:
        """Save the current note with title update from heading"""
        if self.current_note_id:
            content = self.content_area.editor.toPlainText()
            self.model.save_note(
                self.current_note_id,
                content,
                refresh=True,
                update_title_from_heading=True,
            )

    def update_note_folder(self, note_id: str, new_folder_id: str) -> None:
        """Update which folder a note belongs to"""
        self.model.move_note(note_id, parent_id=new_folder_id)

    def update_folder_title(self, folder_id: str, new_title: str) -> None:
        """Update a folder's title and refresh the view"""
        self.model.update_folder(folder_id, title=new_title)

    def update_folder_parent(self, folder_id: str, new_parent_id: str) -> None:
        """Update a folder's parent ID and refresh the view"""
        self.model.update_folder(folder_id, parent_id=new_parent_id)

    def _on_note_created(self, folder_id: str) -> None:
        try:
            note_id = self.model.create_note(folder_id)
        except ValueError as e:
            status_message = f"Failed to create note: {e}"
            print(status_message)
            self.send_status_message(status_message)
            return
        self._handle_note_selection(
            TreeItemData(
                ItemType.NOTE, note_id, "Title Note Needed to select on Note Creation"
            )
        )

    def _on_note_deleted(self, note_id: str) -> None:
        try:
            self.model.delete_note(note_id)
        except ValueError as e:
            status_message = f"Failed to delete note: {e}"
            print(status_message)
            self.send_status_message(status_message)

    def _refresh(self) -> None:
        """
        Refresh the view after the model has been updated.

        This is private, as it should only be triggered by a signal,
        typically from the model.
        """
        # Save current animation state and disable animation
        is_animated = self.tree_widget.isAnimated()
        self.tree_widget.setAnimated(False)

        try:
            # Disable animations before any tree operations
            self.tree_widget.setAnimated(False)

            tree_state = self.tree_widget.export_state()

            # Populate the UI
            self._populate_ui()

            # Restore the fold state
            self.tree_widget.restore_state(tree_state)

            # Use a timer to restore animations after deferred events complete
            QTimer.singleShot(100, lambda: self.tree_widget.setAnimated(is_animated))
        except Exception as e:
            # Ensure animations are restored even if something fails
            self.tree_widget.setAnimated(is_animated)
            raise e

    def _on_editor_text_changed(self) -> None:
        """
        Handle the text changed signal from the editor
        """
        if id := self.current_note_id:
            try:
                self.model.on_note_content_changed(
                    id, self.content_area.editor.toPlainText()
                )
            except ValueError as e:
                print(e)

    def _on_tree_selection_changed(self) -> None:
        items = self.tree_widget.get_selected_items_data()
        if self.follow_mode and len(items) > 0:
            if len(items) > 0:
                self._handle_note_selection(items[0], change_tree=False)

    def _handle_note_selection(
        self, item_data: TreeItemData, change_tree: bool = True
    ) -> None:
        """Common handler for note selection from either tree or list"""
        # Safely disconnect textChanged signal to prevent update loop
        if self.current_note_id == item_data.id:
            print("Attempting to select the same note")
            self.send_status_message("Note already selected")
            return
        try:
            self.content_area.editor.textChanged.disconnect(
                self._on_editor_text_changed
            )
        except TypeError:
            # Signal was not connected
            pass
        except Exception as e:
            print(f"Error disconnecting signal: {e}")

        try:
            match item_data.type:
                case ItemType.NOTE:
                    self.current_note_id = item_data.id
                    note = self.model.find_note_by_id(item_data.id)
                    if note:
                        # Start timer for history tracking
                        self._history_timer.start()
                        self.content_area.editor.setPlainText(note.body or "")
                        if change_tree:
                            self.tree_widget.set_current_item_by_data(item_data)
                        self.backlinks_list.populate(
                            self.model.get_backlinks(item_data.id)
                        )
                        self.forwardlinks_list.populate(
                            self.model.get_forwardlinks(item_data.id)
                        )
                case ItemType.FOLDER:
                    self.current_note_id = None
                    self.content_area.editor.clear()
                    print(f"Selected folder: {item_data.title} -- {item_data.id}")
                    self.tree_widget.set_current_item_by_data(item_data)
        finally:
            # Reconnect signal after text is set
            self.content_area.editor.textChanged.connect(self._on_editor_text_changed)

    def _get_left_sidebar_width(self) -> float:
        return float(self.left_sidebar.width())

    def _set_left_sidebar_width(self, width: float) -> None:
        if self.left_sidebar:
            self.left_sidebar.setFixedWidth(int(width))

    def _get_right_sidebar_width(self) -> float:
        return float(self.right_sidebar.width())

    def _set_right_sidebar_width(self, width: float) -> None:
        if self.right_sidebar:
            self.right_sidebar.setFixedWidth(int(width))

    # Properties for animation
    leftSidebarWidth = Property(
        float,
        _get_left_sidebar_width,
        _set_left_sidebar_width,
        freset=None,
        doc="Property for animating left sidebar width",
    )
    rightSidebarWidth = Property(
        float,
        _get_right_sidebar_width,
        _set_right_sidebar_width,
        freset=None,
        doc="Property for animating right sidebar width",
    )

    def toggle_left_sidebar(self) -> None:
        """Toggle the visibility of the left sidebar with animation"""
        if (
            self._left_animation
            and self._left_animation.state() == QPropertyAnimation.State.Running
        ):
            self._left_animation.stop()

        animation = QPropertyAnimation(self, b"leftSidebarWidth")
        self._left_animation = animation
        self._left_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._left_animation.setDuration(self.ANIMATION_DURATION)

        if self.left_sidebar.isVisible():
            self._left_animation.setStartValue(self.left_sidebar.width())
            self._left_animation.setEndValue(0)
            self._left_animation.finished.connect(self.left_sidebar.hide)
        else:
            self.left_sidebar.show()
            self._left_animation.setStartValue(0)
            self._left_animation.setEndValue(self._sidebar_width)

        self._left_animation.start()

    def toggle_right_sidebar(self) -> None:
        """Toggle the visibility of the right sidebar with animation"""
        if (
            self._right_animation
            and self._right_animation.state() == QPropertyAnimation.State.Running
        ):
            self._right_animation.stop()

        animation = QPropertyAnimation(self, b"rightSidebarWidth")
        self._right_animation = animation
        self._right_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._right_animation.setDuration(self.ANIMATION_DURATION)

        if self.right_sidebar.isVisible():
            self._right_animation.setStartValue(self.right_sidebar.width())
            self._right_animation.setEndValue(0)
            self._right_animation.finished.connect(self.right_sidebar.hide)
        else:
            self.right_sidebar.show()
            self._right_animation.setStartValue(0)
            self._right_animation.setEndValue(self._sidebar_width)

        self._right_animation.start()

    # Alias for backward compatibility
    toggle_sidebar = toggle_left_sidebar

    def maximize_editor(self) -> None:
        """Maximize the editor panel in the content area"""
        self.content_area.maximize_editor()
        self._editor_maximized = True

    def maximize_preview(self) -> None:
        """Maximize the preview panel in the content area"""
        self.content_area.maximize_preview()
        self._editor_maximized = False

    def toggle_editor_preview(self) -> None:
        """Toggle between maximized editor and maximized preview"""
        if self._editor_maximized:
            self.maximize_preview()
            self._editor_maximized = False
        else:
            self.maximize_editor()
            self._editor_maximized = True

    def equal_split_editor(self) -> None:
        """Split editor and preview panels equally in the content area"""
        self.content_area.equal_split()

    def _populate_notes_list(self, search_query: str = "") -> None:
        """Populate the all notes list view with optional search filtering"""
        self.search_tab.populate_notes_list(search_query)

    def _on_search_text_changed(self, text: str) -> None:
        """Handle search text changes"""
        self._populate_notes_list(text)

    def get_current_note_id(self) -> str | None:
        """Return the ID of the currently selected note"""
        return self.current_note_id

    def upload_resource(self) -> None:
        """Handle resource file upload with optional title"""
        from PySide6.QtWidgets import QFileDialog, QInputDialog

        if not self.model:
            return

        # Get current note ID
        note_id = self.get_current_note_id()

        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Upload",
            "",  # Start in current directory
            "All Files (*);;Images (*.png *.jpg *.jpeg *.gif);;Documents (*.pdf *.doc *.docx *.txt)",
        )

        if not file_path:  # User canceled
            return

        # Get resource title from user
        title, ok = QInputDialog.getText(
            self,
            "Resource Title",
            "Enter a title for the resource:",
            text=Path(file_path).stem,  # Default to filename without extension
        )

        if not ok:  # User canceled
            return

        print(f"Uploading file: {file_path} with title: {title}")
        try:
            resource_id = self.model.upload_resource(
                Path(file_path), note_id, title=title if title else None
            )
            self.send_status_message(
                f"Uploaded resource: {title or Path(file_path).name}"
            )
            # Emit signal with resource ID if needed
            print(f"Resource ID: {resource_id}")
        except Exception as e:
            self.send_status_message(f"Error uploading file: {str(e)}")
            return

        if note_id and resource_id is not None:
            # Create markdown link
            resource_name = self.model.get_resource_title(resource_id)
            text = f"![{resource_name}](:/{resource_id})"
            self.insert_text_at_cursor(text, copy=True)

    def insert_text_at_cursor(self, text: str, copy: bool = False) -> None:
        """Insert text at the current cursor position in the editor"""
        self.content_area.editor.insert_text_at_cursor(text, copy=copy)

    def insert_note_link(self, note_id: str) -> None:
        """Insert a link to a note at the current cursor position in the editor"""
        note = self.model.get_note_meta_by_id(note_id)
        if note:
            text = f"[{note.title}](:/{note.id})"
            self.insert_text_at_cursor(text, copy=True)

    def _add_current_note_to_history(self) -> None:
        """Add current note to history after timer expires"""
        if self.current_note_id:
            note = self.model.find_note_by_id(self.current_note_id)
            if note:
                item_data = TreeItemData(
                    ItemType.NOTE, self.current_note_id, title=note.title
                )
                # Remove any forward history when adding new item
                if self.history_position < len(self.history) - 1:
                    self.history = self.history[: self.history_position + 1]
                # Don't add duplicates
                if len(self.history) == 0 or self.history[-1] != item_data:
                    self.history.append(item_data)
                    self.history_position = len(self.history) - 1

    def go_back_in_history(self) -> None:
        """Navigate backwards in the note history"""
        if self.history_position > 0:
            self.history_position -= 1
            item_data = self.history[self.history_position]
            # Temporarily stop history tracking while navigating
            self._history_timer.stop()
            self._handle_note_selection(item_data)
            self._history_timer.start()

    def go_forward_in_history(self) -> None:
        """Navigate forwards in the note history"""
        if self.history_position < len(self.history) - 1:
            self.history_position += 1
            item_data = self.history[self.history_position]
            # Temporarily stop history tracking while navigating
            self._history_timer.stop()
            self._handle_note_selection(item_data)
            self._history_timer.start()

    def focus_filter_bar(self) -> None:
        """Focus the search bar in the tree view"""
        self.note_filter.setFocus()

    def focus_search_bar(self) -> None:
        """Focus the search bar in the tree view"""
        # Focus the tab
        self.left_tabs.setCurrentWidget(self.search_tab)
        # Focus the search bar
        self.search_tab.search_input.setFocus()

    def focus_note_tree(self) -> None:
        """Focus the tree view"""
        self.left_tabs.setCurrentWidget(self.tree_widget)
        self.tree_widget.setFocus()

    def focus_editor(self) -> None:
        """Focus the editor"""
        self.content_area.editor.setFocus()

    def focus_preview(self) -> None:
        """Focus the preview"""
        self.content_area.preview.setFocus()

    def focus_backlinks(self) -> None:
        """Focus the backlinks list"""
        # self.right_splitter.widget(0).setFocus()
        self.backlinks_list.setFocus()

    def focus_forwardlinks(self) -> None:
        """Focus the forwardlinks list"""
        # self.right_splitter.widget(1).setFocus()
        self.forwardlinks_list.setFocus()
