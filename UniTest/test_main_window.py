import os
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from gpi import QtCore, QtGui, QtWidgets
from gpi.launch import _configure_wslg_platform
from gpi.mainWindow import MainCanvas
from gpi.node import Node
from gpi.widgets import GPIFileDialog
from gpi.window_geometry import place_initial_window


class CloseConfirmationWindow(MainCanvas):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.already_closed = False
        self._restart_in_progress = False


class TestCloseConfirmation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.window = CloseConfirmationWindow()
        self.addCleanup(self.window.deleteLater)
        self.addCleanup(self.window.hide)

    def answer_dialog(self, answer):
        self.observed = {}

        def respond():
            dialog = self.app.activeModalWidget()
            self.observed['is_message_box'] = isinstance(dialog, QtWidgets.QMessageBox)
            self.observed['parent_visible'] = self.window.isVisible()
            self.observed['parent_minimized'] = self.window.isMinimized()
            self.observed['parent_maximized'] = self.window.isMaximized()
            if isinstance(dialog, QtWidgets.QMessageBox):
                self.observed['dialog_visible'] = dialog.isVisible()
                self.observed['default_no'] = dialog.defaultButton() == dialog.button(QtWidgets.QMessageBox.No)
                dialog.button(answer).click()

        QtCore.QTimer.singleShot(0, respond)

    def test_minimized_window_restored_before_confirmation(self):
        self.window.showMinimized()
        self.app.processEvents()
        self.assertTrue(self.window.isMinimized())
        self.window.raise_ = Mock(wraps=self.window.raise_)
        self.window.activateWindow = Mock(wraps=self.window.activateWindow)
        self.answer_dialog(QtWidgets.QMessageBox.No)
        self.assertFalse(self.window.quitConfirmed())
        self.assertTrue(self.observed['is_message_box'])
        self.assertTrue(self.observed['parent_visible'])
        self.assertFalse(self.observed['parent_minimized'])
        self.assertTrue(self.observed['dialog_visible'])
        self.assertTrue(self.observed['default_no'])
        self.window.raise_.assert_called_once()
        self.window.activateWindow.assert_called_once()
        self.assertFalse(self.window.already_closed)

    def test_maximized_state_preserved_when_restoring(self):
        self.window.showMaximized()
        self.app.processEvents()
        self.window.showMinimized()
        self.app.processEvents()
        self.answer_dialog(QtWidgets.QMessageBox.No)
        self.assertFalse(self.window.quitConfirmed())
        self.assertFalse(self.observed['parent_minimized'])
        self.assertTrue(self.observed['parent_maximized'])

    def test_yes_confirms_quit(self):
        self.answer_dialog(QtWidgets.QMessageBox.Yes)
        self.assertTrue(self.window.quitConfirmed())
        self.assertTrue(self.window.already_closed)

    def test_no_cancels_close_event(self):
        self.window.showMinimized()
        self.app.processEvents()
        self.answer_dialog(QtWidgets.QMessageBox.No)
        event = QtGui.QCloseEvent()
        self.window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.isMinimized())
        self.assertFalse(self.window.already_closed)


class TestNodeMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.window = QtWidgets.QScrollArea()
        self.widget = QtWidgets.QWidget()
        self.window.setWidget(self.widget)
        self.node = SimpleNamespace(_nodeIF_scrollArea=self.window,
                                    _nodeIF=self.widget, _menuHasRaised=False,
                                    _menuPositioned=False, graph=self.widget)
        self.addCleanup(self.window.deleteLater)
        self.addCleanup(self.window.hide)
        titlebar = patch('gpi.theme.win32_set_dark_titlebar')
        titlebar.start()
        self.addCleanup(titlebar.stop)
        self.window.raise_ = Mock(wraps=self.window.raise_)
        self.window.activateWindow = Mock(wraps=self.window.activateWindow)

    def reopen_menu(self):
        Node.menu(self.node)
        self.app.processEvents()
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.isMinimized())
        self.window.raise_.assert_called_once()
        self.window.activateWindow.assert_called_once()

    def test_minimized_menu_is_restored(self):
        self.window.showMinimized()
        self.app.processEvents()
        self.assertTrue(self.window.isMinimized())
        self.reopen_menu()

    def test_closed_minimized_menu_is_restored(self):
        self.window.showMinimized()
        self.app.processEvents()
        self.window.close()
        self.assertFalse(self.window.isVisible())
        self.reopen_menu()

    def test_maximized_state_is_preserved(self):
        self.node._menuHasRaised = True
        self.window.showMaximized()
        self.app.processEvents()
        self.window.showMinimized()
        self.app.processEvents()
        self.reopen_menu()
        self.assertTrue(self.window.isMaximized())

    def test_closed_menu_is_shown(self):
        self.window.show()
        self.window.close()
        self.reopen_menu()

    def test_initial_menu_position_is_not_reset_after_closing(self):
        with patch('gpi.window_geometry.place_initial_window') as place:
            Node.menu(self.node)
            self.window.close()
            self.node._menuHasRaised = False
            Node.menu(self.node)
        place.assert_called_once_with(self.window, self.node.graph)


class TestWSLWindowPlacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.window = QtWidgets.QLabel('GPI window')
        self.window.setMinimumSize(100, 100)
        self.addCleanup(self.window.deleteLater)
        self.screen_rect = QtCore.QRect(-1920, 293, 1920, 1200)
        screen = SimpleNamespace(availableGeometry=lambda: self.screen_rect)
        self.reference = SimpleNamespace(window=lambda: SimpleNamespace(screen=lambda: screen))

    def test_initial_window_fits_nonzero_screen_origin(self):
        with patch.dict(os.environ, {'WSL_DISTRO_NAME': 'Ubuntu', 'WAYLAND_DISPLAY': 'wayland-0'}):
            place_initial_window(self.window, self.reference)
        geometry = self.window.geometry()
        self.assertTrue(self.screen_rect.contains(geometry))
        self.assertGreaterEqual(geometry.top(), self.screen_rect.top() + 32)
        self.assertGreaterEqual(geometry.left(), self.screen_rect.left() + 32)

    def test_large_startup_size_leaves_room_for_host_window_frame(self):
        with patch.dict(os.environ, {'WSL_DISTRO_NAME': 'Ubuntu', 'WAYLAND_DISPLAY': 'wayland-0'}):
            place_initial_window(
                self.window, self.reference, preferred_size=QtCore.QSize(2884, 898))
        geometry = self.window.geometry()
        self.assertLessEqual(geometry.width(), 1440)
        self.assertLessEqual(geometry.height(), 900)
        self.assertTrue(self.screen_rect.contains(geometry))

    def test_non_wsl_window_is_not_repositioned(self):
        self.window.move(123, 456)
        with patch.dict(os.environ, {'WSL_DISTRO_NAME': '', 'WAYLAND_DISPLAY': 'wayland-0'}):
            place_initial_window(self.window, self.reference)
        self.assertEqual(self.window.pos(), QtCore.QPoint(123, 456))

    def test_wslg_prefers_xwayland_without_overriding_backend(self):
        wslg = {'WSL_DISTRO_NAME': 'Ubuntu', 'WAYLAND_DISPLAY': 'wayland-0',
                'DISPLAY': ':0'}
        with patch.object(sys, 'platform', 'linux'), patch.dict(os.environ, wslg, clear=True):
            _configure_wslg_platform()
            self.assertEqual(os.environ['QT_QPA_PLATFORM'], 'xcb')
            os.environ['QT_QPA_PLATFORM'] = 'wayland'
            _configure_wslg_platform()
            self.assertEqual(os.environ['QT_QPA_PLATFORM'], 'wayland')

    def test_non_wslg_does_not_force_xwayland(self):
        with patch.object(sys, 'platform', 'linux'), \
                patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-0', 'DISPLAY': ':0'}, clear=True):
            _configure_wslg_platform()
            self.assertNotIn('QT_QPA_PLATFORM', os.environ)

    def test_recovers_title_bar_if_xwayland_overrides_initial_position(self):
        screen = self.reference.window().screen()
        with patch.dict(os.environ, {'WSL_DISTRO_NAME': 'Ubuntu', 'WAYLAND_DISPLAY': 'wayland-0'}), \
                patch.object(QtGui.QGuiApplication, 'platformName', return_value='xcb'), \
                patch.object(QtGui.QGuiApplication, 'screens', return_value=[screen]):
            place_initial_window(self.window, self.reference)
            self.window.show()
            self.window.move(self.screen_rect.left(), self.screen_rect.top() - 50)
            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(350, loop.quit)
            loop.exec()
        self.assertTrue(self.screen_rect.contains(self.window.frameGeometry()))

    def test_file_dialog_is_positioned_only_once(self):
        dialog = GPIFileDialog(self.window)
        self.addCleanup(dialog.deleteLater)
        self.addCleanup(dialog.hide)
        with patch('gpi.window_geometry.place_initial_window') as place:
            dialog.show()
            self.app.processEvents()
            dialog.hide()
            dialog.show()
            self.app.processEvents()
        place.assert_called_once_with(dialog, self.window)


if __name__ == '__main__':
    unittest.main()