import sys
from typing import NamedTuple
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit
from PySide6.QtGui import (
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
    QFont,
    QTextDocument,
)
from PySide6.QtCore import QRegularExpression


class HighlightRule(NamedTuple):
    pattern: QRegularExpression
    format: QTextCharFormat


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument):
        super(MarkdownHighlighter, self).__init__(document)
        self.highlightingRules: list[HighlightRule] = []

        # Header
        headerFormat = QTextCharFormat()
        headerFormat.setForeground(QColor("blue"))
        headerFormat.setFontWeight(QFont.Weight.Bold)
        self.highlightingRules.append(
            HighlightRule(QRegularExpression(r"^(#{1,6})\s.*"), headerFormat)
        )

        # Bold
        boldFormat = QTextCharFormat()
        boldFormat.setForeground(QColor("darkRed"))
        boldFormat.setFontWeight(QFont.Weight.Bold)
        self.highlightingRules.append(
            HighlightRule(QRegularExpression(r"\*\*(.+?)\*\*"), boldFormat)
        )

        # Italic
        italicFormat = QTextCharFormat()
        italicFormat.setForeground(QColor("darkGreen"))
        italicFormat.setFontItalic(True)
        self.highlightingRules.append(
            HighlightRule(QRegularExpression(r"\*(.+?)\*"), italicFormat)
        )

    def highlightBlock(self, text: str) -> None:
        """Highlight a block of text using the defined rules."""
        for rule in self.highlightingRules:
            expression = rule.pattern
            expression = pattern
            index = expression.globalMatch(text)
            while index.hasNext():
                match = index.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, rule.format)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Markdown Syntax Highlighter")

        textEdit = QTextEdit()
        self.setCentralWidget(textEdit)

        self.highlighter = MarkdownHighlighter(textEdit.document())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
