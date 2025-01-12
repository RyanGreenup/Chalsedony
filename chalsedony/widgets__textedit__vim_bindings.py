from enum import Enum, auto
from PySide6.QtWidgets import QTextEdit, QWidget
from PySide6.QtGui import (
    QFocusEvent,
    QKeyEvent,
    QMouseEvent,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtCore import Qt


class EditorMode(Enum):
    NORMAL = auto()
    INSERT = auto()
    VISUAL = auto()


class VimTextEdit(QTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__()
        self._mode = EditorMode.INSERT
        self.visual_anchor: None | int = None
        self.yanked_text = ""
        self.g_pressed = False
        self.dark_mode = False
        self.mode = EditorMode.NORMAL

    def _on_lose_focus(self) -> None:
        self.mode = EditorMode.NORMAL
        self.clear_line_highlight()

    def focusOutEvent(self, e: QFocusEvent) -> None:
        event = e
        super().focusOutEvent(event)
        self._on_lose_focus()

    def update_line_highlight(self) -> None:
        if self._mode == EditorMode.NORMAL:
            self.highlight_current_line()
        else:
            self.clear_line_highlight()

    def highlight_current_line(self) -> None:
        if self.hasFocus():
            # Set cursor to block cursor
            cursor = self.textCursor()
            selection = QTextEdit.ExtraSelection()

            # Get highlight color from palette with 40% opacity
            highlight_color = self.palette().color(self.palette().ColorRole.Highlight)
            highlight_color.setAlpha(102)  # 40% of 255

            if hasattr(selection, "format"):
                selection.format.setBackground(highlight_color)  # type: ignore
                selection.format.setProperty(  # type: ignore
                    QTextFormat.Property.FullWidthSelection, True
                )  # type: ignore
                selection.cursor = cursor  # type: ignore
                selection.cursor.clearSelection()  # type: ignore

            self.setExtraSelections([selection])

    def clear_line_highlight(self) -> None:
        self.setExtraSelections([])

    @property
    def mode(self) -> EditorMode:
        return self._mode

    @mode.setter
    def mode(self, value: EditorMode) -> None:
        self._mode = value
        # Set block cursor in normal mode, normal cursor otherwise
        match value:
            case EditorMode.NORMAL:
                self.setCursorWidth(8)  # Block cursor
            case _:
                self.setCursorWidth(1)  # Normal Cursor

    def keyPressEvent(self, e: QKeyEvent) -> None:
        match (self.mode, e.key()):
            case (EditorMode.INSERT, Qt.Key.Key_Escape):
                self.mode = EditorMode.NORMAL
                self.update_line_highlight()

            case (EditorMode.INSERT, _):
                super().keyPressEvent(e)

            case (EditorMode.VISUAL, _):
                self.handle_visual_mode(e)

            case (EditorMode.NORMAL, _):
                self.handle_normal_mode(e)

            case (_, Qt.Key.Key_Escape):
                self.mode = EditorMode.NORMAL
                self.update_line_highlight()

            case (_, _):
                super().keyPressEvent(e)

    def enter_insert_mode(self) -> None:
        self.mode = EditorMode.INSERT
        self.clear_line_highlight()

    def handle_normal_mode(self, e: QKeyEvent) -> None:
        cursor = self.textCursor()
        match e.key():
            case Qt.Key.Key_H:
                cursor.movePosition(QTextCursor.MoveOperation.Left)
            case Qt.Key.Key_J:
                cursor.movePosition(QTextCursor.MoveOperation.Down)
            case Qt.Key.Key_K:
                cursor.movePosition(QTextCursor.MoveOperation.Up)
            case Qt.Key.Key_L:
                cursor.movePosition(QTextCursor.MoveOperation.Right)
            case Qt.Key.Key_I:
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                    self.mode = EditorMode.INSERT
                    self.clear_line_highlight()
                else:
                    self.enter_insert_mode()
            case Qt.Key.Key_0:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            case Qt.Key.Key_D:
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    # Select from current position to end of line
                    cursor.movePosition(
                        QTextCursor.MoveOperation.EndOfBlock,
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    # Store in yank buffer and delete
                    self.yanked_text = cursor.selectedText()
                    cursor.removeSelectedText()
            case Qt.Key.Key_U:
                self.undo()
            case Qt.Key.Key_R:
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    # Enter replace mode which overwrites existing text
                    self.mode = EditorMode.INSERT
                    cursor.movePosition(
                        QTextCursor.MoveOperation.EndOfBlock,
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    # Store text for potential undo
                    self.yanked_text = cursor.selectedText()
                else:
                    # Single character replace (lowercase r)
                    self.mode = EditorMode.INSERT
                cursor.movePosition(
                    QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor
                )
                cursor.removeSelectedText()

            # Capital A for end of line
            case Qt.Key.Key_A:
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.mode = EditorMode.INSERT
                    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                else:
                    cursor.movePosition(QTextCursor.MoveOperation.Right)
                    self.mode = EditorMode.INSERT
            case Qt.Key.Key_O:
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                    cursor.insertText("\n")
                    cursor.movePosition(QTextCursor.MoveOperation.Up)
                else:
                    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                    cursor.insertText("\n")
                self.mode = EditorMode.INSERT
            case Qt.Key.Key_D:
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                    cursor.movePosition(
                        QTextCursor.MoveOperation.EndOfBlock,
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    # Cut text instead of removing it
                    self.yank_text(cursor)
                    cursor.removeSelectedText()
            case Qt.Key.Key_Y:
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                    cursor.movePosition(
                        QTextCursor.MoveOperation.EndOfBlock,
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    self.yank_text(cursor)
            case Qt.Key.Key_V:
                self.mode = EditorMode.VISUAL
                if not e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.visual_anchor = cursor.position()
                else:
                    self.select_entire_line(cursor)
            case Qt.Key.Key_P:
                self.put_text(cursor)
            case Qt.Key.Key_G:
                if self.g_pressed:
                    self.move_to_top(cursor)
                    self.g_pressed = False
                else:
                    self.move_to_bottom(cursor)
            case _:
                self.g_pressed = False

        # This separate check for Key_G ensures that the `g_pressed` state is handled correctly.
        if e.key() == Qt.Key.Key_G and not self.g_pressed:
            self.g_pressed = True
        else:
            self.setTextCursor(cursor)

        self.update_line_highlight()

    def handle_visual_mode(self, e: QKeyEvent) -> None:
        cursor = self.textCursor()

        match e.key():
            case Qt.Key.Key_Escape:
                self.exit_visual_mode(cursor)
            case Qt.Key.Key_J:
                cursor.movePosition(
                    QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor
                )
            case Qt.Key.Key_K:
                cursor.movePosition(
                    QTextCursor.MoveOperation.Up, QTextCursor.MoveMode.KeepAnchor
                )
            case Qt.Key.Key_H:
                cursor.movePosition(
                    QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor
                )
            case Qt.Key.Key_L:
                cursor.movePosition(
                    QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor
                )
            case Qt.Key.Key_I:
                self.insert_mode = True
                # self.exit_visual_mode(cursor)
            case Qt.Key.Key_G:
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    cursor.movePosition(
                        QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor
                    )
            case Qt.Key.Key_0:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            case Qt.Key.Key_X:
                self.delete_text(cursor)
                self.exit_visual_mode(cursor)
            case Qt.Key.Key_Y:
                self.yank_text(cursor)

        self.setTextCursor(cursor)

    def exit_visual_mode(self, cursor: QTextCursor) -> None:
        self.mode = EditorMode.NORMAL
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def yank_text(self, cursor: QTextCursor) -> None:
        self.yanked_text = cursor.selectedText()
        self.exit_visual_mode(cursor)

    def delete_text(self, cursor: QTextCursor) -> None:
        try:
            self.yanked_text = cursor.selectedText()
        except Exception as e:
            print(f"No text selected: {e}")
        try:
            cursor.removeSelectedText()
        except Exception as e:
            print(f"Failed to delete text: {e}")

    def put_text(self, cursor: QTextCursor) -> None:
        if self.yanked_text:
            cursor.insertText(self.yanked_text)

    def select_entire_line(self, cursor: QTextCursor) -> None:
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor
        )
        self.setTextCursor(
            cursor
        )  # Set the cursor to reflect the entire line selection.

    def move_to_top(self, cursor: QTextCursor) -> None:
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)

    def move_to_bottom(self, cursor: QTextCursor) -> None:
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        super().mousePressEvent(e)
        self.mode = EditorMode.INSERT
        self.clear_line_highlight()
