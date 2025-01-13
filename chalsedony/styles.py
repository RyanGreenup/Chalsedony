base_style = """
* {
    font-family: "Fira Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

*:focus {
    border: 2px solid palette(highlight);
}

QLineEdit {
    padding: 4px;
    /*border: 1px solid palette(mid); */
    border-radius: 4px;
    margin: 8px 8px 4px 8px;
    font-size: 13px;
    color: palette(text);
}

"""


tree_view = """

QTreeView {
    border: none;
    background: palette(base);
    padding: 8px;
    font-size: 13px;
}

QTreeView::item {
    padding: 4px;
}

QTreeView::item:hover {
    background: palette(shadow);
    padding: 8px 4px;
    border: none;
}

QTreeView::item:selected {
    background: palette(highlight);
    color: palette(highlighted-text);
    border: none;
    outline: none;
}

/* Style for the row itself to ensure continuous highlighting */
QTreeView::item:selected:active {
    background: palette(highlight);
    border: none;
    outline: none;
}

QTreeView::item:selected:!active {
    background: palette(highlight);
    border: none;
    outline: none;
}

QTreeView::item:focus {
    border: none;
    outline: none;
}

QTreeView::branch {
    background: transparent;
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
    image: url(chalsedony/icons/chevron-right.svg);
}

QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings {
    image: url(chalsedony/icons/chevron-down.svg);
}

"""


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
    background: palette(shadow);
}

"""

note_list_style = """
QListWidget {
    border: none;
    background: palette(base);
    outline: none;
    font-size: 13px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
    margin: 2px 4px;
}

QListWidget::item:selected {
    background: palette(highlight);
    color: palette(highlighted-text);
}

QListWidget::item:hover:!selected {
    background: palette(shadow);
}

QListWidget::item:focus {
    border: none;
    outline: none;
}

/* Style for first item when widget is focused but no selection */
QListWidget[focusFirstItem="true"]::item:first {
    background: palette(shadow);
    border-left: 2px solid palette(highlight);
}
"""

# Tabs must be transparent otherwise the webview will not match the background
# We are simply using the DarkMode on the web preview not CSS, so this is needed
tabs = """
QTabWidget::pane {
    border: 0;
    background: transparent;
}
QTabBar::tab {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 5px;
    margin: 2px;
    border-radius: 3px;
}
QTabBar::tab:selected {
    background: rgba(255, 255, 255, 0.2);
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

scrollbars = """

/* Scrollbar styling */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: palette(mid);
    border-radius: 4px;
    min-height: 20px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: palette(dark);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
    border: none;
}

QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical {
    background: none;
    border: none;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

/* Horizontal scrollbar */
QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 12px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: palette(mid);
    border-radius: 4px;
    min-width: 20px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background: palette(dark);
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    background: none;
    border: none;
}

QScrollBar::left-arrow:horizontal,
QScrollBar::right-arrow:horizontal {
    background: none;
    border: none;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: none;
}

/* Corner widget where scrollbars meet */
QAbstractScrollArea::corner {
    background: transparent;
    border: none;
}
"""

toolbar = """

QToolBar {
    border: none;
    background: transparent;
    spacing: 8px;
    padding: 4px;
}

QToolBar::separator {
    width: 1px;
    background: palette(mid);
    margin: 4px 8px;
}

QToolButton {
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px;
    margin: 2px;
    color: palette(button-text);
}

QToolButton:hover {
    background: palette(shadow);
    color: palette(text);
}

QToolButton:pressed {
    background: palette(dark);
}

QToolButton:checked {
    background: palette(mid);
    border: 1px solid palette(mid);
}

QToolButton:disabled {
    color: palette(disabled-text);
}

QToolButton::menu-indicator {
    image: none;
}

"""


menus = """

QMenuBar {
    border: none;
    background: transparent;
    padding: 2px;
    spacing: 4px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 8px;
    border-radius: 4px;
    color: palette(text);
}

QMenuBar::item:selected {
    background: palette(shadow);
    color: palette(text);
}

QMenuBar::item:pressed {
    background: palette(dark);
    color: palette(text);
}

QMenu {
    background: palette(window);
    border: 1px solid palette(shadow);
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 32px 6px 24px;
    border-radius: 4px;
    margin: 2px 4px;
    color: palette(text);
}

QMenu::item:selected {
    background: palette(shadow);
    color: palette(text);
}

QMenu::separator {
    height: 1px;
    background: palette(shadow);
    margin: 4px 8px;
}

QMenu::indicator {
    width: 16px;
    height: 16px;
    left: 6px;
}

QMenu::icon {
    padding-left: 4px;
}

QMenu QMenu {
    border: 1px solid palette(shadow);
    border-radius: 6px;
}

QMenu::item:disabled {
    color: palette(disabled-text);
}

"""


labels = """

QLabel {
    font-size: 13px;
    padding: 2px;
}

/* For section headers or group titles */
QLabel[heading="true"] {
    font-size: 14px;
    font-weight: bold;
    padding: 8px 0px;
}

/* For smaller helper/hint text */
QLabel[hint="true"] {
    font-size: 12px;
    color: palette(disabled-text);
}

/* For error messages */
QLabel[error="true"] {
    color: #dc3545;
}

/* For success messages */
QLabel[success="true"] {
    color: #28a745;
}

/* For labels that act as links */
QLabel[link="true"] {
    color: palette(highlight);
}

QLabel[link="true"]:hover {
    text-decoration: underline;
}

"""

override_text_edit_background = """
    MDTextEdit { background: palette(window); }
"""

# QSS_STYLE = command_palette_style + buttons + settings_dialog + tree_view + scrollbars + labels + toolbar + menus
QSS_STYLE = (
    base_style
    + command_palette_style
    + buttons
    + settings_dialog
    + tree_view
    + scrollbars
    + labels
    + toolbar
    + menus
    + override_text_edit_background
    + note_list_style
    + tabs
)
