#!/usr/bin/env python
import sys
from PySide6.QtGui import QAction, QPalette, QColor, QPalette
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
        self.default_palette = style.standardPalette()
        self.dark_palette = create_dark_palette()
        self.menu_actions = {}
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()

    def toggle_style(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        # Cast to QApplication to satisfy type checker
        app = QApplication.instance()
        assert isinstance(app, QApplication)
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


def create_light_palette() -> QPalette:
    palette = QPalette()

    colors = {
        "Rosewater": {
            "Hex": "#f4dbd6",
        },
        "Flamingo": {
            "Hex": "#f0c6c6",
        },
        "Pink": {
            "Hex": "#f5bde6",
        },
        "Mauve": {
            "Hex": "#c6a0f6",
        },
        "Red": {
            "Hex": "#ed8796",
        },
        "Maroon": {
            "Hex": "#ee99a0",
        },
        "Peach": {
            "Hex": "#f5a97f",
        },
        "Yellow": {
            "Hex": "#eed49f",
        },
        "Green": {
            "Hex": "#a6da95",
        },
        "Teal": {
            "Hex": "#8bd5ca",
        },
        "Sky": {
            "Hex": "#91d7e3",
        },
        "Sapphire": {
            "Hex": "#7dc4e4",
        },
        "Blue": {
            "Hex": "#8aadf4",
        },
        "Lavender": {
            "Hex": "#b7bdf8",
        },
        "Text": {
            "Hex": "#cad3f5",
        },
        "Subtext 1": {
            "Hex": "#b8c0e0",
        },
        "Subtext 0": {
            "Hex": "#a5adcb",
        },
        "Overlay 2": {
            "Hex": "#939ab7",
        },
        "Overlay 1": {
            "Hex": "#8087a2",
        },
        "Overlay 0": {
            "Hex": "#6e738d",
        },
        "Surface 2": {
            "Hex": "#5b6078",
        },
        "Surface 1": {
            "Hex": "#494d64",
        },
        "Surface 0": {
            "Hex": "#363a4f",
        },
        "Base": {
            "Hex": "#24273a",
        },
        "Mantle": {
            "Hex": "#1e2030",
        },
        "Crust": {
            "Hex": "#181926",
        },
    }

    # Set the palette colors
    palette.setColor(QPalette.ColorRole.Window, QColor(colors["Base"]["Hex"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["Overlay 0"]["Hex"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["Overlay 1"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["Subtext 0"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["Surface 1"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["Red"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(colors["Blue"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["Sapphire"]["Hex"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["Text"]["Hex"]))

    return palette


def create_other_light_palette() -> QPalette:
    palette = QPalette()

    colors = {
        "Rosewater": {
            "Hex": "#dc8a78",
        },
        "Flamingo": {
            "Hex": "#dd7878",
        },
        "Pink": {
            "Hex": "#ea76cb",
        },
        "Mauve": {
            "Hex": "#8839ef",
        },
        "Red": {
            "Hex": "#d20f39",
        },
        "Maroon": {
            "Hex": "#e64553",
        },
        "Peach": {
            "Hex": "#fe640b",
        },
        "Yellow": {
            "Hex": "#df8e1d",
        },
        "Green": {
            "Hex": "#40a02b",
        },
        "Teal": {
            "Hex": "#179299",
        },
        "Sky": {
            "Hex": "#04a5e5",
        },
        "Sapphire": {
            "Hex": "#209fb5",
        },
        "Blue": {
            "Hex": "#1e66f5",
        },
        "Lavender": {
            "Hex": "#7287fd",
        },
        "Text": {
            "Hex": "#4c4f69",
        },
        "Subtext 1": {
            "Hex": "#5c5f77",
        },
        "Subtext 0": {
            "Hex": "#6c6f85",
        },
        "Overlay 2": {
            "Hex": "#7c7f93",
        },
        "Overlay 1": {
            "Hex": "#8c8fa1",
        },
        "Overlay 0": {
            "Hex": "#9ca0b0",
        },
        "Surface 2": {
            "Hex": "#acb0be",
        },
        "Surface 1": {
            "Hex": "#bcc0cc",
        },
        "Surface 0": {
            "Hex": "#ccd0da",
        },
        "Base": {
            "Hex": "#eff1f5",
        },
        "Mantle": {
            "Hex": "#e6e9ef",
        },
        "Crust": {
            "Hex": "#dce0e8",
        },
    }

    # Set the palette colors for dark theme
    palette.setColor(QPalette.ColorRole.Window, QColor(colors["Crust"]["Hex"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["Surface 0"]["Hex"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["Surface 1"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["Surface 2"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["Subtext 0"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["Overlay 1"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["Red"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(colors["Blue"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["Sapphire"]["Hex"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["Surface 0"]["Hex"]))

    return palette


def create_dark_palette() -> QPalette:
    palette = QPalette()

    colors = {
        "Rosewater": {
            "Hex": "#f5e0dc",
        },
        "Flamingo": {
            "Hex": "#f2cdcd",
        },
        "Pink": {
            "Hex": "#f5c2e7",
        },
        "Mauve": {
            "Hex": "#cba6f7",
        },
        "Red": {
            "Hex": "#f38ba8",
        },
        "Maroon": {
            "Hex": "#eba0ac",
        },
        "Peach": {
            "Hex": "#fab387",
        },
        "Yellow": {
            "Hex": "#f9e2af",
        },
        "Green": {
            "Hex": "#a6e3a1",
        },
        "Teal": {
            "Hex": "#94e2d5",
        },
        "Sky": {
            "Hex": "#89dceb",
        },
        "Sapphire": {
            "Hex": "#74c7ec",
        },
        "Blue": {
            "Hex": "#89b4fa",
        },
        "Lavender": {
            "Hex": "#b4befe",
        },
        "Text": {
            "Hex": "#cdd6f4",
        },
        "Subtext 1": {
            "Hex": "#bac2de",
        },
        "Subtext 0": {
            "Hex": "#a6adc8",
        },
        "Overlay 2": {
            "Hex": "#9399b2",
        },
        "Overlay 1": {
            "Hex": "#7f849c",
        },
        "Overlay 0": {
            "Hex": "#6c7086",
        },
        "Surface 2": {
            "Hex": "#585b70",
        },
        "Surface 1": {
            "Hex": "#45475a",
        },
        "Surface 0": {
            "Hex": "#313244",
        },
        "Base": {
            "Hex": "#1e1e2e",
        },
        "Mantle": {
            "Hex": "#181825",
        },
        "Crust": {
            "Hex": "#11111b",
        },
    }

    # Set the palette colors for a mocha theme
    palette.setColor(QPalette.Window, QColor(colors["Base"]["Hex"]))
    palette.setColor(QPalette.WindowText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.Base, QColor(colors["Mantle"]["Hex"]))
    palette.setColor(QPalette.AlternateBase, QColor(colors["Crust"]["Hex"]))
    palette.setColor(QPalette.ToolTipBase, QColor(colors["Surface 0"]["Hex"]))
    palette.setColor(QPalette.ToolTipText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.Text, QColor(colors["Subtext 0"]["Hex"]))
    palette.setColor(QPalette.Button, QColor(colors["Overlay 1"]["Hex"]))
    palette.setColor(QPalette.ButtonText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.BrightText, QColor(colors["Rosewater"]["Hex"]))
    palette.setColor(QPalette.Link, QColor(colors["Blue"]["Hex"]))
    palette.setColor(QPalette.Highlight, QColor(colors["Sapphire"]["Hex"]))
    palette.setColor(QPalette.HighlightedText, QColor(colors["Base"]["Hex"]))

    return palette


class MainWindow(BaseWindowWithMenus):
    def __init__(self, api_url: str) -> None:
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
        app.setPalette(create_light_palette())

    window = MainWindow(api_url="http://example.com/api")
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app()
