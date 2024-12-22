from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFontDialog,
    QApplication,
    QWidget,
    QDialogButtonBox,
    QGroupBox,
)
from PySide6.QtGui import QFont


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(500, 400)  # Set a reasonable default size

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)

        # Appearance section
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout()

        # Font settings
        font_layout = QHBoxLayout()
        font_label = QLabel("Application Font:")
        self.font_preview = QLabel("Preview text")
        self.font_preview.setMinimumWidth(200)
        self.update_font_preview()

        font_button = QPushButton("Change...")
        font_button.setMaximumWidth(100)
        font_button.clicked.connect(self.show_font_dialog)

        font_layout.addWidget(font_label)
        font_layout.addWidget(self.font_preview)
        font_layout.addWidget(font_button)
        appearance_layout.addLayout(font_layout)

        appearance_group.setLayout(appearance_layout)
        main_layout.addWidget(appearance_group)

        # Add spacer
        main_layout.addStretch()

        # Standard dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def update_font_preview(self) -> None:
        """Update the font preview label with current application font"""
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                current_font = app.font()
                self.font_preview.setFont(current_font)
                self.font_preview.setText(
                    f"{current_font.family()}, {current_font.pointSize()}pt"
                )

    def show_font_dialog(self) -> None:
        """Show font selection dialog and apply selected font."""
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                current_font = app.font()
                result = QFontDialog.getFont(current_font, self)
                if isinstance(result, tuple):
                    font, ok = result
                    if ok and isinstance(font, QFont):
                        app.setFont(font)
                        self.update_font_preview()
