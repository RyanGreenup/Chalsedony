from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import QCoreApplication, Signal, QTimer, QObject
import pynvim
import subprocess
import os
import random
import tempfile
import shutil
import asyncio
from pynvim.api import Buffer
import shiboken6
from typing import Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


class Ok(Generic[T]):
    __match_args__ = ("value",)

    def __init__(self, value: T):
        self.value = value

    def unwrap(self) -> T:
        return self.value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False


class Err(Generic[E]):
    __match_args__ = ("error",)

    def __init__(self, error: E):
        self.error = error

    def unwrap(self) -> E:
        raise self.error

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True


Result = Union[Ok[T], Err[E]]


class NeovimBufferError(Exception):
    """Raised when Neovim buffer is not available"""

    pass


class NeovimNotRunning(Exception):
    """Raised when Neovim is not running but needed"""

    pass


class NeovimAlreadyRunning(Exception):
    """Raised when Neovim is not running but needed"""

    pass


class EditorError(Exception):
    """Raised when editor widget is not available"""

    pass


class InvalidEditorWidgetError(EditorError):
    """Raised when attempting to connect an invalid editor widget"""

    def __init__(self, message: str = "Invalid editor widget - cannot connect"):
        super().__init__(message)


class NeovimHandler(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._nvim: pynvim.Nvim | None = None  # If none the socket is not connected
        self._nvim_buffer: Buffer | None = None
        self.nvim_process: subprocess.Popen[bytes] | None = None
        self.editors: dict[str, QTextEdit] = {}  # Track all connected editors
        self.is_syncing = False
        self.socket_path = f"/tmp/draftsmith_qt.{random.random()}.sock"
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_nvim_changes)
        self._editor: QTextEdit | None = None
        self.buffer_named: bool = False
        self.edit_buffer_name: str = "__Chalsedony_Edit"

    @property
    def editor(self) -> QTextEdit | None:
        if shiboken6.isValid(self._editor):
            return self._editor
        return None

    @editor.setter
    def editor(self, editor: QTextEdit) -> None:
        if shiboken6.isValid(editor):
            self._editor = editor
        else:
            print("Invalid editor widget, could be deleted by C++")

    @property
    def nvim(self) -> pynvim.Nvim | None:
        try:
            return self._nvim
        except Exception as e:
            print(f"Failed to get nvim: {e}")
            return None

    @nvim.setter
    def nvim(self, nvim: pynvim.Nvim) -> None:
        self._nvim = nvim

    @nvim.deleter
    def nvim(self) -> None:
        if self._nvim:
            self._nvim.close()
            self._nvim = None

    @property
    def nvim_buffer(self) -> Buffer | None:
        if self.nvim is None:
            return None


        for buffer in self.nvim.buffers:
            if buffer.name.endswith(self.edit_buffer_name):
                return buffer
        return None


        try:
            return self.nvim.current.buffer
        except Exception as e:
            print(f"Failed to get nvim buffer: {e}")
            return None

    @nvim_buffer.setter
    def nvim_buffer(self, buffer: Buffer | None) -> None:
        self._nvim_buffer = buffer

    def connect_editor(self, editor: QTextEdit) -> Result[None, Exception]:
        """Connect a QTextEdit widget to this Neovim instance

        Args:
            editor: The text editor widget to connect
            editor_id: Optional unique identifier for the editor

        Returns:
            Result: Ok(None) on success, Err(Exception) on failure
        """
        try:
            # Assign the editor to the instance
            self.editor = editor

            # Must check that it's a valid widget
            if (e := self.editor) is not None:
                # First sync the text from the editor to Neovim
                # Otherwise the buffer won't correspond to the editor
                self.sync_to_nvim(e)
                # Now connect the signals
                e.textChanged.connect(self.on_editor_changed)
                return Ok(None)
            else:
                return Err(InvalidEditorWidgetError())
        except Exception as e:
            return Err(e)

    # TODO: Returning strings is not great, choose 1:
    # 1. Return None on success, raise an exception on failure
    # 2. Use a Rust-like Result type throughout the code base
    # Given that we don't want to panic, probably go with 2.
    def disconnect_editor(
        self, editor: QTextEdit | None = None
    ) -> Result[None, Exception]:
        """
        Disconnect an editor.

        Avoid using the tracked editor because it could be deleted.

        If None this attempts to disconnect the stored editor with try/except
        to avoid a crash if it's already been deleted.

        Try not to rely on this method, it's better to track the editor

        Args:
            editor: QTextEdit widget to disconnect

        Returns:
            Result: Ok(None) on success, Err(Exception) on failure
        """
        try:
            if editor:
                editor.textChanged.disconnect(self.on_editor_changed)
                return Ok(None)
            else:
                if (stored_editor := self.editor) is None:
                    return Err(ValueError("No valid editor to disconnect"))
                else:
                    try:
                        stored_editor.textChanged.disconnect(self.on_editor_changed)
                        return Ok(None)
                    except RuntimeError as e:
                        return Err(e)
                    except Exception as e:
                        return Err(e)
        except Exception as e:
            return Err(e)

    def restart_nvim_session(self) -> None:
        """Restart the Neovim session"""
        self.stop_nvim_session()
        self.start_nvim_session()

    def start_nvim_session(self) -> Result[str, Exception]:
        """
        Start the Neovim server if if it's not already running
        """
        if self.nvim_process is None:
            try:
                if os.path.exists(self.socket_path):
                    os.remove(self.socket_path)

                self.nvim_process = subprocess.Popen(
                    ["nvim", "--listen", self.socket_path, "--headless"]
                )

                def connect_to_socket_and_set_text() -> None:
                    # Connect to the socket
                    match self._connect_to_socket(self.socket_path):
                        case Ok():
                            # Then set the initial text from the editor
                            if editor := self.editor:
                                self.sync_to_nvim(editor)
                        case Err(error=e):
                            print(f"Unable to connect to socket: {e}")

                # Wait for the socket to be created before connecting
                QTimer.singleShot(500, connect_to_socket_and_set_text)
                message = f"Neovim started with PID: {self.nvim_process.pid} on Socket {self.socket_path}"
                return Ok(message)
            except Exception as e:
                return Err(e)
        else:
            return Err(NeovimAlreadyRunning("Neovim is already running"))

    def stop_nvim_session(self) -> None:
        """Stop the Neovim session and clean up resources"""
        self.cleanup(
            disconnect_editor=False
        )  # Explicitly disconnect when stopping session

    def _connect_to_socket(self, socket_path: str) -> Result[None, Exception]:
        """Connect to the Neovim socket

        Args:
            socket_path: Path to the Neovim socket file
        """
        try:
            self.nvim = pynvim.attach("socket", path=socket_path)
            self.timer.start(20)
            if (nvim := self.nvim) is None:
                raise ValueError(
                    "pynvim object must be instantiated before connecting to socket"
                )
            nvim.command("e " + self.edit_buffer_name)
            # Create temp dir that will be deleted automatically
            temp_dir = tempfile.mkdtemp(prefix="draftsmith_")
            nvim.command(f"cd {temp_dir}")
            # Cleanup temp dir when nvim exits
            def cleanup_temp_dir():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Error cleaning up temp dir: {e}")
            self.destroyed.connect(cleanup_temp_dir)
            nvim.command("LspStop")
            nvim.command("set filetype=markdown")
            return Ok(None)
        except Exception as e:
            return Err(e)

    def on_editor_changed(self) -> None:
        """Handle text changes from the editor"""
        if not self.is_syncing:
            if editor := self.editor:
                self.sync_to_nvim(editor)

    def sync_to_nvim(self, editor: QTextEdit) -> Result[None, Exception]:
        """Sync editor content to Neovim

        Args:
            editor: The text editor widget to sync, or None to use active editor
        """
        if self.nvim_buffer:
            try:
                self.is_syncing = True
                text = editor.toPlainText()
                lines = text.split("\n")
                self.nvim_buffer[:] = lines
                self.is_syncing = False
                return Ok(None)
            except Exception as e:
                self.is_syncing = False
                return Err(ValueError(f"Failed to sync to nvim: {e}"))
        else:
            return Err(ValueError("Neovim Buffer is None"))

    def sync_to_editor(self) -> Result[None, Exception]:
        """Sync Neovim content to the editor"""
        if self.current.buffer.name != self.edit_buffer_name:
            print("Not syncing to editor, wrong buffer")
            return Ok(None)
        if (nvim_buffer := self.nvim_buffer) is None:
            return Err(NeovimBufferError("Neovim Buffer is None"))
        if (editor := self.editor) is None:
            return Err(EditorError("Editor is None"))
        try:
            self.is_syncing = True

            # Get current cursor position before changing text
            cursor = editor.textCursor()
            old_position = cursor.position()

            if nvim_text := nvim_buffer[:]:
                nvim_text = "\n".join(nvim_text)
                editor.setPlainText(nvim_text)

                # Restore cursor position after text change
                new_position = min(old_position, len(nvim_text))
                cursor.setPosition(new_position)
                editor.setTextCursor(cursor)

            self.is_syncing = False
            return Ok(None)
        except Exception as e:
            self.is_syncing = False
            return Err(ValueError(f"Failed to sync to editor: {e}"))

    def _is_nvim_alive(self) -> Result[None, Exception]:
        """
        Returns a Result.

        Ok means alive and well

        Err means something is wrong with an appropriate exception
        """
        # Neovim Process is dead
        if self.nvim_process is None or self.nvim_process.poll() is not None:
            return Err(RuntimeError("Neovim process is not running"))

        # Neovim Buffer is unavailable
        try:
            buffer = self.nvim_buffer
            _ = buffer
            return Ok(None)
        except Exception as e:
            return Err(NeovimBufferError(e))

    def check_nvim_changes(self) -> None:
        """Check for changes from Neovim and sync to active editor"""
        match self._is_nvim_alive():
            case Ok():
                pass
            case Err(error=e):
                print(f"Neovim is not alive: {e}")
                self.cleanup()

        if (nvim_buffer := self.nvim_buffer) is None:
            return None
        if (editor := self.editor) is None:
            return None
        if self.is_syncing:
            return None

        try:
            if self.nvim_process and self.nvim_process.poll() is not None:
                print("Neovim process terminated")
                self.cleanup()
                return

            self.is_syncing = True
            if nvim_text := nvim_buffer[:]:
                nvim_text = "\n".join(nvim_text)
                current_text = editor.toPlainText()

                if nvim_text != current_text:
                    # Get current cursor position
                    cursor = editor.textCursor()
                    old_position = cursor.position()

                    if nvim_text != "":
                        editor.setPlainText(nvim_text)

                        # Restore cursor position
                        new_position = min(old_position, len(nvim_text))
                        cursor.setPosition(new_position)
                        editor.setTextCursor(cursor)
                    else:
                        print("Empty buffer")

            self.is_syncing = False
        except (BrokenPipeError, ConnectionResetError):
            print("Neovim connection lost")
            self.cleanup()
        except Exception as e:
            print(f"Failed to check nvim changes: {e}")
            self.is_syncing = False

    def cleanup(self, disconnect_editor: bool = False) -> None:
        """Clean up resources

        Args:
            disconnect_editor: If True, disconnect the editor. Normally False to preserve content
        """
        if disconnect_editor:
            self.disconnect_editor()

        if self.timer.isActive():
            self.timer.stop()
        if self.nvim:
            try:
                self.nvim.close()
            except Exception as e:
                print(f"Failed to close nvim: {e}")
                pass
            del self.nvim

        if self.nvim_process:
            try:
                self.nvim_process.terminate()
                self.nvim_process.wait(timeout=1)
            except Exception as e:
                print(f"Failed to terminate nvim process: {e}")
                pass
            self.nvim_process = None

        self.nvim_buffer = None
        self.is_syncing = False

        # Clean up socket file
        self._remove_socket()

    def _remove_socket(self) -> None:
        """Remove the socket file if it exists"""
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except Exception as e:
                print(f"Failed to remove socket file: {e}")

    def __del__(self) -> None:
        """Destructor to ensure cleanup when object is deleted"""
        self.cleanup(disconnect_editor=False)  # Preserve content on destruction

    def start_gui_neovim(
        self, gui_editor_path: str | None = None, autostart: bool = True
    ) -> Result[int, Exception]:
        """
        Start Neovide GUI connected to this instance

        params:
            gui_editor_path: Path to the Neovide executable
            autostart: If True, Start the neovim session

        Returns:
            Result[int, Exception]: Ok with process ID on success, Err with exception on failure
        """
        # Set the editor to use
        if gui_editor_path is None:
            gui_editor_path = "neovide"

        # Auto start the Neovim session and connect to socket if needed
        if autostart:
            print("Starting Neovim session")
            if self.nvim is None or self.nvim_process is None:
                self.start_nvim_session()
                # Wait for all the QTimers to finish
                QCoreApplication.processEvents()

        # If the process is running, start the GUI
        if self.nvim_process:
            try:
                out = subprocess.Popen([gui_editor_path, "--server", self.socket_path])
                process_id = out.pid
                return Ok(process_id)
            except Exception as e:
                print(f"Failed to start Neovide: {e}")
                return Err(e)
        else:
            error = RuntimeError("Neovim process not running")
            print(str(error))
            return Err(error)


class EditorWidget(QTextEdit):
    textUpdated = Signal(str)

    def __init__(self, nvim_handler: NeovimHandler | None = None) -> None:
        self._nvim_handler = nvim_handler or NeovimHandler()
        self.textChanged.connect(self._on_text_changed)

    @property
    def nvim_handler(self) -> NeovimHandler:
        if self._nvim_handler is None:
            self.connect_neovim_handler()
        if self._nvim_handler:
            return self._nvim_handler
        else:
            message = "No neovim handler found, This is a bug as the neovim handler should have been created."
            # self.set_status_message(message)
            raise ValueError(message)

    @nvim_handler.setter
    def nvim_handler(self, value: NeovimHandler) -> None:
        self._nvim_handler = value

    @nvim_handler.deleter
    def nvim_handler(self) -> None:
        if self._nvim_handler:
            self._nvim_handler.cleanup()
        del self._nvim_handler

    def connect_neovim_handler(self) -> None:
        """
        Start the neovim handler if necessary and connect it to the current editor.
        """
        # If there is no handler, create one (this method wouldn't be called otherwise)
        if self._nvim_handler is None:
            self._nvim_handler = NeovimHandler()
        editor = self.get_current_editor()
        self._nvim_handler.connect_editor(editor)

    def get_current_editor(self) -> QTextEdit:
        return self

    def _on_text_changed(self) -> None:
        self.textUpdated.emit(self.toPlainText())

    def connect_to_nvim(self) -> Result[None, Exception]:
        result = self.nvim_handler.connect_editor(self)
        match result:
            case Ok():
                return Ok(None)
            case Err() as err:
                return Err(err.error)

    def disconnect_from_nvim(self) -> None:
        match self.nvim_handler.disconnect_editor(self):
            case Ok():
                pass
            case Err(error=e):
                print(f"Unable to disconnect from neovim: {e}")

    def start_nvim_session(self) -> Result[int, Exception]:
        match self.connect_to_nvim():
            case Ok():
                pass
            case Err() as err:
                return err
        match self.nvim_handler.start_gui_neovim():
            case Ok(value=value):
                return Ok(value)
            case Err() as err:
                return Err(err.error)

    def closeEvent(self, event: QCloseEvent) -> None:
        del self.nvim_handler
        super().closeEvent(event)


async def run_async_command(command: list[str]) -> tuple[str, str]:
    """Run a command asynchronously and return its output

    Args:
        command: List of command arguments to execute

    Returns:
        tuple: (stdout, stderr) as strings
    """
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    # Wait for the process to finish and collect the output
    stdout, stderr = await process.communicate()

    # Return the output and error, decoded to a string
    return stdout.decode().strip(), stderr.decode().strip()
