import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, call

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gpi
import numpy as np
from scipy import fft


path = (Path(__file__).resolve().parent.parent / 'gpi_core' / 'fileIO' / 'GPI'
        / 'ComputeTSNR_GPI.py')
spec = importlib.util.spec_from_file_location('ComputeTSNR', path)
tsnr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tsnr)


class TestComputeTSNR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = gpi.QtWidgets.QApplication.instance() or gpi.QtWidgets.QApplication([])

    def setUp(self):
        self.rng = np.random.default_rng(42)
        mixing = np.array([[1, 0], [0.4 + 0.3j, 1.2]])
        samples = self.rng.normal(size=(2, 500)) + 1j * self.rng.normal(size=(2, 500))
        self.noise = (mixing @ samples).astype(np.complex64)

    def test_reconstruction_combination_and_statistics_against_direct_reference(self):
        for spatial in ((4, 8), (3, 4, 8)):
            for crop in (False, True):
                with self.subTest(spatial=spatial, crop=crop):
                    images = (self.rng.normal(size=(2, 50) + spatial)
                              + 1j * self.rng.normal(size=(2, 50) + spatial) + 5)
                    axes = tuple(range(2, images.ndim))
                    raw = fft.fftshift(fft.ifftn(fft.ifftshift(images, axes=axes),
                                                axes=axes, norm='ortho'), axes=axes)
                    result = tsnr.calculate_tsnr(raw, self.noise, crop)
                    centered = self.noise.astype(np.complex128)
                    centered -= centered.mean(axis=1, keepdims=True)
                    covariance = centered @ centered.conj().T / (2 * 499)
                    if crop:
                        images = images[..., 2:6]
                    reference = np.sqrt(np.einsum('ct...,cd,dt...->t...', images.conj(),
                                                 np.linalg.inv(covariance), images).real)
                    reference = np.rot90(reference, axes=(-2, -1))
                    if len(spatial) == 3:
                        reference = np.flip(reference, axis=1)
                    np.testing.assert_allclose(result['noise_covariance'], covariance)
                    np.testing.assert_allclose(result['combined_images'], reference, rtol=2e-6)
                    np.testing.assert_allclose(result['temporal_mean'], reference.mean(axis=0), rtol=2e-6)
                    np.testing.assert_allclose(result['temporal_std'], reference.std(axis=0, ddof=1), rtol=2e-6)
                    np.testing.assert_allclose(result['tSNR'], reference.mean(axis=0)
                                               / reference.std(axis=0, ddof=1), rtol=2e-6)

    def test_noise_scale_cancels_from_tsnr(self):
        raw = (self.rng.normal(size=(2, 5, 4, 8))
               + 1j * self.rng.normal(size=(2, 5, 4, 8))).astype(np.complex64)
        original = tsnr.calculate_tsnr(raw, self.noise)
        scaled = tsnr.calculate_tsnr(raw, self.noise, noise_scale=3)
        np.testing.assert_allclose(scaled['combined_images'], original['combined_images'] / 3,
                                   rtol=2e-6)
        np.testing.assert_allclose(scaled['tSNR'], original['tSNR'], rtol=2e-6)

    def test_zero_variance_is_nan(self):
        frame = np.ones((2, 1, 4, 8), dtype=np.complex64)
        for raw in (np.repeat(frame, 50, axis=1), np.zeros((2, 50, 4, 8), np.complex64)):
            result = tsnr.calculate_tsnr(raw, self.noise)
            np.testing.assert_array_equal(result['temporal_std'], 0)
            self.assertTrue(np.isnan(result['tSNR']).all())

    def test_32_coils_and_50_repetitions(self):
        noise = (self.rng.normal(size=(32, 500))
                 + 1j * self.rng.normal(size=(32, 500))).astype(np.complex64)
        raw = (self.rng.normal(size=(32, 50, 6, 12))
               + 1j * self.rng.normal(size=(32, 50, 6, 12))).astype(np.complex64)
        result = tsnr.calculate_tsnr(raw, noise)
        self.assertEqual(result['combined_images'].shape, (50, 6, 6))
        self.assertEqual(result['tSNR'].shape, (6, 6))
        self.assertEqual(result['noise_covariance'].shape, (32, 32))
        self.assertTrue(np.isfinite(result['tSNR']).all())
        np.testing.assert_allclose(result['tSNR'],
                                   result['combined_images'].mean(axis=0, dtype=np.float64)
                                   / result['combined_images'].std(axis=0, ddof=1, dtype=np.float64),
                                   rtol=2e-6)

    def test_real_widget_settings(self):
        node = tsnr.ExternalNode.__new__(tsnr.ExternalNode)
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
        node.initUI()
        for title, value in (('Compute', True), ('Remove Oversampling', False),
                             ('Noise Std Scale', 2.), ('Covariance Floor', 1e-5)):
            set_attr(title, val=value)
            self.assertEqual(node.getVal(title), value)
        self.assertEqual(node.validate(), 0)

    def test_invalid_inputs(self):
        raw = np.ones((2, 3, 4, 8), dtype=np.complex64)
        nonfinite = raw.copy()
        nonfinite[0, 0, 0, 0] = np.nan
        for data, noise, kwargs in (
                (raw.real, self.noise, {}), (raw[:, :1], self.noise, {}),
                (raw, self.noise[:1], {}), (raw, self.noise.real, {}),
                (raw, self.noise[:, :2], {}), (raw[..., :7], self.noise, {}),
                (nonfinite, self.noise, {}), (raw, self.noise, {'covariance_floor': 0}),
                (raw, self.noise, {'noise_scale': 0})):
            with self.subTest(shape=data.shape, kwargs=kwargs):
                with self.assertRaises(ValueError):
                    tsnr.calculate_tsnr(data, noise, **kwargs)

    def test_node_ports_compute_and_error_clearing(self):
        node = tsnr.ExternalNode.__new__(tsnr.ExternalNode)
        node.addWidget = Mock()
        node.addInPort = Mock()
        node.addOutPort = Mock()
        node.initUI()
        self.assertEqual(node.addInPort.call_args_list, [
            call('in', 'NPYarray', obligation=gpi.REQUIRED),
            call('noise', 'NPYarray', obligation=gpi.REQUIRED)])
        settings = {'Compute': True, 'Remove Oversampling': True,
                    'Noise Std Scale': 1., 'Covariance Floor': 1e-6}
        inputs = {'in': np.ones((2, 50, 4, 8), dtype=np.complex64), 'noise': self.noise}
        outputs = {}
        node.getVal = settings.__getitem__
        node.getData = inputs.__getitem__
        node.setData = outputs.__setitem__
        node.setAttr = Mock()
        node.log = Mock()
        self.assertEqual(node.compute(), 0)
        self.assertEqual(outputs['combined_images'].shape, (50, 4, 4))
        self.assertEqual(outputs['tSNR Metadata']['repetitions'], 50)
        inputs['noise'] = self.noise[:1]
        self.assertEqual(node.compute(), 1)
        self.assertTrue(all(value is None for value in outputs.values()))
        settings['Compute'] = False
        node.getData = Mock(side_effect=AssertionError('Disabled compute must not read inputs'))
        self.assertEqual(node.compute(), 0)


if __name__ == '__main__':
    unittest.main()