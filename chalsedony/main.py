#!/usr/bin/env python
import os
import sys
from pathlib import Path
from styles import QSS_STYLE
from PySide6.QtWidgets import (
    QApplication,
)
from typing import Optional
import typer
import signal
from palettes import create_dark_palette, create_light_palette
from main_window import MainWindow


app = typer.Typer(pretty_exceptions_enable=False)


def is_system_dark_mode() -> bool:
    """Check if system prefers dark mode.

    For now, defaults to True until we implement proper system theme detection.
    """
    return True


@app.command()
def main(
    database: Path = Path(
        os.path.expanduser("~/.config/joplin-desktop/database.sqlite")
    ),
    assets: Path = Path(os.path.expanduser("~/.config/joplin-desktop/resources/")),
    dark_mode: Optional[bool] = None,
    initial_note: Optional[str] = None,
    focus_journal: Optional[bool] = True,
) -> None:
    """
    Start the application

    Args:
        dark_mode: Force dark mode on/off. If None, use system preference
        database: Path to the database file.
        assets: Path to the assets folder
        initial_note: The title of the note to open on startup (First note by update_date)
        focus_journal: Focus todays journal note on startup (default: True)
    """
    app = QApplication(sys.argv)

    # Apply the modern style sheet
    app.setStyleSheet(QSS_STYLE)

    window = MainWindow(database, assets, initial_note, focus_journal)
    window.set_style(dark_mode if dark_mode is not None else is_system_dark_mode())
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app()
