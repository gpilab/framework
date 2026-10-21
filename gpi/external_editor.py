"""VS Code editing sessions for the Custom node's Python code widget."""

import ast
import json
import os
from pathlib import Path
import shutil
import sys
from typing import TYPE_CHECKING

import psutil

from . import QtCore, QtWidgets
from .logger import manager

if TYPE_CHECKING:
    from .widgets import TextEdit

log = manager.getLogger(__name__)

_CONTEXT_HEADER = (
    "# GPI editing context only; this header is not executed by GPI.\n"
    "# Keep this header unchanged and edit your node code below it.\n"
    "from typing import TYPE_CHECKING\n"
    "if TYPE_CHECKING:\n"
    "    from gpi import NodeAPI\n"
    "    self: NodeAPI\n"
    "\n"
    "# --- GPI node code ---\n"
)


def _find_vscode() -> str:
    installations = {
        process.info['exe']
        for process in psutil.process_iter(['name', 'exe'])
        if (process.info['name']
            and process.info['name'].lower() in (
                'code.exe', 'code - insiders.exe', 'code', 'code - insiders')
            and process.info['exe'])
    }
    if len(installations) == 1:
        return installations.pop()
    if len(installations) > 1:
        raise OSError(
            'Multiple VS Code installations are running. Close the one you '
            'do not want GPI to use, then try again.')
    launcher = shutil.which('code')
    if launcher:
        path = Path(launcher)
        if os.name != 'nt' or path.suffix.lower() not in ('.cmd', '.bat'):
            return str(path)
        # QProcess needs the native executable, not the Windows batch launcher.
        executable = path.parent.parent / 'Code.exe'
        if executable.is_file():
            return str(executable)
    if os.name == 'nt':
        for variable, relative in (
            ('LOCALAPPDATA', Path('Programs') / 'Microsoft VS Code' / 'Code.exe'),
            ('ProgramFiles', Path('Microsoft VS Code') / 'Code.exe'),
            ('ProgramFiles(x86)', Path('Microsoft VS Code') / 'Code.exe'),
        ):
            root = os.environ.get(variable)
            if root and (Path(root) / relative).is_file():
                return str(Path(root) / relative)
    raise FileNotFoundError(
        "VS Code was not found. Install VS Code and add its 'code' command "
        "to PATH, then restart GPI."
    )


class VSCodeEditor(QtCore.QObject):
    """Own a GUI-only session; importing a save never emits a compute event."""

    def __init__(self, code_widget: 'TextEdit'):
        super().__init__(code_widget)
        self._widget = code_widget
        self._path: Path | None = None
        self._last_code = ''
        self._pending_text: str | None = None
        self._last_error = ''
        self._active = False
        self._context_header = _CONTEXT_HEADER
        self._code_line = 1
        self._directories: list[QtCore.QTemporaryDir] = []
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._sync)
        code_widget.installEventFilter(self)

        self.open_button = QtWidgets.QPushButton('Edit in VS Code', code_widget)
        self.stop_button = QtWidgets.QPushButton('Stop VS Code Sync', code_widget)
        self.stop_button.setEnabled(False)
        self.status = QtWidgets.QLabel(code_widget)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.open_button.clicked.connect(self.open)
        self.stop_button.clicked.connect(self.stop)
        layout = code_widget.layout()
        row = layout.rowCount()
        layout.addWidget(self.open_button, row, 0, 1, 2)
        layout.addWidget(self.stop_button, row, 2)
        layout.addWidget(self.status, row + 1, 0, 1, 3)

    def eventFilter(self, watched, event):
        if watched is self._widget and event.type() == QtCore.QEvent.Close:
            self.stop()
        return super().eventFilter(watched, event)

    def _error(self, message: str) -> None:
        if message != self._last_error:
            log.warn(message)
        self._last_error = message
        self.status.setText(message)

    def open(self) -> None:
        try:
            executable = _find_vscode()
            if not self._active:
                self._path = self._prepare()
            assert self._path is not None
            arguments = [
                '--reuse-window', '--add', str(self._path.parent),
                '--goto', '{}:{}'.format(self._path, self._code_line),
            ]
            started, _pid = QtCore.QProcess.startDetached(executable, arguments)
            if not started:
                raise OSError('VS Code could not be started.')
        except (OSError, UnicodeError) as error:
            self._error('VS Code: {}'.format(error))
            return

        self._active = True
        self._widget.set_editor_locked(True)
        self.stop_button.setEnabled(True)
        self._last_error = ''
        self.status.setText(
            'VS Code sync active. Auto Save updates GPI after a short pause; '
            'Ctrl+S also syncs. Click Compute to run.\n'
            + str(self._path))
        self._timer.start()

    def _prepare(self) -> Path:
        directory = QtCore.QTemporaryDir(
            str(Path(QtCore.QDir.tempPath()) / 'gpi-custom-XXXXXX'))
        if not directory.isValid():
            raise OSError('Cannot create a temporary VS Code folder.')
        self._directories.append(directory)
        # Node/widget deletion removes the files even if a Python reference
        # to this controller survives the underlying Qt objects.
        self._widget.destroyed.connect(directory.remove)
        folder = Path(directory.path())
        path = folder / 'custom_node.py'
        settings = folder / '.vscode'
        settings.mkdir()
        (settings / 'settings.json').write_text(json.dumps({
            'files.autoSave': 'afterDelay',
            'files.autoSaveDelay': 500,
            'python.defaultInterpreterPath': sys.executable,
            'python.analysis.extraPaths': [str(Path(__file__).resolve().parent.parent)],
        }, indent=2), encoding='utf-8')
        self._last_code = self._widget.get_val()
        # Future imports must precede the generated type-checking context.
        # Syntax-invalid buffers are still editable and checked by the node.
        future_end = 0
        try:
            tree = ast.parse(self._last_code)
        except SyntaxError:
            tree = None
        if tree is not None:
            for statement in tree.body:
                if isinstance(statement, ast.ImportFrom) and statement.module == '__future__':
                    future_end = statement.end_lineno
        offset = len(''.join(self._last_code.splitlines(keepends=True)[:future_end]))
        before, after = self._last_code[:offset], self._last_code[offset:]
        self._context_header = (
            ('\n' if before and not before.endswith('\n') else '') + _CONTEXT_HEADER)
        prefix = before + self._context_header
        self._code_line = prefix.count('\n') + 1
        path.write_text(prefix + after, encoding='utf-8')
        self._pending_text = None
        return path

    def _sync(self, force: bool = False) -> bool:
        if not self._active:
            return True
        assert self._path is not None
        try:
            text = self._path.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError) as error:
            self._error('VS Code sync failed: {}. Last imported code is retained.'
                        .format(error))
            return False

        # Two matching reads avoid importing a file halfway through a save.
        # Polling also handles atomic replacement saves and recreated files.
        if not force and text != self._pending_text:
            self._pending_text = text
            return True
        if text.count(self._context_header) != 1:
            self._error('VS Code sync paused: restore the unchanged GPI context '
                        'header. Last imported code is retained.')
            return False
        if self._widget.get_val() != self._last_code:
            self._error('VS Code sync paused: GPI code changed outside this '
                        'session. Stop sync before editing again; the external '
                        'file is retained until the node closes.')
            return False

        code = text.replace(self._context_header, '', 1)
        if code != self._last_code:
            # Importing saved code must not trigger node execution.
            blocked = self._widget.blockSignals(True)
            try:
                self._widget.set_val(code)
            finally:
                self._widget.blockSignals(blocked)
            self._last_code = code
        self._last_error = ''
        self.status.setText(
            'VS Code sync active. Auto Save updates GPI after a short pause; '
            'Ctrl+S also syncs. Click Compute to run.\n'
            + str(self._path))
        return True

    def stop(self) -> None:
        synced = self._sync(force=True)
        self._timer.stop()
        self._active = False
        self._widget.set_editor_locked(False)
        self.stop_button.setEnabled(False)
        if synced:
            self.status.setText(
                'VS Code sync stopped. Edit here, or reopen VS Code. '
                'Save the GPI network to keep your code.')
        else:
            self.status.setText(
                self._last_error + '\nSync stopped; editing in GPI is enabled. '
                'Recover external edits before closing the node:\n' + str(self._path))
