from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QPalette
import sqlite3
from sqlite3 import Connection
from pathlib import Path
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
    QToolBar,
    QStatusBar,
    QMessageBox,
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
    save_note_signal = Signal()  # Signal to trigger note save
    note_selection_palette_requested = Signal()
    note_link_palette_requested = Signal()

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

        # Initialize model and view
        self.note_model = NoteModel(self.db_connection, assets)
        self.note_view = NoteView(
            parent=self,
            model=self.note_model,
            initial_note=initial_note,
            focus_journal=focus_journal,
        )

        # Connect signals to the view
        # Ask the model to refresh the data (which will emit a signal to refresh the view)
        self.refresh.connect(self.note_model.refresh)

        # Set the view as the central widget
        self.setCentralWidget(self.note_view)

        # Connect signals
        self._connect_signals()

    def toggle_style(self) -> None:
        """Toggle between light and dark mode"""
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                if app.palette() == self.palettes["light"]:
                    # Switch to dark mode
                    app.setPalette(self.palettes["dark"])
                    app.setProperty("darkMode", True)
                    app.setStyleSheet(QSS_STYLE)  # Reapply stylesheet to trigger update
                    self.style_changed.emit(True)
                else:
                    # Switch to light mode
                    app.setPalette(self.palettes["light"])
                    app.setProperty("darkMode", False)
                    app.setStyleSheet(QSS_STYLE)  # Reapply stylesheet to trigger update
                    self.style_changed.emit(False)

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
                        ),
                        MenuAction(
                            id="save_note",
                            text="&Save Note",
                            handler="save_note",
                            shortcut="Ctrl+S",
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

    def back_history(self) -> None:
        if view := self.get_current_view():
            view.go_back_in_history()

    def forward_history(self) -> None:
        if view := self.get_current_view():
            view.go_forward_in_history()

    def toggle_follow_mode(self) -> None:
        if view := self.get_current_view():
            view.follow_mode = not view.follow_mode
            # Update the menu action's checked state
            if action := self.menu_actions.get("toggle_follow_mode"):
                action.setChecked(view.follow_mode)
            self.set_status_message(
                f"Follow mode {'enabled' if view.follow_mode else 'disabled'}"
            )

    def todays_journal(self) -> None:
        if view := self.get_current_view():
            view.focus_todays_journal()

    def note_selection_palette(self) -> None:
        self.note_selection_palette_requested.emit()

    def note_link_palette(self) -> None:
        self.note_link_palette_requested.emit()

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
                app.setStyleSheet(app.styleSheet())

    def upload_resource(self) -> None:
        view = self.get_current_view()
        view.upload_resource()

    # TODO use setter getter, need to handle the current view in tabs
    def get_current_view(self) -> NoteView:
        return self.note_view

    def zoom_in(self) -> None:
        """Increase the UI scale factor by 10%"""
        self.zoom(1.1)

    def zoom_out(self) -> None:
        """Decrease the UI scale factor by 10%"""
        self.zoom(0.9)

    def toggle_sidebar(self) -> None:
        """Toggle the left sidebar visibility"""
        if self.note_view:
            self.note_view.toggle_left_sidebar()

    def toggle_right_sidebar(self) -> None:
        """Toggle the right sidebar visibility"""
        if self.note_view:
            self.note_view.toggle_right_sidebar()

    def maximize_editor(self) -> None:
        """Maximize the editor panel"""
        if self.note_view:
            self.note_view.maximize_editor()

    def maximize_preview(self) -> None:
        """Maximize the preview panel"""
        if self.note_view:
            self.note_view.maximize_preview()

    def equal_split_editor(self) -> None:
        """Split editor and preview equally"""
        if self.note_view:
            self.note_view.equal_split_editor()

    def toggle_editor_preview(self) -> None:
        """Toggle between maximized editor and preview"""
        if self.note_view:
            self.note_view.toggle_editor_preview()

    def show_settings(self) -> None:
        """Show the settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec()

    # TODO ensure this works when multiple tabs are implemented
    def save_note(self) -> None:
        """Trigger note save with title update from heading"""
        self.save_note_signal.emit()

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

    def _connect_signals(self) -> None:
        """Connect signals from child widgets"""
        # From Widgets
        if view := self.get_current_view():
            view.status_bar_message.connect(self.set_status_message)
