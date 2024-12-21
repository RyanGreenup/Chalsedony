#!/usr/bin/env python
import sys
from PySide6.QtGui import QAction, QPalette, QColor
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
        self.menu_actions = {}
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()

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
            self,
            "About Draftsmith",
            "Draftsmith\nVersion 0.1.0\n\nA notetaking tool."
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
                        if (handler := getattr(self, action_item.handler, None)):
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
    
    # Set window and widget background colors
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    
    # Set text colors
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    
    # Set highlight colors
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    
    # Set disabled colors
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    
    # Set tooltip colors
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.black)
    
    return palette


class MainWindow(BaseWindowWithMenus):
    def __init__(self, api_url: str):
        super().__init__()
        self.setWindowTitle("Draftsmith")
        self.setGeometry(100, 100, 800, 600)

        label = QLabel(f"API URL: {api_url}", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)


@app.command()
def main(db_path: str = "duckdb_browser.db", table_name: Optional[str] = None) -> None:
    app = QApplication(sys.argv)
    
    # Apply dark palette to the application
    app.setPalette(create_dark_palette())
    
    # Add custom stylesheet
    app.setStyleSheet("""
        QToolTip { 
            color: #ffffff; 
            background-color: #2a82da; 
            border: 1px solid white; 
        }
        QMenuBar {
            background-color: #353535;
            color: white;
        }
        QMenuBar::item:selected {
            background-color: #2a82da;
        }
        QMenu {
            background-color: #353535;
            color: white;
        }
        QMenu::item:selected {
            background-color: #2a82da;
        }
        QStatusBar {
            background-color: #353535;
            color: white;
        }
    """)
    
    window = MainWindow(api_url="http://example.com/api")
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app()
