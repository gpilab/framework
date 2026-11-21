import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
import gpi


path = Path(__file__).resolve().parent.parent / 'gpi_core' / 'display' / 'GPI' / 'Matplotlib_GPI.py'
spec = importlib.util.spec_from_file_location('matplotlib_node', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestMatplotlibColors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = gpi.QtWidgets.QApplication.instance() or gpi.QtWidgets.QApplication([])

    def setUp(self):
        with patch.object(module, '_load_mpl_colors', return_value={}):
            self.widget = module.MatplotDisplay('Plot')
        self.addCleanup(self.widget.deleteLater)
        self.addCleanup(self.widget._updatetimer.stop)
        self.widget.set_xline(False)
        self.widget.set_yline(False)

    def draw(self, data):
        self.widget.set_val(data)
        self.widget._updatetimer.stop()
        self.widget._on_draw()
        self.widget._updatetimer.stop()
        return list(self.widget.axes.lines)

    def test_columns_use_successive_palette_colors(self):
        data = np.arange(300).reshape(100, 3)
        lines = self.draw([data])
        self.assertEqual([line.get_color() for line in lines],
                         self.widget._port_colors[:3])
        for column, line in enumerate(lines):
            np.testing.assert_array_equal(line.get_ydata(), data[:, column])

    def test_hold_continues_colors_across_input_updates(self):
        data = np.arange(300).reshape(100, 3)
        original = self.draw([data])
        self.widget._hold_btn.set_val(True)
        lines = self.draw([data + 1])
        self.assertEqual(lines[:3], original)
        self.assertEqual([line.get_color() for line in lines],
                         self.widget._port_colors[:6])
        np.testing.assert_array_equal(lines[-1].get_ydata(), data[:, 2] + 1)

    def test_multiple_inputs_and_xy_pairs_share_color_cycle(self):
        data = np.arange(100)
        xy = np.column_stack((data, data ** 2))
        lines = self.draw([('in0', np.column_stack((data, data + 1, data + 2))),
                           ('in4', xy), ('in7', data)])
        self.assertEqual([line.get_color() for line in lines],
                         self.widget._port_colors[:5])
        self.assertEqual([line.get_label() for line in lines],
                         ['in0', 'in0', 'in0', 'in4', 'in7'])
        np.testing.assert_array_equal(lines[3].get_xdata(), xy[:, 0])
        np.testing.assert_array_equal(lines[3].get_ydata(), xy[:, 1])

    def test_disabling_hold_clears_lines_and_restarts_custom_palette(self):
        self.widget._port_colors = ['#abcdef', '#fedcba', '#123456']
        data = np.arange(100)
        self.draw([data])
        self.widget._hold_btn.set_val(True)
        self.draw([data + 1])
        self.widget._hold_btn.set_val(False)
        lines = self.draw([data + 2])
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].get_color(), '#abcdef')
        np.testing.assert_array_equal(lines[0].get_ydata(), data + 2)

    def test_hold_before_first_draw_cycles_through_custom_palette(self):
        self.widget._port_colors = ['#abcdef', '#fedcba']
        self.widget._hold_btn.set_val(True)
        data = np.arange(100)
        for count in range(1, 4):
            lines = self.draw([data + count])
            self.assertEqual([line.get_color() for line in lines],
                             ['#abcdef', '#fedcba', '#abcdef'][:count])

    def test_hold_cycles_single_input_without_reference_lines_consuming_colors(self):
        self.widget.set_xline(True)
        self.widget.set_yline(True)
        data = np.arange(100)
        self.draw([data])
        self.widget._hold_btn.set_val(True)
        for update in range(1, 4):
            self.draw([data + update])
        curves = [line for line in self.widget.axes.lines
                  if line.get_label() == 'in0']
        self.assertEqual([line.get_color() for line in curves],
                         self.widget._port_colors[:4])

    def test_resizing_preserves_plot_shape_limits_and_held_curves(self):
        original = self.draw([np.arange(100)])
        width, height = self.widget.fig.get_size_inches()
        margins = self.widget._subplotPosition
        expected_ratio = (height * (margins['top'] - margins['bottom'])
                          / (width * (margins['right'] - margins['left'])))
        xlim = self.widget.axes.get_xlim()
        ylim = self.widget.axes.get_ylim()
        self.widget._hold_btn.set_val(True)
        self.widget.show()
        self.addCleanup(self.widget.close)
        for size in ((1600, 700), (900, 1200), (1200, 900)):
            with self.subTest(size=size):
                self.widget.resize(*size)
                self.app.processEvents()
                self.widget.canvas.draw()
                bounds = self.widget.axes.get_window_extent()
                self.assertAlmostEqual(bounds.height / bounds.width,
                                       expected_ratio, places=6)
                self.assertEqual(self.widget.axes.get_xlim(), xlim)
                self.assertEqual(self.widget.axes.get_ylim(), ylim)
                self.assertEqual(list(self.widget.axes.lines), original)

        # Clearing the axes on a fresh input must retain the resize behavior.
        self.widget._hold_btn.set_val(False)
        self.draw([np.arange(100) + 1])
        bounds = self.widget.axes.get_window_extent()
        self.assertAlmostEqual(bounds.height / bounds.width,
                               expected_ratio, places=6)

    def test_two_columns_toggle_switches_between_xy_and_overlaid_curves(self):
        data = np.column_stack((np.arange(100) + 10, np.arange(100) ** 2))
        lines = self.draw([data])
        self.assertEqual(len(lines), 1)
        np.testing.assert_array_equal(lines[0].get_xdata(), data[:, 0])
        np.testing.assert_array_equal(lines[0].get_ydata(), data[:, 1])

        self.widget._two_columns_btn.set_val(True)
        self.widget._two_columns_btn.valueChanged.emit(True)
        self.assertTrue(self.widget._updatetimer.isActive())
        self.widget._updatetimer.stop()
        self.widget._on_draw()
        lines = list(self.widget.axes.lines)
        self.assertEqual(len(lines), 2)
        self.assertEqual([line.get_color() for line in lines],
                         self.widget._port_colors[:2])
        for column, line in enumerate(lines):
            np.testing.assert_array_equal(line.get_xdata(), np.arange(100))
            np.testing.assert_array_equal(line.get_ydata(), data[:, column])

        self.widget._two_columns_btn.set_val(False)
        lines = self.draw([data])
        self.assertEqual(len(lines), 1)
        np.testing.assert_array_equal(lines[0].get_xdata(), data[:, 0])

    def test_two_columns_button_visibility_tracks_inputs_and_collapsed_panel(self):
        button = self.widget._two_columns_btn
        self.assertTrue(button.isHidden())
        self.draw([np.arange(100), ('in1', np.zeros((100, 2)))])
        self.assertFalse(button.isHidden())
        self.widget.set_collapsed(True)
        self.assertTrue(button.isHidden())
        self.widget.set_collapsed(False)
        self.assertFalse(button.isHidden())
        for data in ([np.zeros((100, 3))], [np.arange(2)], []):
            self.draw(data)
            self.assertTrue(button.isHidden())
            self.widget.set_collapsed(False)
            self.assertTrue(button.isHidden())

    def test_two_columns_mode_preserves_hold_color_cycling(self):
        self.widget._two_columns_btn.set_val(True)
        data = np.arange(200).reshape(100, 2)
        original = self.draw([data])
        self.widget._hold_btn.set_val(True)
        lines = self.draw([data + 1])
        self.assertEqual(lines[:2], original)
        self.assertEqual([line.get_color() for line in lines],
                         self.widget._port_colors[:4])


if __name__ == '__main__':
    unittest.main()
