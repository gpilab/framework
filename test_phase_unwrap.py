import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from skimage.restoration import unwrap_phase


path = Path(__file__).parent / 'gpi_core' / 'math' / 'GPI' / 'phaseUnwrap_GPI.py'
spec = importlib.util.spec_from_file_location('phaseUnwrap', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PhaseUnwrapNode = module.ExternalNode


class TestPhaseUnwrap(unittest.TestCase):
    def make_node(self, data, dimensions=1):
        node = PhaseUnwrapNode.__new__(PhaseUnwrapNode)
        values = {'Dimensions': dimensions, 'Dimension': 0, 'Units': 1}
        node.getData = Mock(return_value=data)
        node.getVal = values.__getitem__
        node.setData = Mock()
        node.setAttr = Mock()
        node.log = Mock()
        return node

    def wrapped_phase(self, shape, dtype=np.float64):
        phase = sum((axis + 1) * 0.6 * grid
                    for axis, grid in enumerate(np.indices(shape)))
        return np.angle(np.exp(1j * phase)).astype(dtype)

    def test_dimension_selector_defaults_to_existing_volume_behavior(self):
        node = self.make_node(np.zeros((3, 4, 5)))
        node.addWidget = Mock()
        node.addInPort = Mock()
        node.addOutPort = Mock()
        node.initUI()
        node.addWidget.assert_any_call(
            'ExclusivePushButtons', 'Dimensions', buttons=['2D', '3D'], val=1)

    def test_unwraps_independent_trailing_planes_and_volumes(self):
        for mode, rank in ((0, 2), (1, 3)):
            for shape in ((4, 5), (3, 4, 5), (2, 3, 4, 5),
                          (2, 3, 4, 5, 6)):
                for dtype in (np.float32, np.float64):
                    with self.subTest(mode=mode, shape=shape, dtype=dtype):
                        data = self.wrapped_phase(shape, dtype)
                        original = data.copy()
                        node = self.make_node(data, mode)
                        self.assertEqual(node.validate(), 0)
                        with patch('skimage.restoration.unwrap_phase',
                                   wraps=unwrap_phase) as unwrap:
                            self.assertEqual(node.compute(), 0)
                        node.setData.assert_called_once()
                        port, result = node.setData.call_args.args
                        self.assertEqual(port, 'out')
                        self.assertEqual(result.shape, shape)
                        self.assertEqual(result.dtype, np.float64)
                        batch_shape = shape[:-rank]
                        self.assertEqual(unwrap.call_count,
                                         int(np.prod(batch_shape)))
                        for index in np.ndindex(batch_shape):
                            np.testing.assert_allclose(
                                result[index], unwrap_phase(data[index]))
                        np.testing.assert_array_equal(data, original)

    def test_noncontiguous_input_and_singleton_batch_axes(self):
        data = self.wrapped_phase((1, 3, 8, 10))[:, :, ::2, ::-2]
        self.assertFalse(data.flags.c_contiguous)
        node = self.make_node(data, dimensions=0)
        self.assertEqual(node.compute(), 0)
        result = node.setData.call_args.args[1]
        self.assertEqual(result.shape, data.shape)
        for index in np.ndindex(data.shape[:-2]):
            np.testing.assert_allclose(result[index], unwrap_phase(data[index]))

    def test_one_dimensional_input_keeps_existing_behavior(self):
        data = self.wrapped_phase((12,))
        for mode in (0, 1):
            with self.subTest(mode=mode):
                node = self.make_node(data, mode)
                self.assertEqual(node.validate(), 0)
                self.assertEqual(node.compute(), 0)
                np.testing.assert_allclose(
                    node.setData.call_args.args[1], unwrap_phase(data))

    def test_read_only_input_from_process_worker(self):
        for mode, rank in ((0, 2), (1, 3)):
            for shape in ((4, 5), (3, 4, 5), (2, 3, 4, 5)):
                for dtype in (np.float32, np.float64):
                    for strided in (False, True):
                        with self.subTest(mode=mode, shape=shape, dtype=dtype,
                                          strided=strided):
                            data = self.wrapped_phase(shape, dtype)
                            if strided:
                                data = data[..., ::-1]
                            original = data.copy()
                            data.setflags(write=False)
                            node = self.make_node(data, mode)
                            self.assertEqual(node.compute(), 0)
                            result = node.setData.call_args.args[1]
                            self.assertEqual(result.shape, shape)
                            for index in np.ndindex(shape[:-rank]):
                                np.testing.assert_allclose(
                                    result[index],
                                    unwrap_phase(original[index].copy()))
                            self.assertFalse(data.flags.writeable)
                            np.testing.assert_array_equal(data, original)

    def test_rejects_scalar_and_empty_input_with_warning(self):
        for data in (np.array(1.0), np.empty((0, 4, 5)),
                     np.empty((2, 0, 5))):
            with self.subTest(shape=data.shape):
                node = self.make_node(data)
                self.assertEqual(node.validate(), 1)
                node.log.warn.assert_called_once()


if __name__ == '__main__':
    unittest.main()
