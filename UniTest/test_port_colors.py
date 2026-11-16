"""Port colors retain their state meanings across canvas themes."""

import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from gpi import QtCore, QtGui, QtWidgets
from gpi.defines import OPTIONAL, REQUIRED
from gpi.port import InPort, OutPort


class PortColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def make_port(self, port_class, **kwargs):
        data_type = SimpleNamespace(
            toolTip_Port=lambda: "Test data",
            toolTip_Data=lambda data: str(data),
            matchesData=lambda data: data is not None,
            setDataAttr=lambda data: data,
        )
        return port_class(None, None, "test", 0, intype=data_type, **kwargs)

    def assert_painted_color(self, port, color, pressed=False):
        option = QtWidgets.QStyleOptionGraphicsItem()
        if pressed:
            option.state |= QtWidgets.QStyle.State_Sunken
        for theme in ("Classic", "Dark"):
            for save_memory in (False, True):
                with self.subTest(theme=theme, save_memory=save_memory):
                    with patch("gpi.port.Config", SimpleNamespace(APPEARANCE_STYLE=theme)):
                        port.setMemSaver(save_memory)
                        painter = Mock()
                        port.paint(painter, option, None)
                        brush = QtGui.QBrush(painter.setBrush.call_args.args[0])
                        self.assertEqual(brush.style(), QtCore.Qt.SolidPattern)
                        self.assertEqual(brush.color(), QtGui.QColor(color))
                        if save_memory:
                            painter.drawPolygon.assert_called_once_with(port.portShape_memSave)
                        elif theme == "Classic":
                            painter.drawPolygon.assert_called_once_with(port.portShape)
                        else:
                            painter.drawPath.assert_called_once_with(port.portSemiPath)

    def test_input_obligation_and_output_data_states(self):
        required = self.make_port(InPort, obligation=REQUIRED)
        optional = self.make_port(InPort, obligation=OPTIONAL)
        self.assert_painted_color(required, "#2a82da")
        self.assert_painted_color(optional, "#5aac5a")

        output = self.make_port(OutPort)
        self.assert_painted_color(output, "#cc4444")
        self.assertTrue(output.setData(7))
        self.assert_painted_color(output, "#2a82da")
        output.setDataCalled(False)
        self.assert_painted_color(output, "#c8993a")
        output.setData(None)
        self.assert_painted_color(output, "#cc4444")
        self.assertTrue(output.setData(8))
        self.assert_painted_color(output, "#2a82da")

    def test_pressed_color_overrides_port_state(self):
        required = self.make_port(InPort, obligation=REQUIRED)
        optional = self.make_port(InPort, obligation=OPTIONAL)
        output = self.make_port(OutPort)
        output.setData(7)
        for port in (required, optional, output):
            self.assert_painted_color(port, "#cc4444", pressed=True)
        output.setDataCalled(False)
        self.assert_painted_color(output, "#cc4444", pressed=True)
        output.setData(None)
        self.assert_painted_color(output, "#cc4444", pressed=True)


if __name__ == "__main__":
    unittest.main()
