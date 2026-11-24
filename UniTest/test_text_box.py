import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from gpi import QtWidgets
from gpi.widgets import ExclusivePushButtons, TextBox


class TextBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_long_info_wraps_when_scroll_area_is_narrowed(self):
        text = TextBox("Info")
        value = "Phantom information includes a long description " * 20
        text.set_val(value)
        buttons = ExclusivePushButtons("Mode")
        buttons.set_buttons(["First", "Second"])
        content = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(content)
        layout.addWidget(buttons, 0, 0)
        layout.addWidget(text, 1, 0)
        area = QtWidgets.QScrollArea()
        area.setWidget(content)
        area.setWidgetResizable(True)
        area.resize(800, 200)
        area.show()
        self.app.processEvents()
        self.app.processEvents()
        wide_height = text.wdg.height()
        wide_button_width = buttons.buttons[0].width()

        area.resize(300, 200)
        self.app.processEvents()
        self.app.processEvents()
        self.assertEqual(area.horizontalScrollBar().maximum(), 0)
        self.assertLess(buttons.buttons[0].width(), wide_button_width)
        self.assertGreater(text.wdg.height(), wide_height)
        self.assertGreaterEqual(text.wdg.height(), text.wdg.heightForWidth(text.wdg.width()))
        self.assertEqual(text.get_val(), value)
        area.close()

    def test_wordwrap_can_be_disabled(self):
        text = TextBox("Info")
        text.set_wordwrap(False)
        self.assertFalse(text.get_wordwrap())


if __name__ == "__main__":
    unittest.main()
