import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit
from PySide6.QtGui import (
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
    QFont,
    QTextDocument,
)
from PySide6.QtCore import QRegularExpression


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument):
        super(MarkdownHighlighter, self).__init__(document)
        self.highlightingRules = []

        # Header
        headerFormat = QTextCharFormat()
        headerFormat.setForeground(QColor("blue"))
        headerFormat.setFontWeight(QFont.Weight.Bold)
        # Create a named tuple to represent the pattern and format AI!
        tuple = (QRegularExpression(r"^(#{1,6})\s.*"), headerFormat)
        self.highlightingRules.append(tuple)

        # Bold
        boldFormat = QTextCharFormat()
        boldFormat.setForeground(QColor("darkRed"))
        boldFormat.setFontWeight(QFont.Weight.Bold)
        self.highlightingRules.append(
            (QRegularExpression(r"\*\*(.+?)\*\*"), boldFormat)
        )

        # Italic
        italicFormat = QTextCharFormat()
        italicFormat.setForeground(QColor("darkGreen"))
        italicFormat.setFontItalic(True)
        self.highlightingRules.append((QRegularExpression(r"\*(.+?)\*"), italicFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = pattern
            index = expression.globalMatch(text)
            while index.hasNext():
                match = index.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, format)


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
