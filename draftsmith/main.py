#!/usr/bin/env python
import sys
from PySide6.QtGui import QAction, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QMainWindow,
    QLabel,
    QMenuBar,
    QToolBar,
    QStatusBar,
    QMessageBox,
)
from PySide6.QtCore import Qt
from typing import Optional, List, Dict, TypedDict
from pydantic import BaseModel
import typer
import signal
from palettes import create_dark_palette, create_light_palette


app = typer.Typer(pretty_exceptions_enable=False)


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

    def __init__(self, api_url: str) -> None:
        super().__init__()
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("No QApplication instance found")
        # Cast to QApplication to satisfy type checker
        app = QApplication.instance()
        assert isinstance(app, QApplication)
        style = app.style()
        assert isinstance(style, QStyle)
        self.default_palette = style.standardPalette()
        self.dark_palette = create_dark_palette()
        self.palettes = ApplicationPalettes(
            default=create_dark_palette(),
            dark=create_dark_palette(),
            light=create_light_palette(),
        )
        self.menu_actions = {}
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()

        self.setWindowTitle("Draftsmith")
        self.setGeometry(100, 100, 800, 600)

        label = QLabel(f"API URL: {api_url}", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)

    def toggle_style(self) -> None:
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                if app.palette() == self.palettes["light"]:
                    app.setPalette(self.palettes["dark"])
                else:
                    app.setPalette(self.palettes["light"])

    @classmethod
    def get_menu_config(cls) -> MenuConfig:
        return MenuConfig(
            menus=[
                MenuStructure(
                    name="&File",
                    actions=[
                        MenuAction(
                            id="exit",
                            text="E&xit",
                            handler="close",
                        ),
                    ],
                ),
                MenuStructure(
                    name="&View",
                    actions=[
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
                            shortcut="Ctrl++",
                        ),
                        MenuAction(
                            id="zoom_out",
                            text="Zoom &Out",
                            handler="zoom_out",
                            shortcut="Ctrl+-",
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
                current_font = app.font()
                current_size = current_font.pointSize()
                if current_size <= 0:  # If point size is invalid, start from a reasonable size
                    current_size = 10
                    current_font.setPointSize(current_size)  # Set the base size first
                new_size = max(6, round(current_size * factor))  # Ensure we don't go below 6pt
                current_font.setPointSize(new_size)
                app.setFont(current_font)

    def zoom_in(self) -> None:
        """Increase the UI scale factor by 10%"""
        self.zoom(1.1)

    def zoom_out(self) -> None:
        """Decrease the UI scale factor by 10%"""
        self.zoom(0.9)

    def show_about_dialog(self) -> None:
        QMessageBox.about(
            self, "About Draftsmith", "Draftsmith\nVersion 0.1.0\n\nA notetaking tool."
        )

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


def is_system_dark_mode() -> bool:
    """Check if system prefers dark mode.

    For now, defaults to True until we implement proper system theme detection.
    """
    return True


@app.command()
def main(
    dark_mode: Optional[bool] = None,
) -> None:
    """
    Start the application

    Args:
        dark_mode: Force dark mode on/off. If None, use system preference
    """
    app = QApplication(sys.argv)

    # Determine dark mode setting
    use_dark = dark_mode if dark_mode is not None else is_system_dark_mode()

    # Set the appropriate palette
    if use_dark:
        app.setPalette(create_dark_palette())
    else:
        app.setPalette(create_light_palette())

    window = MainWindow(api_url="http://example.com/api")
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app()
