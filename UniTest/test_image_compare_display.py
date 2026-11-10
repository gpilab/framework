import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gpi
import numpy as np


def load_node(name):
    path = (Path(__file__).resolve().parent.parent / 'gpi_core' / 'display' / 'GPI'
            / (name + '_GPI.py'))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare = load_node('ImageCompareDisplay')
display = load_node('ImageDisplay')


class NodeHarness:
    def __init__(self, node_class, inputs, **settings):
        self.inputs = inputs
        self.values = {}
        self.attrs = {}
        self.outputs = {}
        self.viewport = Mock()
        self.node = node_class.__new__(node_class)
        self.node.addWidget = self.add_widget
        self.node.addInPort = Mock()
        self.node.addOutPort = Mock()
        self.node.getData = self.inputs.get
        self.node.getVal = self.values.__getitem__
        self.node.getAttr = self.get_attr
        self.node.setAttr = self.set_attr
        self.node.setData = self.outputs.__setitem__
        self.node.getWidget = Mock(return_value=self.viewport)
        self.node.widgetEvents = lambda: set()
        self.node.getLayoutDirection = lambda: 'Vertical'
        self.node.log = Mock()
        self.node.initUI()
        self.values.update({
            'L W F C:': {'floor': 0, 'ceiling': 100},
            'Comparison': {'transition': 0, 'swap': False, 'edge': 2},
            'Range Min': 0., 'Range Max': 1.,
            'Advanced Controls': False,
            'Viewport:': None,
        })
        self.values.update(settings)
        self.attrs['Viewport:', 'normalize_images'] = False
        self.attrs['Viewport:', 'loaded_mask'] = None
        self.attrs['Viewport:', 'roi_mask'] = None

    def add_widget(self, kind, title, **attrs):
        self.values[title] = attrs.get('val', 0)
        for key, value in attrs.items():
            self.attrs[title, key] = value

    def get_attr(self, title, attr):
        if attr == 'val':
            return self.values[title]
        return self.attrs[title, attr]

    def set_attr(self, title, **attrs):
        for key, value in attrs.items():
            self.attrs[title, key] = value
            if key == 'val' and not isinstance(value, gpi.QtGui.QImage):
                self.values[title] = value


class TestImageCompareDisplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = gpi.QtWidgets.QApplication.instance() or gpi.QtWidgets.QApplication([])

    def test_first_input_required_and_other_inputs_optional(self):
        harness = NodeHarness(compare.ExternalNode, {})
        harness.node.addInPort.assert_any_call(
            'inleft', 'NPYorTorch', obligation=gpi.REQUIRED,
            kind='numpy', drange=(2, 3))
        harness.node.addInPort.assert_any_call(
            'inright', 'NPYorTorch', obligation=gpi.OPTIONAL,
            kind='numpy', drange=(2, 3))
        harness.node.addInPort.assert_any_call(
            'mask', 'NPYarray', obligation=gpi.OPTIONAL,
            dtype=[np.bool_, np.uint8])

    def test_no_images_reports_error(self):
        harness = NodeHarness(compare.ExternalNode, {})
        self.assertEqual(harness.node.validate(), 1)
        self.assertEqual(harness.node.compute(), 1)
        self.assertEqual(harness.node.log.warn.call_count, 2)

    def test_comparison_operations_require_two_inputs(self):
        data = np.arange(30, dtype=float).reshape(5, 6)
        harness = NodeHarness(compare.ExternalNode, {})
        toolbar = compare.ComparisonToolbar('Comparison')
        viewport = compare.CompareViewBox('Viewport')
        self.addCleanup(toolbar.deleteLater)
        self.addCleanup(viewport.deleteLater)
        controls = (toolbar._mode, toolbar._swap, toolbar._edge,
                    viewport.normalizeCheckBox, viewport._exportgif_btn,
                    viewport.gifDurationSpinBox)
        for control in controls:
            self.assertFalse(control.isEnabled())
        toolbar.set_val({'transition': 6, 'swap': True, 'edge': 50})
        viewport.set_normalize_images(True)
        for inputs in ({'inleft': data}, {'inright': data},
                       {'inleft': data, 'inright': data}, {'inright': data}, {}):
            with self.subTest(inputs=tuple(inputs)):
                harness.inputs.clear()
                harness.inputs.update(inputs)
                self.assertEqual(harness.node.validate(), 0 if inputs else 1)
                enabled = len(inputs) == 2
                self.assertEqual(harness.attrs['Comparison', 'comparison_enabled'], enabled)
                self.assertEqual(harness.attrs['Viewport:', 'comparison_enabled'], enabled)
                toolbar.set_comparison_enabled(enabled)
                viewport.set_comparison_enabled(enabled)
                for control in controls:
                    self.assertEqual(control.isEnabled(), enabled)
                self.assertEqual(toolbar.get_val()['transition'], 6)
                self.assertTrue(toolbar.get_val()['swap'])
                self.assertTrue(viewport.get_normalize_images())
                self.assertTrue(viewport.imageLabel.isEnabled())
                if enabled:
                    viewport.set_gif_frames([gpi.QtGui.QImage(), gpi.QtGui.QImage()])
                    viewport.set_mirror_offset(6)
                else:
                    self.assertFalse(viewport._gif_frames)
                    self.assertIsNone(viewport.get_mirror_offset())

    def test_single_input_matches_image_display(self):
        real = np.arange(30, dtype=float).reshape(5, 6) - 9
        complex_data = real * np.exp(1j * real / 7)
        volume = np.stack([real, real + 10, real + 20])
        rgb = np.arange(90, dtype=np.uint8).reshape(5, 6, 3)
        cases = [
            (real, {}),
            (real, {'Complex Display': 1}),
            (real, {'Color Map': 3, 'Gamma': 1.5}),
            (complex_data, {}),
            (complex_data, {'Complex Display': 3}),
            (volume, {'Slice': 2}),
            (volume, {'Extra Dimension': 1}),
            (rgb, {}),
        ]
        for port in ('inleft', 'inright'):
            for data, settings in cases:
                with self.subTest(port=port, shape=data.shape, settings=settings):
                    harness = NodeHarness(compare.ExternalNode, {port: data}, **settings)
                    reference = NodeHarness(display.ExternalNode, {'in': data}, **settings)
                    self.assertEqual(harness.node.validate(), 0)
                    self.assertEqual(reference.node.validate(), 0)
                    self.assertEqual(harness.node.compute(), 0)
                    self.assertEqual(reference.node.compute(), 0)
                    np.testing.assert_array_equal(harness.outputs['out'],
                                                  reference.outputs['out'])
                    self.assertFalse(harness.attrs['Comparison', 'visible'])
                    self.assertFalse(harness.attrs['Viewport:', 'comparison_enabled'])
                    connected_output = 'outleft' if port == 'inleft' else 'outright'
                    absent_output = 'outright' if port == 'inleft' else 'outleft'
                    np.testing.assert_array_equal(harness.outputs[connected_output],
                                                  reference.outputs['out'])
                    self.assertIsNone(harness.outputs[absent_output])
                    self.assertIsNone(harness.attrs['Viewport:', 'mirror_offset'])
                    harness.viewport.set_gif_frames.assert_called_with(None)
                    image = harness.attrs['Viewport:', 'val']
                    np.testing.assert_array_equal(
                        image.pixelColor(0, 0).getRgb(), harness.outputs['out'][0, 0])

    def test_saved_comparison_settings_do_not_change_single_image(self):
        data = np.arange(30, dtype=float).reshape(5, 6)
        for port in ('inleft', 'inright'):
            reference = NodeHarness(compare.ExternalNode, {port: data})
            reference.node.compute()
            for transition in range(7):
                with self.subTest(port=port, transition=transition):
                    settings = {'transition': transition, 'swap': True, 'edge': 70}
                    harness = NodeHarness(compare.ExternalNode, {port: data},
                                          Comparison=settings)
                    harness.attrs['Viewport:', 'normalize_images'] = True
                    self.assertEqual(harness.node.compute(), 0)
                    np.testing.assert_array_equal(harness.outputs['out'],
                                                  reference.outputs['out'])
                    self.assertEqual(harness.values['Comparison'], settings)

    def test_single_image_masks_roi_and_hover(self):
        data = np.arange(30, dtype=float).reshape(5, 6)
        mask = np.zeros(data.shape, dtype=np.uint8)
        mask[1:3, 2:4] = 1
        for port in ('inleft', 'inright'):
            with self.subTest(port=port):
                harness = NodeHarness(compare.ExternalNode, {port: data, 'mask': mask})
                harness.attrs['Viewport:', 'roi_mask'] = mask
                self.assertEqual(harness.node.compute(), 0)
                np.testing.assert_array_equal(harness.outputs['roi'], mask)
                stats = harness.attrs['Viewport:', 'stats_text']
                self.assertIn(f'mean={data[mask > 0].mean():.4g}', stats)
                self.assertNotIn('RMSE', stats)
                self.assertNotIn('empty', stats)
                self.assertNotIn('mean(L-R)', stats)
                self.assertFalse(np.array_equal(
                    harness.outputs['out'][mask > 0],
                    harness.outputs['outleft' if port == 'inleft' else 'outright'][mask > 0]))
                widget = compare.CompareViewBox('Test')
                self.addCleanup(widget.deleteLater)
                for name in ('rawdata_left', 'rawdata_right', 'rawphys_left', 'rawphys_right'):
                    getattr(widget, 'set_' + name)(harness.attrs['Viewport:', name])
                widget._show_hover(1, 2)
                self.assertIn('8', widget._hover_lbl.text())
                self.assertNotIn('L-R', widget._hover_lbl.text())
                widget._show_hover(99, 99)
                self.assertIn('out of bounds', widget._hover_lbl.text())
                widget.imageLabel._rois = [
                    {'type': 'Rectangle', 'p1': (1, 1), 'p2': (3, 3)}]
                widget._request_send_roi()
                roi = widget.get_roi_mask()
                self.assertEqual(roi.shape, data.shape)
                self.assertTrue(roi.any())
                with patch.object(gpi.QtWidgets.QFileDialog, 'getSaveFileName',
                                  return_value=('test_roi.npy', '')), \
                        patch.object(compare.np, 'save') as save:
                    widget._save_mask_to_file()
                save.assert_called_once()
                np.testing.assert_array_equal(save.call_args.args[1], roi)
                widget.set_comparison_enabled(False)
                self.assertFalse(widget.normalizeCheckBox.isEnabled())
                widget.set_comparison_enabled(True)
                self.assertTrue(widget.normalizeCheckBox.isEnabled())

    def test_reconnecting_restores_comparison_and_disconnect_clears_missing_side(self):
        left = np.arange(30, dtype=float).reshape(5, 6)
        right = left[::-1].copy()
        harness = NodeHarness(compare.ExternalNode, {'inleft': left, 'inright': right},
                              **{'Complex Display': 0})
        for transition in range(7):
            with self.subTest(transition=transition):
                harness.values['Comparison'] = {
                    'transition': transition, 'swap': False, 'edge': 2}
                self.assertEqual(harness.node.validate(), 0)
                self.assertEqual(harness.node.compute(), 0)
                self.assertTrue(harness.attrs['Comparison', 'visible'])
                self.assertIsNotNone(harness.outputs['outleft'])
                self.assertIsNotNone(harness.outputs['outright'])
                if transition == 5:
                    np.testing.assert_array_equal(
                        harness.outputs['out'],
                        np.concatenate((harness.outputs['outleft'],
                                        harness.outputs['outright']), axis=1))
                harness.inputs['inleft'] = None
                self.assertEqual(harness.node.validate(), 0)
                self.assertEqual(harness.node.compute(), 0)
                self.assertFalse(harness.attrs['Comparison', 'visible'])
                self.assertIsNone(harness.outputs['outleft'])
                np.testing.assert_array_equal(harness.outputs['out'],
                                              harness.outputs['outright'])
                harness.inputs['inleft'] = left


if __name__ == '__main__':
    unittest.main()
