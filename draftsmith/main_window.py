from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QPalette
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
from typing import List, Dict, TypedDict
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
    refresh = Signal()

    def __init__(self) -> None:
        super().__init__()
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("No QApplication instance found")
        # Cast to QApplication to satisfy type checker
        app = QApplication.instance()
        assert isinstance(app, QApplication)
        style = app.style()
        assert isinstance(style, QStyle)

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

        self.setWindowTitle("Draftsmith")
        self.setGeometry(100, 100, 800, 600)

        # Initialize model and view
        self.note_model = NoteModel()
        self.note_view = NoteView(self, model=self.note_model)

        # Connect signals to the view
        # Ask the model to refresh the data (which will emit a signal to refresh the view)
        self.refresh.connect(self.note_model.refresh)

        # Set the view as the central widget
        self.setCentralWidget(self.note_view)

    def toggle_style(self) -> None:
        """Toggle between light and dark mode"""
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                if app.palette() == self.palettes["light"]:
                    # Switch to dark mode
                    app.setPalette(self.palettes["dark"])
                    app.setProperty("darkMode", True)
                    app.setStyleSheet(QSS_STYLE)  # Reapply stylesheet to trigger update
                else:
                    # Switch to light mode
                    app.setPalette(self.palettes["light"])
                    app.setProperty("darkMode", False)
                    app.setStyleSheet(QSS_STYLE)  # Reapply stylesheet to trigger update

    @classmethod
    def get_menu_config(cls) -> MenuConfig:
        return MenuConfig(
            menus=[
                MenuStructure(
                    name="&File",
                    actions=[
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
                            id="toggle_sidebar",
                            text="Toggle &Sidebar",
                            handler="toggle_sidebar",
                            shortcut="Ctrl+B",
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
                    widget.update()

                # Trigger style refresh
                app.setStyleSheet(app.styleSheet())

    def zoom_in(self) -> None:
        """Increase the UI scale factor by 10%"""
        self.zoom(1.1)

    def zoom_out(self) -> None:
        """Decrease the UI scale factor by 10%"""
        self.zoom(0.9)

    def toggle_sidebar(self) -> None:
        """Toggle the sidebar visibility"""
        if self.note_view:
            self.note_view.toggle_sidebar()

    def show_settings(self) -> None:
        """Show the settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec()

    def show_about_dialog(self) -> None:
        QMessageBox.about(
            self, "About Draftsmith", "Draftsmith\nVersion 0.1.0\n\nA notetaking tool."
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
