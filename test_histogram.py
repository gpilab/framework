import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np

try:
    import torch
except ImportError:
    torch = None


path = Path(__file__).parent / 'gpi_core' / 'math' / 'GPI' / '1DHistogram_GPI.py'
spec = importlib.util.spec_from_file_location('histogram', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HistogramNode = module.ExternalNode


class TestHistogram(unittest.TestCase):
    def make_node(self, data, component=2, auto_range=True, device=None):
        node = HistogramNode.__new__(HistogramNode)
        values = {'R I M': component, '# Bins': 4, 'Bin Range': int(auto_range),
                  'Lower Bound': -4., 'Upper Bound': 4., 'Device': 0}

        def set_attr(name, **attrs):
            if 'val' in attrs:
                values[name] = attrs['val']

        node.getData = Mock(return_value=data)
        node.getVal = values.__getitem__
        node.setAttr = Mock(side_effect=set_attr)
        node.setData = Mock()
        node.log = Mock()
        node._resolve_device = Mock(return_value=device)
        return node

    def validate(self, node):
        with patch.object(module, '_device_buttons', return_value=['cpu']):
            return node.validate()

    def assert_histogram(self, node, samples):
        self.assertEqual(self.validate(node), 0)
        self.assertEqual(node.compute(), 0)
        output = dict(call.args for call in node.setData.call_args_list)
        expected, edges = np.histogram(
            samples, bins=4, range=(node.getVal('Lower Bound'),
                                   node.getVal('Upper Bound')))
        for name, reference in (('HistVal', expected), ('HistBin', edges)):
            actual = output[name]
            if module._is_torch(actual):
                self.assertEqual(actual.device.type, 'cpu')
                actual = actual.numpy()
            np.testing.assert_allclose(actual, reference)
        self.assertEqual(module._is_torch(output['HistVal']),
                         module._is_torch(node.getData('Data In')))
        node.setAttr.assert_any_call(
            'Histogram Plot', val=unittest.mock.ANY)

    def test_numpy_ignores_nan_and_infinity_in_both_range_modes(self):
        for auto_range in (False, True):
            with self.subTest(auto_range=auto_range):
                data = np.array([0., -2., 1., 2., np.nan, np.inf, -np.inf])
                node = self.make_node(data, auto_range=auto_range)
                self.assert_histogram(node, [-2., 1., 2.])
                self.assertTrue(node.log.warn.called)
                self.assertIn('3 non-finite', node.log.warn.call_args.args[0])
                np.testing.assert_array_equal(
                    data, [0., -2., 1., 2., np.nan, np.inf, -np.inf])

    def test_rejects_all_nonfinite_in_validate_and_compute(self):
        for backend in ('numpy', 'torch'):
            if backend == 'torch' and torch is None:
                continue
            for auto_range in (False, True):
                with self.subTest(backend=backend, auto_range=auto_range):
                    data = np.array([np.nan, np.inf, -np.inf])
                    if backend == 'torch':
                        data = torch.tensor(data)
                    node = self.make_node(
                        data, auto_range=auto_range,
                        device='cpu' if backend == 'torch' else None)
                    self.assertEqual(self.validate(node), 1)
                    self.assertEqual(node.compute(), 1)
                    node.setData.assert_not_called()
                    self.assertIn('no finite samples',
                                  node.log.warn.call_args.args[0])

    def test_zero_empty_constant_and_small_values_preserve_behavior(self):
        for samples in ([], [0., 0.], [2., 2.], [1e-8, 2e-8], [-2., 1., 2.]):
            with self.subTest(samples=samples):
                data = np.asarray(samples)
                node = self.make_node(data)
                self.assert_histogram(node, data[data != 0])
                node.log.warn.assert_not_called()

    def test_finite_zeros_with_nonfinite_samples_are_valid(self):
        node = self.make_node(np.array([0., np.nan, np.inf]))
        self.assert_histogram(node, [])
        self.assertEqual(node.getVal('Lower Bound'), 0.)
        self.assertEqual(node.getVal('Upper Bound'), 1.)
        self.assertTrue(node.log.warn.called)

    def test_filters_selected_complex_component(self):
        data = np.array([complex(1., np.nan), complex(np.inf, 2.),
                         complex(3., 4.), 0j])
        for component, samples in ((0, [1., 3.]), (1, [2., 4.]), (2, [5.])):
            with self.subTest(component=component):
                node = self.make_node(data, component=component)
                self.assert_histogram(node, samples)
                self.assertTrue(node.log.warn.called)

    def test_nonfinite_manual_bounds_are_rejected(self):
        for bound in ('Lower Bound', 'Upper Bound'):
            for value in (np.nan, np.inf, -np.inf):
                with self.subTest(bound=bound, value=value):
                    node = self.make_node(np.array([1., 2.]), auto_range=False)
                    node.setAttr(bound, val=value)
                    self.assertEqual(self.validate(node), 1)
                    self.assertEqual(node.compute(), 1)
                    node.setData.assert_not_called()
                    self.assertIn('must be finite',
                                  node.log.warn.call_args.args[0])

    @unittest.skipIf(torch is None, 'PyTorch is not installed')
    def test_torch_backend_and_numpy_to_torch_conversion(self):
        for tensor_input in (False, True):
            for component in (0, 1, 2):
                with self.subTest(tensor_input=tensor_input, component=component):
                    data = np.array([complex(1., np.nan), complex(np.inf, 2.),
                                     complex(3., 4.), 0j])
                    if tensor_input:
                        data = torch.tensor(data)
                    node = self.make_node(data, component=component, device='cpu')
                    samples = ([1., 3.], [2., 4.], [5.])[component]
                    self.assert_histogram(node, samples)
                    self.assertTrue(node.log.warn.called)


if __name__ == '__main__':
    unittest.main()
