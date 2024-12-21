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
from typing import Optional
import typer
import signal


app = typer.Typer(pretty_exceptions_enable=False)


class MainWindow(QMainWindow):
    def __init__(self, api_url: str):
        super().__init__()
        self.setWindowTitle("Draftsmith")
        self.setGeometry(100, 100, 800, 600)

        self.create_menu_bar()
        self.create_tool_bar()
        self.create_status_bar()

        label = QLabel(f"API URL: {api_url}", self)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # File Menu
        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menu_bar.addMenu("Edit")
        # Add more actions to the Edit menu if needed

    def create_tool_bar(self):
        tool_bar = QToolBar("Main Toolbar", self)
        self.addToolBar(tool_bar)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        tool_bar.addAction(exit_action)

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
