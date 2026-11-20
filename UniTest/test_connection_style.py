"""Dark connection styles, Classic behavior, and settings persistence."""

import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from gpi import QtCore, QtWidgets
from gpi.associate import Bindings
from gpi.config import ConfigManager
from gpi.edge import Edge
from gpi.port import InPort, OutPort
from gpi.settings_dialog import SettingsDialog


class ConnectionStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.settings_file = Path(folder.name) / "gpi_settings.json"
        self.settings_file.write_text(
            json.dumps({"APPEARANCE": {"STYLE": "Dark"}}), encoding="utf-8")
        for target, value in (
            ("gpi.config.GPI_SETTINGS_FILE", str(self.settings_file)),
            ("gpi.config.GPI_CONFIG_DIR", folder.name),
        ):
            patched = patch(target, value)
            patched.start()
            self.addCleanup(patched.stop)
        bindings = patch.dict(Bindings._db)
        bindings.start()
        self.addCleanup(bindings.stop)
        self.config = ConfigManager()

    def test_default_persistence_and_reset(self):
        self.assertEqual(self.config.CONNECTION_STYLE, "Curly")
        self.config.CONNECTION_STYLE = "Straight"
        self.config.saveConfigFile()
        self.assertEqual(
            json.loads(self.settings_file.read_text())["APPEARANCE"]["CONNECTION_STYLE"],
            "Straight")
        loaded = ConfigManager()
        self.assertEqual(loaded.CONNECTION_STYLE, "Straight")
        loaded._appearance_style = "Classic"
        loaded.saveConfigFile()
        self.assertEqual(ConfigManager().CONNECTION_STYLE, "Straight")
        loaded.resetToDefaults()
        self.assertEqual(ConfigManager().CONNECTION_STYLE, "Curly")

    def test_invalid_setting_is_reported(self):
        self.settings_file.write_text(json.dumps({
            "APPEARANCE": {"STYLE": "Dark", "CONNECTION_STYLE": "invalid"}
        }), encoding="utf-8")
        with patch("gpi.config.log.warn") as warning:
            self.config.loadConfigFile()
        warning.assert_called_once()
        self.assertEqual(self.config.CONNECTION_STYLE, "Curly")
        with self.assertRaises(ValueError):
            self.config.CONNECTION_STYLE = "invalid"

    def test_general_setting_visibility_apply_and_cancel(self):
        with patch("gpi.settings_dialog.Config", self.config), \
                patch.object(SettingsDialog, "_create_gpu_box", return_value=None), \
                patch.object(SettingsDialog, "_preview_theme"), \
                patch.object(SettingsDialog, "_revert_theme"):
            dialog = SettingsDialog()
            self.addCleanup(dialog.deleteLater)
            self.assertEqual(dialog.tabWidget.tabText(0), "General")
            self.assertEqual(dialog.connectionStyleCombo.currentText(), "Curly")
            self.assertFalse(dialog.connectionStyleCombo.isHidden())
            label = dialog._appearance_form.labelForField(dialog.connectionStyleCombo)
            dialog.themeCombo.setCurrentText("Classic")
            self.assertTrue(dialog.connectionStyleCombo.isHidden())
            self.assertTrue(label.isHidden())
            dialog.themeCombo.setCurrentText("Dark")
            self.assertFalse(dialog.connectionStyleCombo.isHidden())
            self.assertFalse(label.isHidden())

            applied = Mock()
            dialog.settings_applied.connect(applied)
            dialog.connectionStyleCombo.setCurrentText("Straight")
            dialog._apply()
            applied.assert_called_once()
            self.assertEqual(ConfigManager().CONNECTION_STYLE, "Straight")
            dialog.connectionStyleCombo.setCurrentText("Curly")
            dialog._on_reject()
            self.assertEqual(self.config.CONNECTION_STYLE, "Straight")
            self.assertEqual(ConfigManager().CONNECTION_STYLE, "Straight")

    def test_edge_rendering_switches_only_in_dark(self):
        data_type = SimpleNamespace(
            toolTip_Port=lambda: "Test data",
            toolTip_Data=lambda data: "",
            edgeTip=lambda data: "",
        )
        source = OutPort(None, None, "out", 0, intype=data_type)
        dest = InPort(None, None, "in", 0, intype=data_type)
        dest.setPos(100, 80)
        edge = Edge(source, dest)
        settings = SimpleNamespace(
            APPEARANCE_STYLE="Dark", LAYOUT_DIRECTION="Horizontal",
            CONNECTION_STYLE="Curly")
        with patch("gpi.edge.Config", settings):
            for theme in ("Classic", "Dark"):
                for direction in ("Horizontal", "Vertical"):
                    settings.APPEARANCE_STYLE = theme
                    settings.LAYOUT_DIRECTION = direction
                    edge.adjust()
                    for style in ("Curly", "Straight", "Curly"):
                        with self.subTest(theme=theme, direction=direction, style=style):
                            settings.CONNECTION_STYLE = style
                            edge.adjust()
                            if theme == "Dark":
                                self.assertEqual(
                                    edge.sourcePoint, edge.mapFromItem(source, 3.5, 0))
                                self.assertEqual(
                                    edge.destPoint, edge.mapFromItem(dest, 3.5, 3.5))
                            painter = Mock()
                            edge.paint(painter, QtWidgets.QStyleOptionGraphicsItem(), None)
                            if theme == "Classic" or style == "Straight":
                                painter.drawLine.assert_called_once_with(
                                    QtCore.QLineF(edge.sourcePoint, edge.destPoint))
                                painter.drawPath.assert_not_called()
                            else:
                                painter.drawLine.assert_not_called()
                                path = painter.drawPath.call_args.args[0]
                                self.assertEqual(path.elementCount(), 4)
                                self.assertEqual(path.pointAtPercent(0), edge.sourcePoint)
                                self.assertEqual(path.pointAtPercent(1), edge.destPoint)
                                control = path.elementAt(1)
                                if direction == "Horizontal":
                                    self.assertGreater(control.x, edge.sourcePoint.x())
                                    self.assertEqual(control.y, edge.sourcePoint.y())
                                else:
                                    self.assertEqual(control.x, edge.sourcePoint.x())
                                    self.assertGreater(control.y, edge.sourcePoint.y())


if __name__ == "__main__":
    unittest.main()
