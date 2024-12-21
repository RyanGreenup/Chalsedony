from PySide6.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QLabel, 
    QPushButton,
    QFontDialog,
    QApplication
)
from PySide6.QtGui import QFont

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Font selection section
        font_label = QLabel("Application Font:", self)
        layout.addWidget(font_label)
        
        font_button = QPushButton("Select Font...", self)
        font_button.clicked.connect(self.show_font_dialog)
        layout.addWidget(font_button)
        
        self.setLayout(layout)
    
    def show_font_dialog(self) -> None:
        """Show font selection dialog and apply selected font."""
        if app := QApplication.instance():
            if isinstance(app, QApplication):
                current_font = app.font()
                result = QFontDialog.getFont(current_font, self)
                if isinstance(result, tuple):  # Explicitly check if it's a tuple
                    font, ok = result
                    if ok and isinstance(font, QFont):  # Verify we have a valid QFont
                        app.setFont(font)
