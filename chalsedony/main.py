#!/usr/bin/env python
import os
import sys
from pathlib import Path
from .styles import QSS_STYLE
from PySide6.QtWidgets import (
    QApplication,
)
import typer
import signal
from .main_window import MainWindow
import sqlite3


app = typer.Typer(pretty_exceptions_enable=False)


def is_system_dark_mode() -> bool:
    """Check if system prefers dark mode.

    For now, defaults to True until we implement proper system theme detection.
    """
    return True


@app.command()
def main(
    database: Path | None = None,
    assets: Path | None = None,
    dark_mode: bool | None = None,
    initial_note: str | None = None,
    focus_journal: bool | None = True,
) -> None:
    """
    Start the application

    Args:
        dark_mode: Force dark mode on/off. If None, use system preference
        database: Path to the database file. If None, uses default location (Joplin)
        assets: Path to the assets folder. If None, uses default location (Joplin)
        initial_note: The title of the note to open on startup (First note by update_date)
        focus_journal: Focus todays journal note on startup (default: True)
    """
    # Set default paths if not provided
    database = database or Path(
        os.path.expanduser("~/.config/joplin-desktop/database.sqlite")
    )
    assets = assets or Path(os.path.expanduser("~/.config/joplin-desktop/resources/"))

    app = QApplication(sys.argv)

    if not database.exists():
        create_database(database)
    if not database.exists():
        raise FileNotFoundError(f"Database file not found: {database}")
    if not assets.exists():
        # Make the directory
        assets.mkdir(parents=True, exist_ok=True)

    # Apply the modern style sheet
    app.setStyleSheet(QSS_STYLE)

    window = MainWindow(database, assets, initial_note, focus_journal)
    window.set_style(dark_mode if dark_mode is not None else is_system_dark_mode())
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


def create_database(path: Path) -> None:
    from .init_db import init_joplin_db

    with sqlite3.connect(path) as conn:
        conn.executescript(init_joplin_db())
        conn.commit()
        conn.executescript("""PRAGMA journal_mode = 'WAL';""")
        conn.executescript("""PRAGMA cache_size = -64000""")
        conn.commit()


if __name__ == "__main__":
    app()
