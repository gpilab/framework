import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

import numpy as np


path = Path(__file__).resolve().parent.parent / 'gpi_core/math/GPI/ValueBounds_GPI.py'
spec = importlib.util.spec_from_file_location('value_bounds', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestValueBounds(unittest.TestCase):
    def compute(self, data, operation, minmax, minimum=2., maximum=6.):
        node = module.ExternalNode.__new__(module.ExternalNode)
        node.getData = Mock(return_value=data)
        node.getVal = {'operation': operation, 'MinMax': minmax,
                       'Min': minimum, 'Max': maximum}.__getitem__
        node.setData = Mock()
        node.setAttr = Mock()
        self.assertEqual(node.compute(), 0)
        node.setData.assert_called_once()
        self.assertEqual(node.setData.call_args.args[0], 'out')
        return node.setData.call_args.args[1]

    def test_nan_positions_zero_and_valid_values_match_clean_input(self):
        for complex_data in (False, True):
            clean = np.array([1., 3., 8.], dtype=np.float32)
            if complex_data:
                clean = clean.astype(np.complex64) * np.exp(0.7j)
            data = np.insert(clean, 1, np.nan).reshape(2, 2)
            original = data.copy()
            for operation in (1, 2, 3):
                for minmax in (0, 1, 2):
                    with self.subTest(complex=complex_data, operation=operation, minmax=minmax):
                        expected = self.compute(clean, operation, minmax)
                        result = self.compute(data, operation, minmax)
                        self.assertEqual(result.shape, data.shape)
                        self.assertEqual(result.flat[1], 0)
                        self.assertFalse(np.isnan(result).any())
                        np.testing.assert_allclose(result.reshape(-1)[[0, 2, 3]], expected,
                                                   rtol=2e-6, atol=1e-6)
                        np.testing.assert_array_equal(data, original)

    def test_all_nan_inputs_become_zero(self):
        for dtype in (np.float32, np.complex64):
            data = np.full((2, 3), np.nan, dtype=dtype)
            for operation in (1, 2, 3):
                for minmax in (0, 1, 2):
                    with self.subTest(dtype=dtype, operation=operation, minmax=minmax):
                        result = self.compute(data, operation, minmax)
                        np.testing.assert_array_equal(result, np.zeros_like(data))
                        self.assertEqual(result.dtype, data.dtype)

    def test_complex_nan_in_either_component_becomes_zero(self):
        data = np.array([complex(np.nan, 2), complex(2, np.nan), 3 + 4j])
        for operation in (1, 2, 3):
            with self.subTest(operation=operation):
                result = self.compute(data, operation, 2)
                np.testing.assert_array_equal(result[:2], 0)
                self.assertTrue(np.isfinite(result).all())

    def test_pass_preserves_nans_and_values(self):
        for data in (np.array([np.nan, 2., 4.]), np.array([complex(np.nan, 0), 2 + 3j])):
            with self.subTest(dtype=data.dtype):
                result = self.compute(data, 0, 2)
                np.testing.assert_allclose(result, data, rtol=1e-14, equal_nan=True)

    def test_integer_input_keeps_clamp_and_threshold_results(self):
        data = np.array([-3, 0, 4, 9], dtype=np.int16)
        np.testing.assert_array_equal(self.compute(data, 1, 2), [2, 2, 4, 6])
        np.testing.assert_array_equal(self.compute(data, 2, 2), [0, 0, 4, 0])


if __name__ == '__main__':
    unittest.main()