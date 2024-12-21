#!/usr/bin/env python
import sys
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QMenuBar,
    QToolBar,
    QStatusBar,
)
from PySide6.QtCore import Qt  # Import Qt from PySide6.QtCore
from typing import Optional, List
from pydantic import BaseModel
import typer
import signal


app = typer.Typer(pretty_exceptions_enable=False)


class MenuAction(BaseModel):
    name: str
    handler: str = "close"  # default handler
    shortcut: str = ""


class MenuStructure(BaseModel):
    name: str
    actions: List[MenuAction]


class MenuConfig(BaseModel):
    menus: List[MenuStructure]


class MainWindow(QMainWindow):
    def __init__(self, api_url: str):
        super().__init__()
        self.setWindowTitle("Draftsmith")
        self.setGeometry(100, 100, 800, 600)

        # Create menu bar first so actions are available
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()

        label = QLabel(f"API URL: {api_url}", self)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

    @classmethod
    def get_menu_config(cls) -> MenuConfig:
        return MenuConfig(
            menus=[
                MenuStructure(
                    name="File",
                    actions=[
                        MenuAction(name="Exit", handler="close"),
                    ],
                ),
                MenuStructure(
                    name="Edit",
                    actions=[
                        # Add more actions as needed
                    ],
                ),
            ]
        )

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        menu_config = self.get_menu_config()
        self.actions = {}  # Store actions for reuse

        for menu_struct in menu_config.menus:
            menu = menu_bar.addMenu(menu_struct.name)
            for action_item in menu_struct.actions:
                action = QAction(action_item.name, self)
                if action_item.shortcut:
                    action.setShortcut(action_item.shortcut)
                # Get the handler method by name using getattr
                handler = getattr(self, action_item.handler, None)
                if handler:
                    action.triggered.connect(handler)
                menu.addAction(action)
                self.actions[action_item.name] = action

    def create_tool_bar(self):
        tool_bar = QToolBar("Main Toolbar", self)
        self.addToolBar(tool_bar)

        # Reuse actions from menu
        if "Exit" in self.actions:
            tool_bar.addAction(self.actions["Exit"])

    def create_status_bar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Ready")


@app.command()
def main(db_path: str = "duckdb_browser.db", table_name: Optional[str] = None) -> None:
    app = QApplication(sys.argv)
    window = MainWindow(api_url="http://example.com/api")
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app()
