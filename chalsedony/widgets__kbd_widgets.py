from PySide6.QtWidgets import QListWidget, QWidget


class KbdListWidget(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
