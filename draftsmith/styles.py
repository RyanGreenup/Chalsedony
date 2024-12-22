from PySide6.QtCore import Qt

MODERN_STYLE = """
QTreeView {
    background-color: #1e293b;  /* slate-800 */
    border: none;
    padding: 8px;
}

QTreeView::item {
    padding: 6px;
    border-radius: 4px;
    margin: 2px 4px;
}

QTreeView::item:hover {
    background-color: #334155;  /* slate-700 */
}

QTreeView::item:selected {
    background-color: #3b82f6;  /* blue-500 */
    color: white;
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
"""
