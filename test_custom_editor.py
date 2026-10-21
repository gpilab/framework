import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gpi
from gpi import QtCore, QtWidgets
from gpi.external_editor import VSCodeEditor, _CONTEXT_HEADER, _find_vscode
from gpi.widgets import TextEdit


class TestVSCodeEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.widget = TextEdit('Python Code')
        self._widget_destroyed = False
        self.widget.set_val("self.setData('out1', 1)\n")
        self.editor = VSCodeEditor(self.widget)
        self.events = Mock()
        self.widget.valueChanged.connect(self.events)
        self.launcher = patch('gpi.external_editor._find_vscode', return_value='Code.exe')
        self.launcher.start()
        self.addCleanup(self.launcher.stop)
        self.process = patch.object(QtCore.QProcess, 'startDetached',
                                    return_value=(True, 1234))
        self.start_process = self.process.start()
        self.addCleanup(self.process.stop)
        self.addCleanup(self.destroy_widget)

    def destroy_widget(self):
        if not self._widget_destroyed:
            self.widget.deleteLater()
            QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
            self._widget_destroyed = True

    def start(self):
        self.editor.open_button.click()
        self.assertTrue(self.editor._active)
        self.assertTrue(self.widget.wdg.isReadOnly())
        self.assertTrue(self.editor._timer.isActive())
        return self.editor._path

    def save(self, code, path=None):
        path = path or self.editor._path
        path.write_text(_CONTEXT_HEADER + code, encoding='utf-8')
        self.editor._sync()
        self.editor._sync()

    def test_launch_has_context_interpreter_and_import_path(self):
        path = self.start()
        self.assertEqual(path.read_text(encoding='utf-8'),
                         _CONTEXT_HEADER + self.widget.get_val())
        settings = json.loads((path.parent / '.vscode' / 'settings.json').read_text())
        self.assertEqual(settings['files.autoSave'], 'afterDelay')
        self.assertEqual(settings['files.autoSaveDelay'], 500)
        self.assertEqual(settings['python.defaultInterpreterPath'], os.sys.executable)
        self.assertEqual(settings['python.analysis.extraPaths'],
                         [str(Path(__file__).resolve().parent)])
        arguments = self.start_process.call_args.args[1]
        self.assertEqual(arguments[:3], ['--reuse-window', '--add', str(path.parent)])
        self.assertNotIn('--new-window', arguments)
        self.assertNotIn('--user-data-dir', arguments)
        self.assertNotIn('--profile', arguments)
        self.assertEqual(arguments[-1], '{}:9'.format(path))
        self.events.assert_not_called()

    def test_save_imports_without_compute_event_and_preserves_text_signal(self):
        self.start()
        text_changed = Mock()
        self.widget.wdg.textChanged.connect(text_changed)
        code = "self.setData('out1', 'saved')\n"
        self.save(code)
        self.assertEqual(self.widget.get_val(), code)
        self.events.assert_not_called()
        text_changed.assert_called_once()

    def test_waits_for_two_matching_reads(self):
        path = self.start()
        original = self.widget.get_val()
        path.write_text(_CONTEXT_HEADER + 'partial', encoding='utf-8')
        self.editor._sync()
        self.assertEqual(self.widget.get_val(), original)
        path.write_text(_CONTEXT_HEADER + 'finished', encoding='utf-8')
        self.editor._sync()
        self.assertEqual(self.widget.get_val(), original)
        self.editor._sync()
        self.assertEqual(self.widget.get_val(), 'finished')

    def test_future_imports_remain_valid_and_round_trip_exactly(self):
        for code in (
            'from __future__ import annotations',
            '"""Module documentation."""\nfrom __future__ import annotations\n'
            "self.setData('out1', 1)\n",
        ):
            with self.subTest(code=code):
                self.widget.set_val(code)
                path = self.start()
                exported = path.read_text(encoding='utf-8')
                compile(exported, str(path), 'exec')
                self.assertLess(exported.index('from __future__'),
                                exported.index(_CONTEXT_HEADER))
                self.editor.stop()
                self.assertEqual(self.widget.get_val(), code)

    def test_atomic_save_recreated_file_and_unicode(self):
        path = self.start()
        replacement = path.with_suffix('.tmp')
        code = "label = '\\u03b1'\n"
        replacement.write_text(_CONTEXT_HEADER + code, encoding='utf-8-sig')
        replacement.replace(path)
        self.editor._sync()
        self.editor._sync()
        self.assertEqual(self.widget.get_val(), code)
        path.unlink()
        self.assertFalse(self.editor._sync(force=True))
        self.assertIn('sync failed', self.editor.status.text())
        self.save('')
        self.assertEqual(self.widget.get_val(), '')

    def test_invalid_header_preserves_code_and_recovers(self):
        path = self.start()
        original = self.widget.get_val()
        path.write_text("print('missing header')", encoding='utf-8')
        self.assertFalse(self.editor._sync(force=True))
        self.assertEqual(self.widget.get_val(), original)
        self.assertIn('header', self.editor.status.text())
        self.save('recovered = True')
        self.assertEqual(self.widget.get_val(), 'recovered = True')

    def test_invalid_encoding_does_not_erase_code(self):
        path = self.start()
        original = self.widget.get_val()
        path.write_bytes(b'\xff')
        self.assertFalse(self.editor._sync(force=True))
        self.assertEqual(self.widget.get_val(), original)
        self.assertIn('sync failed', self.editor.status.text())

    def test_programmatic_edit_is_not_overwritten(self):
        self.start()
        self.widget.set_val('changed_in_gpi = True')
        self.save('external_change = True')
        self.assertEqual(self.widget.get_val(), 'changed_in_gpi = True')
        self.assertIn('changed outside', self.editor.status.text())
        self.editor.stop_button.click()
        self.assertFalse(self.widget.wdg.isReadOnly())
        self.assertIn('Recover external edits', self.editor.status.text())

    def test_stop_imports_last_save_and_allows_local_editing(self):
        path = self.start()
        path.write_text(_CONTEXT_HEADER + 'last_save = True', encoding='utf-8')
        self.editor.stop_button.click()
        self.assertEqual(self.widget.get_val(), 'last_save = True')
        self.assertFalse(self.editor._active)
        self.assertFalse(self.widget.wdg.isReadOnly())
        self.assertFalse(self.editor._timer.isActive())
        self.assertFalse(self.editor.stop_button.isEnabled())
        self.events.assert_not_called()
        self.save('ignored = True')
        self.assertEqual(self.widget.get_val(), 'last_save = True')

    def test_sessions_are_isolated_and_reopen_uses_current_gpi_code(self):
        path = self.start()
        other = TextEdit('Other node')
        other.set_val('other = True')
        session = VSCodeEditor(other)
        try:
            session.open()
            self.assertNotEqual(path.parent, session._path.parent)
            self.save('first = True')
            self.assertEqual(other.get_val(), 'other = True')
        finally:
            other.deleteLater()
            QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        self.editor.stop()
        self.widget.set_val('local_edit = True')
        reopened = self.start()
        self.assertNotEqual(path, reopened)
        self.assertTrue(path.exists())
        self.assertEqual(reopened.read_text(encoding='utf-8'),
                         _CONTEXT_HEADER + 'local_edit = True')

    def test_launch_failure_leaves_local_editing_and_reports_error(self):
        self.start_process.return_value = (False, 0)
        self.editor.open_button.click()
        self.assertFalse(self.widget.wdg.isReadOnly())
        self.assertFalse(self.editor._active)
        self.assertFalse(self.editor._timer.isActive())
        self.assertIn('could not be started', self.editor.status.text())

    def test_missing_vscode_reports_actionable_error(self):
        with patch('gpi.external_editor._find_vscode',
                   side_effect=FileNotFoundError('Install VS Code')):
            self.editor.open_button.click()
        self.assertFalse(self.widget.wdg.isReadOnly())
        self.assertIn('Install VS Code', self.editor.status.text())
        self.start_process.assert_not_called()

    def test_temp_write_failure_does_not_lock_editor(self):
        with patch.object(Path, 'write_text', side_effect=PermissionError('denied')):
            self.editor.open_button.click()
        self.assertIn('denied', self.editor.status.text())
        self.assertFalse(self.widget.wdg.isReadOnly())
        self.assertFalse(self.editor._timer.isActive())
        self.start_process.assert_not_called()

    def test_network_settings_persist_code_but_not_session_lock(self):
        self.start()
        self.save('persisted = True')
        settings = self.widget.getSettings()
        self.assertEqual(settings['kwargs']['val'], 'persisted = True')
        self.assertFalse(settings['kwargs']['readonly'])
        self.assertNotIn('editor_locked', settings['kwargs'])
        restored = TextEdit('Restored')
        try:
            for name, value in settings['kwargs'].items():
                getattr(restored, 'set_' + name)(value)
            self.assertEqual(restored.get_val(), 'persisted = True')
            self.assertFalse(restored.wdg.isReadOnly())
        finally:
            restored.deleteLater()

    def test_configured_readonly_survives_session_unlock(self):
        self.widget.set_readonly(True)
        self.start()
        self.editor.stop()
        self.assertTrue(self.widget.get_readonly())
        self.assertTrue(self.widget.wdg.isReadOnly())

    def test_deleting_widget_cleans_temporary_files_and_timer(self):
        path = self.start()
        self.destroy_widget()
        self.assertFalse(path.parent.exists())

    def test_closing_code_widget_stops_session_and_imports_last_save(self):
        path = self.start()
        path.write_text(_CONTEXT_HEADER + 'last_save = True', encoding='utf-8')
        self.widget.close()
        self.assertFalse(self.editor._active)
        self.assertFalse(self.editor._timer.isActive())
        self.assertEqual(self.widget.get_val(), 'last_save = True')

    def test_timer_imports_save_without_manual_sync(self):
        path = self.start()
        path.write_text(_CONTEXT_HEADER + 'timer_save = True', encoding='utf-8')
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(1500, loop.quit)
        loop.exec()
        self.assertEqual(self.widget.get_val(), 'timer_save = True')
        self.events.assert_not_called()


class TestVSCodeDiscovery(unittest.TestCase):
    def setUp(self):
        processes = patch('gpi.external_editor.psutil.process_iter', return_value=[])
        self.processes = processes.start()
        self.addCleanup(processes.stop)

    def test_running_installation_wins_over_stale_path(self):
        executable = r'C:\Users\example\Microsoft VS Code\Code.exe'
        self.processes.return_value = [
            Mock(info={'name': 'Code.exe', 'exe': executable}),
            Mock(info={'name': 'Code.exe', 'exe': executable}),
            Mock(info={'name': 'python.exe', 'exe': r'C:\Python\python.exe'}),
            Mock(info={'name': 'Code.exe', 'exe': None}),
        ]
        with patch('gpi.external_editor.shutil.which',
                   return_value=r'C:\VSCode\1.99.3\bin\code.cmd') as which:
            self.assertEqual(_find_vscode(), executable)
            which.assert_not_called()

    def test_multiple_running_installations_require_user_choice(self):
        self.processes.return_value = [
            Mock(info={'name': 'Code.exe', 'exe': r'C:\VSCode\Code.exe'}),
            Mock(info={'name': 'Code - Insiders.exe',
                       'exe': r'C:\Insiders\Code - Insiders.exe'}),
        ]
        with self.assertRaisesRegex(OSError, 'Multiple VS Code installations'):
            _find_vscode()

    def test_missing_executable_is_actionable(self):
        with patch('gpi.external_editor.shutil.which', return_value=None), \
                patch('gpi.external_editor.os.environ', {}):
            with self.assertRaisesRegex(FileNotFoundError, "add its 'code' command"):
                _find_vscode()

    @unittest.skipUnless(os.name == 'nt', 'Windows launcher resolution')
    def test_windows_batch_launcher_resolves_native_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bin').mkdir()
            (root / 'Code.exe').touch()
            with patch('gpi.external_editor.shutil.which',
                       return_value=str(root / 'bin' / 'code.cmd')):
                self.assertEqual(_find_vscode(), str(root / 'Code.exe'))


class TestCustomNodeEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        path = (Path(__file__).parent / 'gpi_core' / 'interfaces' / 'GPI'
                / 'Custom_GPI.py')
        spec = importlib.util.spec_from_file_location('custom_editor_node', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.node_class = module.ExternalNode

    def make_node(self):
        node = self.node_class.__new__(self.node_class)
        QtWidgets.QWidget.__init__(node)
        widgets = {}

        def add_widget(kind, title, **attributes):
            widget = getattr(gpi.widgets, kind)(title)
            widgets[title] = widget
            for name, value in attributes.items():
                getattr(widget, 'set_' + name)(value)

        node.addWidget = add_widget
        node.getWidget = widgets.__getitem__
        node.addInPort = Mock()
        node.addOutPort = Mock()
        node.modifyWidget_direct = lambda title, **attrs: [
            getattr(widgets[title], 'set_' + name)(value)
            for name, value in attrs.items()
        ]
        node.initUI()
        for widget in widgets.values():
            self.addCleanup(widget.deleteLater)
        self.addCleanup(node.deleteLater)
        return node, widgets

    def test_gui_wires_editor_without_live_syntax_check(self):
        with patch.dict(os.environ, {'GPI_WORKER_MODE': '0'}):
            node, widgets = self.make_node()
        self.assertIsInstance(node._external_editor, VSCodeEditor)
        self.assertFalse(hasattr(node, '_syntax_timer'))
        widgets['Python Code'].set_val('if:')
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(600, loop.quit)
        loop.exec()
        self.assertEqual(widgets['Status'].get_val(), 'Ready.')
        self.assertIsNone(widgets['Python Code'].get_error_line())

    def test_compute_still_reports_syntax_errors(self):
        with patch.dict(os.environ, {'GPI_WORKER_MODE': '0'}):
            node, widgets = self.make_node()
        widgets['Python Code'].set_val('if:')
        node.getVal = lambda title: widgets[title].get_val()
        node.setAttr = node.modifyWidget_direct
        node.setData = Mock()
        node.log = Mock()
        self.assertEqual(node.compute(), 1)
        self.assertIn('SYNTAX ERROR', widgets['Status'].get_val())
        self.assertEqual(widgets['Python Code'].get_error_line(), 1)
        for port in ('out1', 'out2', 'out3', 'out4'):
            node.setData.assert_any_call(port, None)

    def test_worker_does_not_create_external_editor(self):
        with patch.dict(os.environ, {'GPI_WORKER_MODE': '1'}):
            node, _ = self.make_node()
        self.assertFalse(hasattr(node, '_external_editor'))

    def test_imported_code_executes_only_on_compute_in_all_execution_modes(self):
        with patch.dict(os.environ, {'GPI_WORKER_MODE': '0'}):
            node, widgets = self.make_node()
        outputs = {}
        node.getVal = lambda title: widgets[title].get_val()
        node.getData = lambda title: 41
        node.setData = Mock(side_effect=outputs.__setitem__)
        node.setAttr = node.modifyWidget_direct
        node.log = Mock()
        editor = node._external_editor
        with patch('gpi.external_editor._find_vscode', return_value='Code.exe'), \
                patch.object(QtCore.QProcess, 'startDetached', return_value=(True, 1234)):
            editor.open_button.click()
        self.addCleanup(editor._timer.stop)
        code = "self.setData('out1', self.getData('in1') + 1)\n"
        editor._path.write_text(_CONTEXT_HEADER + code, encoding='utf-8')
        editor._sync(force=True)
        node.setData.assert_not_called()
        for value, execution in enumerate(
                (gpi.GPI_THREAD, gpi.GPI_PROCESS, gpi.GPI_APPLOOP)):
            with self.subTest(execution=execution):
                widgets['Execution Type'].set_val(value)
                self.assertEqual(node.execType(), execution)
                self.assertEqual(node.compute(), 0)
                self.assertEqual(outputs['out1'], 42)
        editor.stop_button.click()
        self.assertEqual(node.setData.call_count, 3)


if __name__ == '__main__':
    unittest.main()
