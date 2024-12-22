from PySide6.QtCore import Qt



command_palette_style = """

SelectionDialog {
    border: 1px solid palette(mid);
    border-radius: 8px;
}

SelectionDialog QLineEdit {
    padding: 8px;
    border: 1px solid palette(mid);
    border-radius: 4px;
    margin: 8px 8px 4px 8px;
    font-size: 13px;
}

SelectionDialog QListWidget {
    border: none;
    margin: 0px 8px 8px 8px;
    outline: none;
    font-size: 13px;
}

SelectionDialog QListWidget::item {
    padding: 6px;
    border-radius: 4px;
}

SelectionDialog QListWidget::item:selected {
    background: palette(highlight);
    color: palette(highlighted-text);
}

SelectionDialog QListWidget::item:hover:!selected {
    background: palette(mid);
}

"""


buttons = """

QPushButton {
    padding: 6px 16px;
    border-radius: 4px;
    border: 1px solid palette(mid);
    background: palette(button);
    min-height: 24px;
    font-size: 13px;
}

QPushButton:hover {
    background: palette(light);
    border-color: palette(mid);
}

QPushButton:pressed {
    background: palette(dark);
}

QPushButton:disabled {
    background: palette(window);
    border-color: palette(mid);
    color: palette(disabled-text);
}

QPushButton:default {
    border-width: 2px;
    border-color: palette(highlight);
}

QPushButton:focus {
    border-color: palette(highlight);
    outline: none;
}

/* Style for primary action buttons */
QPushButton[primary="true"] {
    background: palette(highlight);
    color: palette(highlighted-text);
    border-color: palette(highlight);
}

QPushButton[primary="true"]:hover {
    background: palette(highlight);
    border-color: palette(dark);
}

QPushButton[primary="true"]:pressed {
    background: palette(dark);
    border-color: palette(shadow);
}

QPushButton[primary="true"]:disabled {
    background: palette(mid);
    border-color: palette(mid);
    color: palette(disabled-text);
}

"""



settings_dialog = """

QDialog {
    background: palette(window);
}

QGroupBox {
    font-weight: bold;
    border: none;
    margin-top: 16px;
    padding-top: 16px;
}

QGroupBox::title {
    padding: 0px 8px;
}

/* Settings specific button styling */
QDialog QPushButton {
    min-width: 80px;
}

QDialog QLabel {
    font-size: 13px;
}

/* Font preview styling */
QDialog QLabel[frameStyle="48"] {  /* For the font preview specifically */
    padding: 8px;
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 4px;
}

/* Dialog button box styling */
QDialogButtonBox {
    border-top: 1px solid palette(mid);
    padding-top: 16px;
}

"""

QSS_STYLE = command_palette_style + buttons + settings_dialog
