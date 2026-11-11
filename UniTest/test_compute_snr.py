import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, call, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gpi
import numpy as np


path = (Path(__file__).resolve().parent.parent / 'gpi_core' / 'fileIO' / 'GPI'
        / 'ComputeSNR_GPI.py')
spec = importlib.util.spec_from_file_location('ComputeSNR', path)
snr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snr)


class TestComputeSNRInputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = gpi.QtWidgets.QApplication.instance() or gpi.QtWidgets.QApplication([])

    def make_node(self):
        return snr.ExternalNode.__new__(snr.ExternalNode)

    def test_only_required_inputs_are_registered(self):
        node = self.make_node()
        node.addWidget = Mock()
        node.addInPort = Mock()
        node.addOutPort = Mock()
        node.initUI()
        self.assertEqual(node.addInPort.call_args_list, [
            call('in', 'NPYarray', obligation=gpi.REQUIRED),
            call('Metadata', 'DICT', obligation=gpi.REQUIRED),
        ])
        self.assertEqual(node.addOutPort.call_args_list, [
            call(title, 'NPYarray') for title in
            ('coil_snr', 'combined_snr', 'coil_images', 'rss', 'noise_covariance')
        ] + [call('SNR Metadata', 'DICT')])
        self.assertEqual([entry.args[1] for entry in node.addWidget.call_args_list], [
            'SNR Info:', 'Acquisition', 'SNR Method', 'Remove Oversampling',
            'Power Bias Correction', 'Noise Std Scale', 'Covariance Floor', 'Compute'])

    def test_both_methods_compute_without_a_noise_port(self):
        for split in (False, True):
            with self.subTest(split=split):
                node = self.make_node()
                inputs = {'in': np.zeros((2, 2, 4, 6), dtype=np.complex64),
                          'Metadata': {}}
                settings = {'Compute': True, 'Acquisition': 0, 'SNR Method': int(split),
                            'Remove Oversampling': True, 'Noise Std Scale': 1.,
                            'Power Bias Correction': True, 'Covariance Floor': 1e-6}
                outputs = {}
                node.getData = Mock(side_effect=inputs.__getitem__)
                node.getVal = settings.__getitem__
                node.setData = outputs.__setitem__
                node.setAttr = Mock()
                node.log = Mock()
                images = np.full((2, 2, 4, 6), 10 + 2j, dtype=np.complex64)
                covariance = np.eye(2, dtype=np.complex128)[None]
                details = {'axes': ['chan', 'frame' if split else 'dyn', 'y', 'x'],
                           'dynamic_ids': [0, 1], 'noise_std_scale': 1.}
                with patch.object(snr, 'reconstruct_cartesian',
                                  return_value=(images, covariance, details)) as reconstruct:
                    self.assertEqual(node.compute(), 0)
                self.assertEqual(node.getData.call_args_list,
                                 [call('in'), call('Metadata')])
                self.assertIsNone(reconstruct.call_args.args[1])
                self.assertEqual(reconstruct.call_args.kwargs['use_rf_off'], not split)
                self.assertEqual(reconstruct.call_args.kwargs['use_readout_split'], split)
                self.assertEqual(outputs['combined_snr'].shape, (6, 4))
                self.assertTrue(np.isfinite(outputs['combined_snr']).all())
                np.testing.assert_array_equal(outputs['noise_covariance'], covariance[0])
                self.assertEqual(set(outputs), {'coil_snr', 'combined_snr', 'coil_images',
                                                'rss', 'noise_covariance', 'SNR Metadata'})
                self.assertNotIn('g_factor_prediction', outputs['SNR Metadata'])

    def test_disabled_or_failed_compute_clears_registered_outputs(self):
        for enabled, acquisition, expected in ((False, 0, 0), (True, 1, 1)):
            with self.subTest(enabled=enabled):
                node = self.make_node()
                node.getVal = {'Compute': enabled, 'Acquisition': acquisition}.__getitem__
                outputs = {}
                node.setData = outputs.__setitem__
                node.setAttr = Mock()
                node.log = Mock()
                self.assertEqual(node.compute(), expected)
                self.assertEqual(set(outputs), {'coil_snr', 'combined_snr', 'coil_images',
                                                'rss', 'noise_covariance', 'SNR Metadata'})
                self.assertTrue(all(value is None for value in outputs.values()))

    def test_noise_controls_use_supported_widget_setters(self):
        node = self.make_node()
        parent = gpi.QtWidgets.QWidget()
        self.addCleanup(parent.deleteLater)
        widgets = {}

        def set_attr(title, **attrs):
            for key, value in attrs.items():
                gpi.NodeAPI.modifyWidget_setter(node, widgets[title], key, value)

        def add_widget(kind, title, **attrs):
            widgets[title] = getattr(gpi, kind)(title, parent)
            set_attr(title, **attrs)

        node.addWidget = add_widget
        node.addInPort = Mock()
        node.addOutPort = Mock()
        node.getVal = lambda title: widgets[title].get_val()
        node.setAttr = set_attr
        node.initUI()
        for split in (False, True, False):
            set_attr('SNR Method', val=int(split))
            self.assertEqual(node.validate(), 0)
            self.assertEqual(widgets['Remove Oversampling'].isHidden(), split)
            if split:
                self.assertTrue(widgets['Remove Oversampling'].get_val())

    def test_snr_outputs_follow_native_axes_and_orientation(self):
        for dimensions in (2, 3):
            for split in (False, True):
                with self.subTest(dimensions=dimensions, split=split):
                    node = self.make_node()
                    shape = (4, 4, 6) if dimensions == 3 else (4, 6)
                    coils = 4 if dimensions == 3 else 2
                    maps = np.zeros((coils,) + shape, dtype=np.complex64)
                    for coil in range(coils):
                        if dimensions == 3:
                            maps[coil, coil // 2 * 2:coil // 2 * 2 + 2,
                                 coil % 2 * 2:coil % 2 * 2 + 2] = 10
                        else:
                            maps[coil, coil * 2:coil * 2 + 2] = 10
                    images = np.stack((maps, np.ones_like(maps)), axis=1)
                    covariance = np.eye(coils, dtype=np.complex128)[None]
                    axes = ['chan', 'frame' if split else 'dyn']
                    axes += ['z', 'y', 'x'] if dimensions == 3 else ['y', 'x']
                    details = {'axes': axes, 'dynamic_ids': [0, 1], 'noise_std_scale': 1.}
                    settings = {'Compute': True, 'Acquisition': 0, 'SNR Method': int(split),
                                'Remove Oversampling': True, 'Noise Std Scale': 1.,
                                'Power Bias Correction': False, 'Covariance Floor': 1e-6}
                    outputs = {}
                    node.getVal = settings.__getitem__
                    node.getData = {'in': images, 'Metadata': {}}.__getitem__
                    node.setData = outputs.__setitem__
                    node.setAttr = Mock()
                    node.log = Mock()
                    with patch.object(snr, 'reconstruct_cartesian',
                                      return_value=(images, covariance, details)):
                        self.assertEqual(node.compute(), 0)
                    expected_images = maps
                    if dimensions == 3:
                        expected_images = np.flip(expected_images, axis=-3)
                    expected_images = np.rot90(expected_images, axes=(-2, -1))
                    np.testing.assert_array_equal(outputs['coil_images'], expected_images)
                    np.testing.assert_allclose(outputs['coil_snr'], np.abs(expected_images))
                    np.testing.assert_allclose(outputs['combined_snr'], 10)
                    np.testing.assert_allclose(outputs['rss'][0], 10)
                    np.testing.assert_allclose(outputs['rss'][1], np.sqrt(coils))
                    self.assertNotIn('g_factor_prediction', outputs['SNR Metadata'])


if __name__ == '__main__':
    unittest.main()