#!/usr/bin/env python
import sys
from PySide6.QtGui import QAction, QPalette, QColor
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QMenuBar,
    QToolBar,
    QStatusBar,
    QMessageBox,
)
from PySide6.QtCore import Qt
from typing import Optional, List, Dict
from pydantic import BaseModel
import typer
import signal


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


class BaseWindowWithMenus(QMainWindow):
    menu_actions: Dict[str, QAction]

    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("No QApplication instance found")
        self.default_palette = app.style().standardPalette()
        self.dark_palette = create_dark_palette()
        self.menu_actions = {}
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()

    def toggle_style(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        if app.palette() == self.default_palette:
            app.setPalette(self.dark_palette)
        else:
            app.setPalette(self.default_palette)

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


def create_dark_palette() -> QPalette:
    palette = QPalette()

    # Base colors
    base_dark = QColor(35, 35, 35)
    widget_dark = QColor(53, 53, 53)
    highlight = QColor(42, 130, 218)
    disabled_gray = QColor(127, 127, 127)

    # Window and base
    palette.setColor(QPalette.ColorRole.Window, widget_dark)
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, base_dark)
    palette.setColor(QPalette.ColorRole.AlternateBase, widget_dark)

    # Text and buttons
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, widget_dark)
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)

    # Selection and highlights
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)

    # Menu specific (replaces QSS)
    palette.setColor(QPalette.ColorRole.Light, widget_dark)  # For menu borders
    palette.setColor(QPalette.ColorRole.Mid, widget_dark)  # For menu separators
    palette.setColor(QPalette.ColorRole.Dark, base_dark)  # For pressed states

    # Tooltips
    palette.setColor(QPalette.ColorRole.ToolTipBase, highlight)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)

    # Disabled state
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_gray
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_gray
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_gray
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(80, 80, 80)
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, disabled_gray
    )

    return palette


class MainWindow(BaseWindowWithMenus):
    def __init__(self, api_url: str):
        super().__init__()
        self.setWindowTitle("Draftsmith")
        self.setGeometry(100, 100, 800, 600)

        label = QLabel(f"API URL: {api_url}", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)


def is_system_dark_mode() -> bool:
    """Check if system prefers dark mode.

    For now, defaults to True until we implement proper system theme detection.
    """
    return True


@app.command()
def main(
    db_path: str = "duckdb_browser.db",
    table_name: Optional[str] = None,
    dark_mode: Optional[bool] = None,
) -> None:
    """
    Start the application

    Args:
        db_path: Path to the database file
        table_name: Optional table name to open
        dark_mode: Force dark mode on/off. If None, use system preference
    """
    app = QApplication(sys.argv)

    # Determine dark mode setting
    use_dark = dark_mode if dark_mode is not None else is_system_dark_mode()

    # Set the appropriate palette
    if use_dark:
        app.setPalette(create_dark_palette())
    else:
        app.setPalette(app.style().standardPalette())

    window = MainWindow(api_url="http://example.com/api")
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app()
