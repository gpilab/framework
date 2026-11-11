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

    def test_both_methods_compute_without_a_noise_port(self):
        for split in (False, True):
            with self.subTest(split=split):
                node = self.make_node()
                inputs = {'in': np.zeros((2, 2, 4, 6), dtype=np.complex64),
                          'Metadata': {}}
                settings = {'Compute': True, 'Acquisition': 0, 'SNR Method': int(split),
                            'Remove Oversampling': True, 'Noise Std Scale': 1.,
                            'Power Bias Correction': True, 'Covariance Floor': 1e-6,
                            'Predict g-factor': False}
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
                for title in ('g_factor', 'predicted_snr', 'sensitivity_maps', 'g_factor_mask'):
                    self.assertIsNone(outputs[title])

    def test_invalid_prediction_retains_snr_and_clears_prediction_outputs(self):
        for shape, acceleration_y, acceleration_z in (((5, 4, 6), 2, 2),
                                                       ((4, 6), 3, 1)):
            with self.subTest(shape=shape):
                node = self.make_node()
                images = np.full((2, 2) + shape, 10 + 2j, dtype=np.complex64)
                covariance = np.eye(2, dtype=np.complex128)[None]
                settings = {'Compute': True, 'Acquisition': 0, 'SNR Method': 0,
                            'Remove Oversampling': True, 'Noise Std Scale': 1.,
                            'Power Bias Correction': True, 'Covariance Floor': 1e-6,
                            'Predict g-factor': True, 'g-factor R y': acceleration_y,
                            'g-factor R z': acceleration_z,
                            'Sensitivity Smoothing (voxels)': 2., 'Sensitivity Mask (%)': 5.}
                outputs = dict.fromkeys(('g_factor', 'predicted_snr', 'sensitivity_maps',
                                         'g_factor_mask'), 'stale')
                node.getVal = settings.__getitem__
                node.getData = {'in': images, 'Metadata': {}}.__getitem__
                node.setData = outputs.__setitem__
                node.setAttr = Mock()
                node.log = Mock()
                axes = ['chan', 'dyn'] + (['z', 'y', 'x'] if len(shape) == 3 else ['y', 'x'])
                details = {'axes': axes, 'dynamic_ids': [0, 1], 'noise_std_scale': 1.}
                with patch.object(snr, 'reconstruct_cartesian',
                                  return_value=(images, covariance, details)), \
                        patch.object(snr, 'estimate_sensitivity_maps') as estimate:
                    self.assertEqual(node.compute(), 0)
                estimate.assert_not_called()
                self.assertTrue(np.isfinite(outputs['combined_snr']).all())
                for title in ('g_factor', 'predicted_snr', 'sensitivity_maps', 'g_factor_mask'):
                    self.assertIsNone(outputs[title])
                prediction = outputs['SNR Metadata']['g_factor_prediction']
                self.assertTrue(prediction['enabled'])
                self.assertFalse(prediction['available'])
                self.assertIn('Compatible R y:', prediction['reason'])
                self.assertIn('SNR retained', node.setAttr.call_args.kwargs['val'])

    def test_prediction_controls_use_supported_widget_setters(self):
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
        controls = ('g-factor R y', 'g-factor R z', 'Sensitivity Smoothing (voxels)',
                    'Sensitivity Mask (%)')
        for enabled in (False, True, False):
            set_attr('Predict g-factor', val=enabled)
            self.assertEqual(node.validate(), 0)
            for title in controls:
                self.assertEqual(widgets[title].isHidden(), not enabled)
        self.assertEqual(widgets['g-factor R y'].get_val(), 2)
        self.assertEqual(widgets['g-factor R z'].get_val(), 1)

    def test_prediction_outputs_follow_native_axes_and_orientation(self):
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
                                'Power Bias Correction': False, 'Covariance Floor': 1e-6,
                                'Predict g-factor': True, 'g-factor R y': 2,
                                'g-factor R z': 2 if dimensions == 3 else 1,
                                'Sensitivity Smoothing (voxels)': 0.,
                                'Sensitivity Mask (%)': 0.}
                    outputs = {}
                    node.getVal = settings.__getitem__
                    node.getData = {'in': images, 'Metadata': {}}.__getitem__
                    node.setData = outputs.__setitem__
                    node.setAttr = Mock()
                    node.log = Mock()
                    with patch.object(snr, 'reconstruct_cartesian',
                                      return_value=(images, covariance, details)):
                        self.assertEqual(node.compute(), 0)
                    np.testing.assert_allclose(outputs['g_factor'], 1, atol=1e-6)
                    self.assertTrue(outputs['g_factor_mask'].all())
                    np.testing.assert_allclose(outputs['predicted_snr'],
                                               outputs['combined_snr'] / np.sqrt(coils))
                    expected_maps = maps / 10
                    if dimensions == 3:
                        expected_maps = np.flip(expected_maps, axis=-3)
                    expected_maps = np.rot90(expected_maps, axes=(-2, -1))
                    np.testing.assert_array_equal(outputs['sensitivity_maps'], expected_maps)
                    np.testing.assert_array_equal(outputs['coil_images'], expected_maps * 10)
                    info = outputs['SNR Metadata']['g_factor_prediction']
                    self.assertEqual(info['total_acceleration'], coils)
                    self.assertEqual(info['singular_voxels'], 0)


class TestAnalyticalGFactor(unittest.TestCase):
    def test_unaccelerated_and_orthogonal_encoding_have_unit_g(self):
        maps = np.zeros((2, 4, 3), dtype=np.complex64)
        maps[0, :2] = 1
        maps[1, 2:] = 1
        for acceleration in (1, 2):
            factor = snr.calculate_g_factor(maps, np.eye(2), acceleration_y=acceleration)
            np.testing.assert_allclose(factor, 1, atol=1e-6)

    def test_correlated_noise_matches_analytical_solution(self):
        maps = np.zeros((2, 4, 3), dtype=np.complex64)
        maps[0, :2] = 1
        maps[1, 2:] = 1
        correlation = 0.6j
        covariance = np.array([[1, correlation], [correlation.conjugate(), 1]])
        factor = snr.calculate_g_factor(maps, covariance, acceleration_y=2)
        np.testing.assert_allclose(factor, 1 / np.sqrt(1 - abs(correlation) ** 2),
                                   atol=1e-6)

    def test_indistinguishable_coils_are_singular_not_unit_g(self):
        maps = np.ones((2, 4, 3), dtype=np.complex64)
        factor = snr.calculate_g_factor(maps, np.eye(2), acceleration_y=2)
        self.assertTrue(np.isinf(factor).all())

    def test_three_dimensional_prediction_matches_direct_matrix_inverse(self):
        rng = np.random.default_rng(42)
        maps = rng.normal(size=(8, 4, 6, 3)) + 1j * rng.normal(size=(8, 4, 6, 3))
        noise = rng.normal(size=(8, 8)) + 1j * rng.normal(size=(8, 8))
        covariance = noise @ noise.conj().T + np.eye(8)
        support = np.ones((4, 6, 3), dtype=bool)
        support[0, 0, 0] = False
        factor = snr.calculate_g_factor(maps, covariance, acceleration_y=3,
                                         acceleration_z=2, support=support)
        expected = np.full(support.shape, np.nan)
        for base_z in range(2):
            for base_y in range(2):
                for position_x in range(3):
                    positions = [(base_z + offset_z * 2, base_y + offset_y * 2, position_x)
                                 for offset_z in range(2) for offset_y in range(3)]
                    positions = [position for position in positions if support[position]]
                    encoding = np.stack([maps[(slice(None),) + position]
                                         for position in positions], axis=1)
                    gram = encoding.conj().T @ np.linalg.solve(covariance, encoding)
                    reference = np.sqrt((np.diag(np.linalg.inv(gram)) * np.diag(gram)).real)
                    for position, value in zip(positions, reference):
                        expected[position] = value
        np.testing.assert_allclose(factor, expected, rtol=2e-6)

    def test_g_factor_is_invariant_to_common_voxel_scaling(self):
        rng = np.random.default_rng(7)
        maps = rng.normal(size=(4, 6, 3)) + 1j * rng.normal(size=(4, 6, 3))
        phase = np.exp(1j * rng.normal(size=(6, 3)))
        scaled = maps * phase * np.geomspace(1e-4, 1e4, 18).reshape(6, 3)
        reference = snr.calculate_g_factor(maps, np.eye(4), acceleration_y=2)
        actual = snr.calculate_g_factor(scaled, np.eye(4), acceleration_y=2)
        np.testing.assert_allclose(actual, reference, rtol=1e-6)

    def test_sensitivity_estimation_masks_background_and_normalizes(self):
        images = np.zeros((2, 8, 8), dtype=np.complex64)
        images[0, 2:6, 2:6] = 3
        images[1, 2:6, 2:6] = 4j
        maps, support = snr.estimate_sensitivity_maps(images, smoothing=1.)
        self.assertEqual(int(support.sum()), 16)
        np.testing.assert_allclose(np.sum(np.abs(maps[:, support]) ** 2, axis=0),
                                   1, atol=1e-6)
        np.testing.assert_allclose(maps[0, support], 0.6, atol=1e-6)
        np.testing.assert_allclose(maps[1, support], 0.8j, atol=1e-6)
        self.assertFalse(maps[:, ~support].any())
        factor = snr.calculate_g_factor(maps, np.eye(2), support=support)
        self.assertTrue(np.isnan(factor[~support]).all())
        np.testing.assert_allclose(factor[support], 1)

    def test_zero_signal_produces_empty_support_not_finite_g(self):
        maps, support = snr.estimate_sensitivity_maps(np.zeros((2, 4, 4), dtype=complex))
        self.assertFalse(support.any())
        factor = snr.calculate_g_factor(maps, np.eye(2), acceleration_y=2, support=support)
        self.assertTrue(np.isnan(factor).all())

    def test_rank_deficiency_and_invalid_accelerations(self):
        maps = np.ones((1, 4, 4), dtype=complex)
        self.assertTrue(np.isinf(snr.calculate_g_factor(
            maps, np.eye(1), acceleration_y=2)).all())
        for kwargs in ({'acceleration_y': 3}, {'acceleration_z': 2},
                       {'acceleration_y': 1.5}, {'acceleration_y': 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                snr.calculate_g_factor(maps, np.eye(1), **kwargs)

    def test_covariance_floor_matches_explicit_floored_covariance(self):
        rng = np.random.default_rng(8)
        maps = rng.normal(size=(3, 4, 3)) + 1j * rng.normal(size=(3, 4, 3))
        original = np.diag([0, 1., 2.])
        regularized = np.diag([0.02, 1., 2.])
        actual = snr.calculate_g_factor(maps, original, acceleration_y=2,
                                        covariance_floor=0.01)
        expected = snr.calculate_g_factor(maps, regularized, acceleration_y=2)
        np.testing.assert_allclose(actual, expected, rtol=1e-6)

    def test_alias_group_batch_boundaries(self):
        maps = np.zeros((2, 4, 2049), dtype=complex)
        maps[0, :2] = 1
        maps[1, 2:] = 1
        factor = snr.calculate_g_factor(maps, np.eye(2), acceleration_y=2)
        np.testing.assert_allclose(factor, 1, atol=1e-6)


if __name__ == '__main__':
    unittest.main()