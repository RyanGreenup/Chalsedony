#!/usr/bin/env python
import sys
from PySide6.QtWidgets import (
    QApplication,
)
from typing import Optional
import typer
import signal

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(db_path: str = "duckdb_browser.db", table_name: Optional[str] = None) -> None:
    app = QApplication(sys.argv)
    window = MainWindow(api_url)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app()

