import sys
from typing import NamedTuple, final, override, Optional
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit
from PySide6.QtGui import (
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
    QFont,
    QTextDocument,
)
from PySide6.QtCore import QRegularExpression

BLUE =  "#89b4fa"


class HighlightRule(NamedTuple):
    pattern: QRegularExpression
    format: QTextCharFormat
    level: int = 0  # 0 means not a header rule


class MarkdownHighlighter(QSyntaxHighlighter):
    # Block state constants
    STATE_NORMAL = 0
    STATE_CODE_BLOCK = 1
    STATE_LATEX_BLOCK = 2

    def __init__(self, document: QTextDocument):
        super(MarkdownHighlighter, self).__init__(document)
        self.highlightingRules: list[HighlightRule] = []

        # Set default document font to Fira Sans
        default_font = document.defaultFont()
        default_font.setFamily("Fira Sans")
        document.setDefaultFont(default_font)

        # Code block formats
        self.codeFormat = QTextCharFormat()
        self.codeFormat.setFontFamily("Fira Code")

        self.codeFenceFormat = QTextCharFormat()
        self.codeFenceFormat.setForeground(QColor("green"))
        self.codeFenceFormat.setFontWeight(QFont.Weight.Bold)

        # LaTeX block formats
        self.latexFormat = QTextCharFormat()
        self.latexFormat.setFontFamily("Fira Code")

        self.latexFenceFormat = QTextCharFormat()
        self.latexFenceFormat.setFontWeight(QFont.Weight.Bold)

        # Get base font size from document

        # Define header formats with increasing sizes
        header_formats = []
        for level in range(6, 0, -1):
            header_format = QTextCharFormat()
            # header_format.setForeground(QColor("blue"))
            header_format.setFontFamily("Fira Sans")
            header_format.setFontWeight(QFont.Weight.Bold)
            header_formats.append(header_format)

        # Add rules for each header level
        for level, header_format in enumerate(header_formats, start=1):
            self.highlightingRules.append(
                HighlightRule(
                    QRegularExpression(r"^#{1,%d}\s.*" % level),
                    header_format,
                    level,  # Store the header level
                )
            )

        # Inline math format
        self.inlineMathFormat = QTextCharFormat()
        self.inlineMathFormat.setForeground(QColor("darkBlue"))
        self.inlineMathFormat.setFontFamily("Fira Code")
        self.inlineMathFormat.setBackground(QColor( "#9ca0b0"))
        # Inline math (but not LaTeX block fences)
        self.highlightingRules.append(
            HighlightRule(QRegularExpression(r"(?<!\$)\$([^$\n]+?)\$(?!\$)"), self.inlineMathFormat)
        )

        # Inline code format
        self.inlineCodeFormat = QTextCharFormat()
        self.inlineCodeFormat.setForeground(QColor("darkBlue"))
        self.inlineCodeFormat.setFontFamily("Fira Code")
        self.inlineCodeFormat.setBackground(QColor("#9ca0b0"))
        # Inline code (but not code fences)
        self.highlightingRules.append(
            HighlightRule(QRegularExpression(r"(?<!`)`([^`\n]+?)`(?!`)"), self.inlineCodeFormat)
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

        # Links
        linkFormat = QTextCharFormat()
        linkFormat.setForeground(QColor(BLUE))
        linkFormat.setFontWeight(QFont.Weight.Bold)
        linkFormat.setFontUnderline(True)
        # Inline links: [text](url)
        self.highlightingRules.append(
            HighlightRule(QRegularExpression(r"\[([^\]]+)\]\([^\)]+\)"), linkFormat)
        )
        # Reference-style links: [text][ref]
        self.highlightingRules.append(
            HighlightRule(QRegularExpression(r"\[([^\]]+)\]\[[^\]]+\]"), linkFormat)
        )

    @override
    def highlightBlock(self, text: str) -> None:
        """Highlight a block of text using the defined rules."""
        # Handle block states
        previous_state = self.previousBlockState()
        current_state = self.STATE_NORMAL
        stripped_text = text.strip()

        # Check if we're in or entering a code block
        is_code_fence = stripped_text.startswith("```")
        is_latex_fence = stripped_text.startswith("$$")

        if is_code_fence:
            # Always format code fences
            self.setFormat(0, len(text), self.codeFenceFormat)

            if previous_state == self.STATE_CODE_BLOCK:
                # Ending a code block
                current_state = self.STATE_NORMAL
            else:
                # Starting a code block
                current_state = self.STATE_CODE_BLOCK
        elif is_latex_fence:
            # Always format LaTeX fences
            self.setFormat(0, len(text), self.latexFenceFormat)

            if previous_state == self.STATE_LATEX_BLOCK:
                # Ending a LaTeX block
                current_state = self.STATE_NORMAL
            else:
                # Starting a LaTeX block
                current_state = self.STATE_LATEX_BLOCK
        elif previous_state == self.STATE_CODE_BLOCK:
            # Continue code block
            current_state = self.STATE_CODE_BLOCK
        elif previous_state == self.STATE_LATEX_BLOCK:
            # Continue LaTeX block
            current_state = self.STATE_LATEX_BLOCK

        # Set the current block state
        self.setCurrentBlockState(current_state)

        # Apply highlighting based on state
        if current_state == self.STATE_CODE_BLOCK and not is_code_fence:
            # Format entire line as code (except for fences)
            self.setFormat(0, len(text), self.codeFormat)
        elif current_state == self.STATE_LATEX_BLOCK and not is_latex_fence:
            # Format entire line as LaTeX (except for fences)
            self.setFormat(0, len(text), self.latexFormat)
        else:
            # Apply normal highlighting rules
            line_of_text = text
            for rule in self.highlightingRules:
                expression = rule.pattern
                index = expression.globalMatch(line_of_text)
                while index.hasNext():
                    match = index.next()
                    start = match.capturedStart()
                    length = match.capturedLength()
                    self.setFormat(start, length, rule.format)
                    # # Debug print to verify matches
                    # if rule.level > 0:  # Only print for header rules
                    #     print(
                    #         f"Matched header level {rule.level} at {start}:{length} - '{text[start:start+length]}'"
                    #     )


if __name__ == "__main__":

    @final
    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super(MainWindow, self).__init__()

            self.setWindowTitle("Markdown Syntax Highlighter")

            textEdit = QTextEdit()
            self.setCentralWidget(textEdit)

            self.highlighter = MarkdownHighlighter(textEdit.document())

    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
