import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from gpi import QtCore, QtGui, QtWidgets
from gpi.mainWindow import MainCanvas
from gpi.node import Node


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
                                    _nodeIF=self.widget, _menuHasRaised=False)
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


if __name__ == '__main__':
    unittest.main()