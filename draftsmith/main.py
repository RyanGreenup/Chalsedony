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
from PySide6.QtCore import Qt  # Import Qt and Alignment
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


class MainWindow(QMainWindow):
    menu_actions: Dict[str, QAction]  # Renamed from 'actions' to 'menu_actions'

    def __init__(self, api_url: str):
        super().__init__()
        self.menu_actions = {}  # Initialize with new name
        self.setWindowTitle("Draftsmith")
        self.setGeometry(100, 100, 800, 600)

        # Create menu bar first so actions are available
        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()

        label = QLabel(f"API URL: {api_url}", self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)

    @classmethod
    def get_menu_config(cls) -> MenuConfig:
        return MenuConfig(
            menus=[
                MenuStructure(
                    name="&File",
                    actions=[
                        MenuAction(
                            id="exit",  # Stable identifier
                            text="E&xit",  # Display text with accelerator
                            handler="close",
                        ),
                    ],
                ),
                MenuStructure(
                    name="&Edit",
                    actions=[
                        # Add more actions as needed
                    ],
                ),
            ]
        )

    def create_menu_bar(self) -> None:
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        menu_config = self.get_menu_config()
        self.menu_actions = {}  # Use new name

        for menu_struct in menu_config.menus:
            menu = menu_bar.addMenu(menu_struct.name)  # Qt handles & automatically
            for action_item in menu_struct.actions:
                # Create action with display text
                action = QAction(action_item.text, self)
                if action_item.shortcut:
                    action.setShortcut(action_item.shortcut)

                # call self.close
                if (handler := getattr(self, action_item.handler, None)):
                    action.triggered.connect(handler)

                # Store using stable ID
                menu.addAction(action)
                self.menu_actions[action_item.id] = action

    def create_tool_bar(self) -> None:
        tool_bar = QToolBar("Main Toolbar", self)
        self.addToolBar(tool_bar)

        # Reuse actions from menu using stable ID
        exit_action = self.menu_actions.get("exit")  # Use ID instead of display text
        if exit_action is not None:
            tool_bar.addAction(exit_action)

    def create_status_bar(self) -> None:
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
