from PySide6.QtCore import Qt

QSS_STYLE = """
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
