#!/usr/bin/env python
import sys
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
    dark_mode: Optional[bool] = None,
) -> None:
    """
    Start the application

    Args:
        dark_mode: Force dark mode on/off. If None, use system preference
    """
    app = QApplication(sys.argv)

    # Determine dark mode setting
    use_dark = dark_mode if dark_mode is not None else is_system_dark_mode()

    # Set the appropriate palette and dark mode property
    if use_dark:
        app.setPalette(create_dark_palette())
        app.setProperty("darkMode", True)
    else:
        app.setPalette(create_light_palette())
        app.setProperty("darkMode", False)

    # Apply the modern style sheet
    app.setStyleSheet(QSS_STYLE)

    window = MainWindow()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app()
