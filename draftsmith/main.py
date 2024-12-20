#!/usr/bin/env python
import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
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
        
        label = QLabel(f"API URL: {api_url}", self)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

@app.command()
def main(db_path: str = "duckdb_browser.db", table_name: Optional[str] = None) -> None:
    app = QApplication(sys.argv)
    window = MainWindow(api_url="http://example.com/api")
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    app()
