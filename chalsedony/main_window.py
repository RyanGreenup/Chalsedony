from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QAction, QPalette
import sqlite3
from sqlite3 import Connection
from pathlib import Path
from utils__neovim_ipc_handler import (
    InvalidEditorWidgetError,
    NeovimAlreadyRunning,
    NeovimHandler,
    Result,
    Ok,
    Err,
)
from note_view import NoteView
from note_model import (
    NoteModel,
)  # Ensure this imports the correct module with generate_dummy_data
from settings import SettingsDialog
from styles import QSS_STYLE
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QMainWindow,
    QMenuBar,
    QTextEdit,
    QToolBar,
    QStatusBar,
    QMessageBox,
    QTabWidget,
)
from typing import List, Dict, Optional, TypedDict
from pydantic import BaseModel
from palettes import create_dark_palette, create_light_palette


class MenuAction(BaseModel):
    id: str  # Unique identifier for the action
    text: str  # Display text (can include &)
    handler: str = "close"
    shortcut: str = ""


class MenuStructure(BaseModel):
    name: str
    actions: List[MenuAction]


class MenuConfig(BaseModel):
    menus: List[MenuStructure]


class ApplicationPalettes(TypedDict):
    default: QPalette
    dark: QPalette
    light: QPalette


class MainWindow(QMainWindow):
    menu_actions: Dict[str, QAction]
    base_font_size: float = 10.0  # Store original size
    current_scale: float = 1.0  # Track current scale factor
    style_changed = Signal(bool)  # Emits True for dark mode, False for light mode
    refresh = Signal()
    zoom_editor = Signal(float)  # Scale of zoom

    def __init__(
        self,
        database: Path,
        assets: Path,
        initial_note: Optional[str],
        focus_journal: Optional[bool],
    ) -> None:
        super().__init__()
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("No QApplication instance found")
        # Cast to QApplication to satisfy type checker
        app = QApplication.instance()
        assert isinstance(app, QApplication)
        style = app.style()
        assert isinstance(style, QStyle)

        # Connect to the database
        self.db_connection: Connection = sqlite3.connect(database)

        # Initialize palettes
        self.default_palette = style.standardPalette()
        self.dark_palette = create_dark_palette()
        self.palettes = ApplicationPalettes(
            default=create_dark_palette(),
            dark=create_dark_palette(),
            light=create_light_palette(),
        )

        # Set initial darkMode property based on current palette
        is_dark = app.palette() == self.palettes["dark"]
        app.setProperty("darkMode", is_dark)

        # Setup application font
        self.setup_application_font()

        self.menu_actions = {}
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()

        self.setWindowTitle("Chalsedony")
        self.setGeometry(100, 100, 800, 600)

        # Initialize model
        self.note_model = NoteModel(self.db_connection, assets)

        # Create tab widget for multiple views
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        # Create initial view
        self.add_new_tab(initial_note, focus_journal)

        # Connect the neovim handler
        self._nvim_handler: NeovimHandler | None = None

        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self._on_tab_change)

        # Connect signals to the view
        self.refresh.connect(self.note_model.refresh)

        # Set tab widget as central widget
        self.setCentralWidget(self.tab_widget)

        # Connect signals
        self._connect_signals()

    @property
    def nvim_handler(self) -> NeovimHandler:
        if self._nvim_handler is None:
            match self.connect_neovim_handler():
                case Ok():
                    pass
                case Err(error=e):
                    _ = e  # Unused variable
                    self._nvim_handler = NeovimHandler()
                    self.set_status_message(
                        "Warning: Neovim is not running but NOT connected to the editor! This is a bug"
                    )
        if self._nvim_handler:
            return self._nvim_handler
        else:
            message = "No neovim handler found, This is a bug as the neovim handler should have been created."
            self.set_status_message(message)
            raise ValueError(message)

    @nvim_handler.setter
    def nvim_handler(self, value: NeovimHandler) -> None:
        self._nvim_handler = value

    @nvim_handler.deleter
    def nvim_handler(self) -> None:
        if self._nvim_handler:
            self._nvim_handler.cleanup()
        self._nvim_handler = None

    def set_style(self, dark_mode: bool) -> None:
        """Set the application style to dark or light mode
        
        Args:
            dark_mode: True for dark mode, False for light mode
        """
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                self.statusBar().showMessage(
                    "Changing style... (this may take a moment)"
                )
                palette = self.palettes["dark"] if dark_mode else self.palettes["light"]
                QTimer.singleShot(
                    0,
                    lambda: (
                        app.setPalette(palette),
                        app.setProperty("darkMode", dark_mode),
                        app.setStyleSheet(QSS_STYLE),  # type: ignore # Reapply stylesheet to trigger update
                        self.style_changed.emit(dark_mode),  # type: ignore
                        None,
                    ),
                )

    def toggle_style(self) -> None:
        """Toggle between light and dark mode"""
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                is_dark = app.palette() != self.palettes["dark"]
                self.set_style(is_dark)

    @classmethod
    def get_menu_config(cls) -> MenuConfig:
        return MenuConfig(
            menus=[
                MenuStructure(
                    name="&File",
                    actions=[
                        MenuAction(
                            id="upload_resource",
                            text="&Upload Resource",
                            handler="upload_resource",
                            shortcut="Ctrl+U",
                        ),
                        MenuAction(
                            id="settings",
                            text="&Settings",
                            handler="show_settings",
                            shortcut="Ctrl+,",
                        ),
                        MenuAction(
                            id="exit",
                            text="E&xit",
                            handler="close",
                        ),
                        MenuAction(
                            id="refresh",
                            text="&Refresh",
                            handler="refresh",
                            shortcut="Ctrl+R",
                        ),
                        MenuAction(
                            id="save_note",
                            text="&Save Note",
                            handler="save_note",
                            shortcut="Ctrl+S",
                        ),
                        MenuAction(
                            id="new_tab",
                            text="New &Tab",
                            handler="add_new_tab",
                            shortcut="Ctrl+Alt+T",
                        ),
                        MenuAction(
                            id="close_tab",
                            text="&Close Tab",
                            handler="close_current_tab",
                            shortcut="Ctrl+W",
                        ),
                        MenuAction(
                            id="next_tab",
                            text="Next &Tab",
                            handler="next_tab",
                            shortcut="Ctrl+]",
                        ),
                        MenuAction(
                            id="previous_tab",
                            text="Previous &Tab",
                            handler="previous_tab",
                            shortcut="Ctrl+[",
                        ),
                    ],
                ),
                MenuStructure(
                    name="&View",
                    actions=[
                        MenuAction(
                            id="command_palette",
                            text="Command &Palette",
                            handler="show_command_palette",
                            shortcut="Ctrl+Shift+P",
                        ),
                        MenuAction(
                            id="note_selection_palette",
                            text="&Note Selection Palette",
                            handler="note_selection_palette",
                            shortcut="Ctrl+P",
                        ),
                        MenuAction(
                            id="note_link_palette",
                            text="&Note Link Palette",
                            handler="note_link_palette",
                            shortcut="Ctrl+L",
                        ),
                        MenuAction(
                            id="maximize_editor",
                            text="Maximize &Editor",
                            handler="maximize_editor",
                            shortcut="Ctrl+E",
                        ),
                        MenuAction(
                            id="maximize_preview",
                            text="Maximize &Preview",
                            handler="maximize_preview",
                            shortcut="Ctrl+Shift+E",
                        ),
                        MenuAction(
                            id="equal_split_editor",
                            text="&Equal Split Editor",
                            handler="equal_split_editor",
                            shortcut="Ctrl+Shift+T",
                        ),
                        MenuAction(
                            id="toggle_editor_preview",
                            text="Toggle Editor/&Preview",
                            handler="toggle_editor_preview",
                            shortcut="Ctrl+T",
                        ),
                        MenuAction(
                            id="toggle_style",
                            text="Toggle &Dark Mode",
                            handler="toggle_style",
                            shortcut="Ctrl+D",
                        ),
                        MenuAction(
                            id="zoom_in",
                            text="Zoom &In",
                            handler="zoom_in",
                            shortcut="Ctrl+=",
                        ),
                        MenuAction(
                            id="zoom_out",
                            text="Zoom &Out",
                            handler="zoom_out",
                            shortcut="Ctrl+-",
                        ),
                        MenuAction(
                            id="zoom_editor_in",
                            text="Zoom &Editor In",
                            handler="zoom_editor_in",
                            shortcut="Ctrl+Alt+=",
                        ),
                        MenuAction(
                            id="zoom_editor_out",
                            text="Zoom E&ditor Out",
                            handler="zoom_editor_out",
                            shortcut="Ctrl+Alt+-",
                        ),
                        MenuAction(
                            id="toggle_left_sidebar",
                            text="Toggle &Left Sidebar",
                            handler="toggle_sidebar",
                            shortcut="Ctrl+B",
                        ),
                        MenuAction(
                            id="toggle_right_sidebar",
                            text="Toggle &Right Sidebar",
                            handler="toggle_right_sidebar",
                            shortcut="Ctrl+Shift+B",
                        ),
                    ],
                ),
                MenuStructure(
                    name="&Go",
                    actions=[
                        MenuAction(
                            id="todays_journal",
                            text="&Today's Journal",
                            handler="todays_journal",
                            shortcut="Ctrl+G",
                        ),
                        MenuAction(
                            id="next_widget",
                            text="Next &Widget",
                            handler="focusNextChild",
                            shortcut="Ctrl+J",
                        ),
                        MenuAction(
                            id="previous_widget",
                            text="Previous Wi&dget",
                            handler="focusPreviousChild",
                            shortcut="Ctrl+K",
                        ),
                        MenuAction(
                            id="forward_history",
                            text="&Forward",
                            handler="forward_history",
                            shortcut="Ctrl+Alt+Right",
                        ),
                        MenuAction(
                            id="back_history",
                            text="&Back",
                            handler="back_history",
                            shortcut="Ctrl+Alt+Left",
                        ),
                        MenuAction(
                            id="search_preview_next",
                            text="&Search Preview Next",
                            handler="search_preview_next",
                            shortcut="F3",
                        ),
                        MenuAction(
                            id="search_preview_previous",
                            text="&Search Preview Previous",
                            handler="search_preview_previous",
                            shortcut="Shift+F3",
                        ),
                    ],
                ),
                MenuStructure(
                    name="&Focus",
                    actions=[
                        MenuAction(
                            id="focus_search_bar",
                            text="&Search Bar",
                            handler="focus_search_bar",
                            shortcut="F6",
                        ),
                        MenuAction(
                            id="focus_filter_bar",
                            text="&Filter Bar",
                            handler="focus_search_bar",
                            shortcut="Ctrl+/",
                        ),
                        MenuAction(
                            id="focus_note_tree",
                            text="Note &Tree",
                            handler="focus_note_tree",
                            shortcut="Ctrl+Alt+L",
                        ),
                        MenuAction(
                            id="focus_editor",
                            text="&Editor",
                            handler="focus_editor",
                            shortcut="Ctrl+Alt+B",
                        ),
                        MenuAction(
                            id="focus_backlinks",
                            text="&Backlinks",
                            handler="focus_backlinks",
                            shortcut="F7",
                        ),
                        MenuAction(
                            id="focus_forwardlinks",
                            text="Forward &Links",
                            handler="focus_forwardlinks",
                            shortcut="F8",
                        ),
                    ],
                ),
                MenuStructure(
                    name="&Edit",
                    actions=[
                        MenuAction(
                            id="start_nvim_session",
                            text="Start Neovim Session",
                            shortcut="Ctrl+Alt+N",
                            handler="start_nvim_session",
                        ),
                        MenuAction(
                            id="stop_nvim_session",
                            text="stop Neovim Session",
                            shortcut="Ctrl+Alt+X",
                            handler="stop_nvim_session",
                        ),
                        MenuAction(
                            id="open_neovim_gui",
                            text="Open Neovim GUI (Automatically Starts Session)",
                            shortcut="Ctrl+Alt+E",
                            handler="open_neovim_gui",
                        ),
                    ],
                ),
                MenuStructure(
                    name="&Options",
                    actions=[
                        MenuAction(
                            id="toggle_follow_mode",
                            text="Toggle &Follow Mode",
                            shortcut="Ctrl+F",
                            handler="toggle_follow_mode",
                        ),
                    ],
                ),
                MenuStructure(
                    name="&Help",
                    actions=[
                        MenuAction(
                            id="about",
                            text="&About",
                            handler="about",
                        ),
                    ],
                ),
            ]
        )

    # Searching
    def get_text(self) -> str | None:
        if view := self.current_view:
            text = view.search_tab.search_input.text()
            if not text:
                text = view.note_filter.text()
            return text
        return None

    def search_preview_previous(self) -> None:
        if view := self.current_view:
            if (text := self.get_text()) is not None:
                view.get_current_content_area().preview.findPrevious(text)
            else:
                self.set_status_message("No text to search for")

    def search_preview_next(self) -> None:
        if view := self.current_view:
            if (text := self.get_text()) is not None:
                view.get_current_content_area().preview.findNext(text)
            else:
                self.set_status_message("No text to search for")

    # Neovim Methods

    def get_current_editor(self) -> QTextEdit:
        """
        Get the current view and in that view get the current editor.

        This should/could handle multiple tabs in the future.
        """
        return self.current_view.get_current_content_area().editor

    def connect_neovim_handler(self) -> Result[None, Exception]:
        """
        Start the neovim handler if necessary and connect it to the current editor.
        """
        # If there is no handler, create one (this method wouldn't be called otherwise)
        if self._nvim_handler is None:
            self._nvim_handler = NeovimHandler()
        editor = self.get_current_editor()
        match self._nvim_handler.connect_editor(editor):
            case Ok():
                return Ok(None)
            case Err(error=e):
                match e:
                    case InvalidEditorWidgetError():
                        self.set_status_message("Invalid editor widget")
                    case _:
                        self.set_status_message(f"Error connecting to neovim: {e}")
                return Err(e)

    def start_nvim_session(self) -> None:
        match self.nvim_handler.start_nvim_session():
            case Ok(message):
                self.set_status_message(message)
            case Err(error=e):
                match e:
                    case NeovimAlreadyRunning():
                        self.set_status_message("Neovim is already running")
                    case _:
                        self.set_status_message(f"Error starting neovim: {e}")

    def stop_nvim_session(self) -> None:
        self.nvim_handler.stop_nvim_session()

    def open_neovim_gui(self) -> None:
        match self.nvim_handler.start_gui_neovim():
            case Ok(pid):
                self.set_status_message(f"Neovim GUI started with PID {pid}")
            case Err(error=e):
                self.set_status_message(f"Error starting neovim GUI: {e}")

    def zoom_editor_in(self) -> None:
        print("Zooming in")
        self.zoom_editor.emit(1.1)

    def zoom_editor_out(self) -> None:
        self.zoom_editor.emit(0.9)

    def focus_editor(self) -> None:
        if view := self.current_view:
            view.focus_editor()

    def focus_note_tree(self) -> None:
        if view := self.current_view:
            view.focus_note_tree()

    def focus_backlinks(self) -> None:
        if view := self.current_view:
            view.focus_backlinks()

    def focus_forwardlinks(self) -> None:
        if view := self.current_view:
            view.focus_forwardlinks()

    def focus_filter_bar(self) -> None:
        if view := self.current_view:
            view.focus_filter_bar()

    def focus_search_bar(self) -> None:
        if view := self.current_view:
            view.focus_search_bar()

    def back_history(self) -> None:
        if view := self.current_view:
            view.go_back_in_history()

    def forward_history(self) -> None:
        if view := self.current_view:
            view.go_forward_in_history()

    def toggle_follow_mode(self) -> None:
        if view := self.current_view:
            view.follow_mode = not view.follow_mode
            # Update the menu action's checked state
            if action := self.menu_actions.get("toggle_follow_mode"):
                action.setChecked(view.follow_mode)
            self.set_status_message(
                f"Follow mode {'enabled' if view.follow_mode else 'disabled'}"
            )

    def todays_journal(self) -> None:
        if view := self.current_view:
            view.focus_todays_journal()

    def note_selection_palette(self) -> None:
        if view := self.current_view:
            view.note_selection_palette()

    def note_link_palette(self) -> None:
        if view := self.current_view:
            view.note_link_palette()

    def zoom(self, factor: float) -> None:
        """Change the UI scale by the given factor.

        Args:
            factor: Scale multiplier (e.g., 1.1 for 10% increase, 0.9 for 10% decrease)
        """
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                # Update the current scale
                self.current_scale *= factor

                # Calculate new size based on base size and total scale
                new_size = max(6, round(self.base_font_size * self.current_scale))

                # Create a new font with the calculated size
                current_font = app.font()
                current_font.setPointSize(new_size)

                # Apply the font to the application
                app.setFont(current_font)

                # Force update on all widgets
                for widget in app.allWidgets():
                    widget.setFont(current_font)
                    try:
                        widget.update()
                    except AttributeError as e:
                        print(f"Error updating widget: {e}")
                    except TypeError as e:
                        print(f"Error updating widget: {e}")
                    except Exception as e:
                        print(f"Error updating widget: {e}")

                # Trigger style refresh
                # NOTE this could work instead of the loop, probably should be used as well
                # However, parsing the stylesheet is slow, so it's better to avoid it
                # User can toggle dark mode for now.
                # app.setStyleSheet(app.styleSheet())

    def upload_resource(self) -> None:
        if view := self.current_view:
            view.upload_resource()

    @property
    def current_view(self) -> NoteView:
        """Get the currently active NoteView from the tab widget"""
        if current_widget := self.tab_widget.currentWidget():
            if isinstance(current_widget, NoteView):
                return current_widget
            else:
                message = "Current widget is not a NoteView, this is a bug"
                print("ERROR:", message)
                self.set_status_message(message)
                raise RuntimeError(message)
        else:
            # This will happen when there are no tabs
            # On startup it will happen because there are no tabs yet, this is ok
            # QT deals with this and we can just return the empty tab widget
            # Possibly review this though, but it seems ok
            return current_widget  # type: ignore [return-value]

    def add_new_tab(
        self, initial_note: Optional[str] = None, focus_journal: Optional[bool] = None
    ) -> NoteView:
        """
        Create and add a new NoteView tab

        Args:
            initial_note: The note title to open initially (TODO this should probably be ID)
            focus_journal: Whether to focus the journal tree
        """
        tree_data = None
        if self.current_view:
            # Get the tree data from the current view
            tree_data = self.current_view.tree_widget.tree_data
            # If no initial note is provided, use the current note
            if not initial_note:
                if initial_note_id := self.current_view.current_note_id:
                    if initial_note_meta := self.note_model.get_note_meta_by_id(
                        initial_note_id
                    ):
                        initial_note = initial_note_meta.title

        view = NoteView(
            parent=self,
            model=self.note_model,
            # TODO if this is none, it should be the last viewed note
            initial_note=initial_note,
            focus_journal=focus_journal,
            tree_data=tree_data,
        )

        tab_index = self.tab_widget.addTab(view, "New Note")
        self.tab_widget.setCurrentIndex(tab_index)
        view.status_bar_message.connect(self.set_status_message)
        return view

    def close_tab(self, index: int) -> None:
        """Close a tab at the given index"""
        self.tab_widget.removeTab(index)

    def close_current_tab(self) -> None:
        """Close the currently active tab"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index)

    def next_tab(self) -> None:
        """Switch to the next tab"""
        current_index = self.tab_widget.currentIndex()
        if current_index < self.tab_widget.count() - 1:
            self.tab_widget.setCurrentIndex(current_index + 1)
        else:
            self.tab_widget.setCurrentIndex(0)

    def previous_tab(self) -> None:
        """Switch to the previous tab"""
        current_index = self.tab_widget.currentIndex()
        if current_index > 0:
            self.tab_widget.setCurrentIndex(current_index - 1)
        else:
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)

    def zoom_in(self) -> None:
        """Increase the UI scale factor by 10%"""
        self.zoom(1.1)

    def zoom_out(self) -> None:
        """Decrease the UI scale factor by 10%"""
        self.zoom(0.9)

    def toggle_sidebar(self) -> None:
        """Toggle the left sidebar visibility"""
        if view := self.current_view:
            view.toggle_left_sidebar()

    def toggle_right_sidebar(self) -> None:
        """Toggle the right sidebar visibility"""
        if view := self.current_view:
            view.toggle_right_sidebar()

    def maximize_editor(self) -> None:
        """Maximize the editor panel"""
        if view := self.current_view:
            view.maximize_editor()

    def maximize_preview(self) -> None:
        """Maximize the preview panel"""
        if view := self.current_view:
            view.maximize_preview()

    def equal_split_editor(self) -> None:
        """Split editor and preview equally"""
        if view := self.current_view:
            view.equal_split_editor()

    def toggle_editor_preview(self) -> None:
        """Toggle between maximized editor and preview"""
        if view := self.current_view:
            view.toggle_editor_preview()

    def show_settings(self) -> None:
        """Show the settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec()

    # TODO ensure this works when multiple tabs are implemented
    def save_note(self) -> None:
        """Trigger note save with title update from heading"""
        if view := self.current_view:
            view.save_current_note()

    def show_about_dialog(self) -> None:
        QMessageBox.about(
            self, "About Chalsedony", "Chalsedony\nVersion 0.1.0\n\nA notetaking tool."
        )

    def show_command_palette(self) -> None:
        """Show the command palette dialog"""
        from command_palette import CommandPalette

        dialog = CommandPalette(self, self.menu_actions)
        dialog.command_selected.connect(
            lambda action: action.trigger()
        )  # Connect the signal
        dialog.exec()

    def setup_application_font(self) -> None:
        """Set up the application font, using Fira Sans if available"""
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                font = app.font()
                # Try to set Fira Sans, falling back to system default if unavailable
                font.setFamilies(["Fira Sans", font.family()])
                self.base_font_size = font.pointSize()
                app.setFont(font)

    def create_menu_bar(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        menu_config = self.get_menu_config()
        self.menu_actions = {}

        for menu_struct in menu_config.menus:
            menu = menu_bar.addMenu(menu_struct.name)
            for action_item in menu_struct.actions:
                action = QAction(action_item.text, self)
                if action_item.shortcut:
                    action.setShortcut(action_item.shortcut)

                match action_item.handler:
                    case "close":
                        action.triggered.connect(self.close)
                    case "about":
                        action.triggered.connect(self.show_about_dialog)
                    case "refresh":
                        action.triggered.connect(self.refresh.emit)
                    case _:
                        if handler := getattr(self, action_item.handler, None):
                            action.triggered.connect(handler)

                # Make toggle_follow_mode action checkable
                if action_item.id == "toggle_follow_mode":
                    action.setCheckable(True)
                menu.addAction(action)
                self.menu_actions[action_item.id] = action

    def create_tool_bar(self) -> None:
        tool_bar = QToolBar("Main Toolbar", self)
        self.addToolBar(tool_bar)

        exit_action = self.menu_actions.get("exit")
        if exit_action is not None:
            tool_bar.addAction(exit_action)

    def create_status_bar(self) -> None:
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Ready")

    def set_status_message(self, message: str) -> None:
        """Set a message in the status bar"""
        self.statusBar().showMessage(message)

    def _on_tab_change(self, index: int) -> None:
        """Handle tab changes by updating status and reconnecting signals"""
        if index >= 0:
            if view := self.tab_widget.widget(index):
                if isinstance(view, NoteView):
                    # Update status message
                    self.set_status_message(
                        f"Switched to tab: {self.tab_widget.tabText(index)}"
                    )

                    # Reconnect signals for the new view
                    view.status_bar_message.connect(self.set_status_message)

                    # Update neovim handler connection
                    if self._nvim_handler:
                        self._nvim_handler.connect_editor(
                            view.get_current_content_area().editor
                        )

                    if (note_id := view.current_note_id) is not None:
                        view._handle_note_selection_from_id(note_id)

    def _connect_signals(self) -> None:
        """Connect signals from child widgets"""
        # From Widgets
        if view := self.current_view:
            view.status_bar_message.connect(self.set_status_message)
