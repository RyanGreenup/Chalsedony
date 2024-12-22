from PySide6.QtCore import Qt

QSS_STYLE = """
QListView, QTreeView {
    background-color: transparent;
    border: none;
    padding: 8px;
}

QListView::item, QTreeView::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 4px;
    color: #475569;  /* slate-600 */
}

QListView::item:hover, QTreeView::item:hover {
    background-color: #f1f5f9;  /* slate-100 */
}

QListView::item:selected, QTreeView::item:selected {
    background-color: #e2e8f0;  /* slate-200 */
    color: #1e293b;  /* slate-800 */
    border: 1px solid #cbd5e1;  /* slate-300 */
}

/* Dark mode overrides using palette */
QListView::item, QTreeView::item {
    color: #e2e8f0;  /* slate-200 */
}

QListView[darkMode="true"]::item:hover, 
QTreeView[darkMode="true"]::item:hover {
    background-color: #334155;  /* slate-700 */
}

QListView[darkMode="true"]::item:selected, 
QTreeView[darkMode="true"]::item:selected {
    background-color: #1e293b;  /* slate-800 */
    color: #f1f5f9;  /* slate-100 */
    border: 1px solid #475569;  /* slate-600 */
}

QTreeView::branch {
    background-color: transparent;
}

QTreeView::branch:has-siblings:!adjoins-item {
    border-image: none;
    image: none;
}

QTreeView::branch:has-siblings:adjoins-item {
    border-image: none;
    image: none;
}

QTreeView::branch:!has-children:!has-siblings:adjoins-item {
    border-image: none;
    image: none;
}

QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {
    image: url(icons/chevron-right.svg);
}

QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings {
    image: url(icons/chevron-down.svg);
}

QSplitter::handle {
    background-color: #334155;  /* slate-700 */
    width: 1px;
}

QScrollBar:vertical {
    border: none;
    background-color: #1e293b;  /* slate-800 */
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #475569;  /* slate-600 */
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #64748b;  /* slate-500 */
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

/* Additional modern styling for the command palette and selection dialogs */
QLineEdit {
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid #cbd5e1;  /* slate-300 */
    background-color: white;
    margin: 4px 0;
}

QLineEdit:focus {
    border-color: #3b82f6;  /* blue-500 */
    outline: none;
}

QLineEdit[darkMode="true"] {
    background-color: #1e293b;  /* slate-800 */
    border-color: #475569;  /* slate-600 */
    color: #f1f5f9;  /* slate-100 */
}

QLineEdit[darkMode="true"]:focus {
    border-color: #60a5fa;  /* blue-400 */
}

/* Modern dialog styling */
QDialog {
    background-color: white;
}

QDialog[darkMode="true"] {
    background-color: #0f172a;  /* slate-900 */
}

/* Button styling */
QPushButton {
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #cbd5e1;  /* slate-300 */
    background-color: white;
    color: #475569;  /* slate-600 */
}

QPushButton:hover {
    background-color: #f1f5f9;  /* slate-100 */
}

QPushButton:pressed {
    background-color: #e2e8f0;  /* slate-200 */
}

QPushButton[darkMode="true"] {
    background-color: #1e293b;  /* slate-800 */
    border-color: #475569;  /* slate-600 */
    color: #f1f5f9;  /* slate-100 */
}

QPushButton[darkMode="true"]:hover {
    background-color: #334155;  /* slate-700 */
}

QPushButton[darkMode="true"]:pressed {
    background-color: #0f172a;  /* slate-900 */
}
"""
