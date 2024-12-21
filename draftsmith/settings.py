from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        
        layout = QVBoxLayout()
        # For now just add a placeholder label
        layout.addWidget(QLabel("Settings window (under construction)"))
        
        self.setLayout(layout)
