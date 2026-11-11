import importlib.util
import logging
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gpi
from gpi.associate import Bindings, getGPIAssociatedExt, isGPIAssociatedFile
import numpy as np


def load_node(name):
    path = Path(__file__).resolve().parent.parent / 'gpi_core/fileIO/GPI' / (name + '_GPI.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ExternalNode


ReadNode = load_node('ReadNPY')
WriteNode = load_node('WriteNPY')
WriteMatNode = load_node('WriteMAT')
ReadMatNode = load_node('ReadMatlab')


class TestNumpyIO(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = gpi.QtWidgets.QApplication.instance() or gpi.QtWidgets.QApplication([])

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.values = {'File Browser': '', 'Squeeze': False, 'Array': '',
                       'Write Mode': False, 'Write Now': True}
        for port in ('in', 'in2', 'in3', 'in4', 'in5'):
            self.values['Array Name ({})'.format(port)] = port
        self.attrs = {'Array': {'items': []}}
        self.outputs = {}
        self.inputs = {'in': np.arange(12, dtype=np.float32).reshape(1, 3, 4),
                       'in3': np.array([1 + 2j], dtype=np.complex64)}
        self.reader = self.make_node(ReadNode)
        self.writer = self.make_node(WriteNode)
        self.writer.getData = self.inputs.get
        self.writer.widgetEvents = lambda: set()

    def make_node(self, node_class):
        node = node_class.__new__(node_class)
        node.getVal = self.values.__getitem__
        node.getAttr = lambda title, attr: self.attrs[title][attr]
        node.setAttr = self.set_attr
        node.setData = self.outputs.__setitem__
        node.setDetailLabel = Mock()
        node.log = Mock()
        node.URI = gpi.TranslateFileURI
        return node

    def set_attr(self, title, **attrs):
        self.attrs.setdefault(title, {}).update(attrs)
        if 'val' in attrs:
            self.values[title] = attrs['val']

    def filename(self, name):
        path = Path(self.tempdir.name) / name
        self.values['File Browser'] = str(path)
        self.reader.validate()
        return path

    def test_matlab_missing_path_uses_standard_worker_logger(self):
        reader = self.make_node(ReadMatNode)
        reader.log = logging.getLogger('test.readmatlab.worker')
        for filename in ('', str(Path(self.tempdir.name) / 'missing.mat')):
            with self.subTest(filename=filename):
                self.values['File Browser'] = filename
                with self.assertLogs(reader.log, level='WARNING') as messages:
                    self.assertEqual(reader.validate(), 0)
                    self.assertEqual(reader.compute(), 0)
                self.assertEqual(len(messages.records), 2)
                self.assertTrue(all('Path does not exist:' in record.getMessage()
                                    for record in messages.records))
                self.assertEqual(self.outputs, {})

    def test_reader_subtitle_shows_filename_only(self):
        for name in ('image.npy', 'arrays.npz'):
            with self.subTest(name=name):
                path = self.filename(name)
                self.reader.setDetailLabel.assert_called_with(name)
                self.assertEqual(self.reader.fname, str(path))
                self.assertEqual(self.values['File Browser'], str(path))
        self.values['File Browser'] = ''
        self.reader.validate()
        self.reader.setDetailLabel.assert_called_with('')

    def test_multi_array_round_trip_and_selection(self):
        path = self.filename('arrays.npz')
        self.assertEqual(self.writer.compute(), 0)
        with np.load(path) as archive:
            self.assertEqual(archive.files, ['in', 'in3'])
        self.assertEqual(self.reader.compute(), 0)
        np.testing.assert_array_equal(self.outputs['out'], self.inputs['in'])
        self.assertEqual(self.attrs['Array']['items'], ['in', 'in3'])
        self.assertTrue(self.attrs['Array']['visible'])
        self.values['Array'] = 'in3'
        self.reader.compute()
        np.testing.assert_array_equal(self.outputs['out'], self.inputs['in3'])
        self.assertEqual(self.values['Array'], 'in3')
        path.unlink()

    def test_npy_compatibility_and_default_extension(self):
        self.inputs.pop('in3')
        self.values['Array Name (in)'] = ''
        for name in ('array.npy', 'array', 'array.NPY'):
            with self.subTest(name=name):
                path = self.filename(name)
                self.assertEqual(self.writer.compute(), 0)
                if not path.suffix:
                    path = self.filename(name + '.npy')
                self.reader.compute()
                np.testing.assert_array_equal(self.outputs['out'], self.inputs['in'])
                self.assertFalse(self.attrs['Array']['visible'])
                path.unlink()

    def test_compressed_archive_squeeze_and_stale_selection(self):
        path = self.filename('compressed.npz')
        np.savez_compressed(path, volume=self.inputs['in'])
        self.values.update({'Array': 'missing', 'Squeeze': True})
        self.reader.compute()
        self.assertEqual(self.values['Array'], 'volume')
        np.testing.assert_array_equal(self.outputs['out'], self.inputs['in'].squeeze())
        path.unlink()

    def test_read_failures_clear_output(self):
        for name in ('empty.npz', 'invalid.npz', 'missing.npy', 'object.npz'):
            with self.subTest(name=name):
                path = self.filename(name)
                if name == 'empty.npz':
                    np.savez(path)
                elif name == 'invalid.npz':
                    path.write_bytes(b'invalid')
                elif name == 'object.npz':
                    np.savez(path, data=np.array([{}], dtype=object))
                self.outputs['out'] = 'stale'
                self.reader.compute()
                self.assertIsNone(self.outputs['out'])
                if path.exists():
                    path.unlink()

    def test_multiple_arrays_require_npz(self):
        path = self.filename('array.npy')
        self.assertEqual(self.writer.compute(), 1)
        self.assertFalse(path.exists())

    def test_single_array_archive_and_all_optional_inputs(self):
        self.inputs.pop('in3')
        for name in ('single.npz', 'all.NPZ'):
            with self.subTest(name=name):
                if name == 'all.NPZ':
                    for index in range(2, 6):
                        self.inputs['in{}'.format(index)] = np.array(index)
                path = self.filename(name)
                self.assertEqual(self.writer.compute(), 0)
                with np.load(path) as archive:
                    self.assertEqual(set(archive.files), set(self.inputs))
                    for key, expected in self.inputs.items():
                        np.testing.assert_array_equal(archive[key], expected)
                self.reader.compute()
                np.testing.assert_array_equal(self.outputs['out'], self.inputs['in'])

    def test_npz_file_association(self):
        path = self.filename('arrays.NPZ')
        path.touch()
        self.assertTrue(isGPIAssociatedFile(str(path)))
        self.assertEqual(getGPIAssociatedExt(str(path)), '.npz')
        self.assertEqual(Bindings.get('.npz').node, 'gpi_core.fileIO.ReadNPY')
        self.assertEqual(Bindings.get('.npz').wdg, 'File Browser')

    def test_custom_array_names_round_trip(self):
        path = self.filename('named.npz')
        self.values.update({'Array Name (in)': 'image',
                            'Array Name (in3)': 'coil sensitivities',
                            'Array Name (in2)': ''})
        self.assertEqual(self.writer.compute(), 0)
        with np.load(path) as archive:
            self.assertEqual(archive.files, ['image', 'coil sensitivities'])
            np.testing.assert_array_equal(archive['image'], self.inputs['in'])
            np.testing.assert_array_equal(archive['coil sensitivities'], self.inputs['in3'])
        self.values['Array'] = 'coil sensitivities'
        self.reader.compute()
        np.testing.assert_array_equal(self.outputs['out'], self.inputs['in3'])

    def test_invalid_array_names_preserve_existing_file(self):
        path = self.filename('existing.npz')
        original = b'existing file contents'
        path.write_bytes(original)
        for name in ('', '   ', 'in', 'file', 'allow_pickle'):
            with self.subTest(name=name):
                self.values['Array Name (in3)'] = name
                self.assertEqual(self.writer.compute(), 1)
                self.assertEqual(path.read_bytes(), original)
                self.writer.log.error.assert_called()

    def test_array_name_field_visibility(self):
        for filename, visible in (('arrays.npz', True), ('array.npy', False),
                                  ('arrays.NPZ', True)):
            with self.subTest(filename=filename):
                self.filename(filename)
                self.assertEqual(self.writer.validate(), 0)
                for port in ('in', 'in2', 'in3', 'in4', 'in5'):
                    self.assertEqual(self.attrs['Array Name ({})'.format(port)]['visible'], visible)

    def test_writer_triggers_and_empty_filename(self):
        path = self.filename('arrays.npz')
        self.values['Write Now'] = False
        self.writer.compute()
        self.assertFalse(path.exists())
        self.writer.widgetEvents = lambda: {'File Browser'}
        self.writer.compute()
        self.assertTrue(path.exists())
        self.values['File Browser'] = ''
        self.assertEqual(self.writer.compute(), 0)

    def make_mat_writer(self):
        writer = self.make_node(WriteMatNode)
        writer.getData = self.inputs.get
        writer.widgetEvents = lambda: set()
        self.values['Compression'] = True
        return writer

    def test_mat_multiple_arrays_complex_and_default_extension(self):
        from scipy.io import loadmat

        writer = self.make_mat_writer()
        self.values['Array Name (in)'] = 'volume'
        self.values['Array Name (in3)'] = 'complex_data'
        for compressed in (True, False):
            with self.subTest(compressed=compressed):
                self.values['Compression'] = compressed
                path = Path(self.tempdir.name) / ('arrays' if compressed else 'arrays.MAT')
                self.values['File Browser'] = str(path)
                self.assertEqual(writer.compute(), 0)
                saved = path.with_suffix('.mat') if not path.suffix else path
                loaded = loadmat(saved)
                np.testing.assert_array_equal(loaded['volume'], self.inputs['in'])
                np.testing.assert_array_equal(loaded['complex_data'], self.inputs['in3'][None])
                self.assertEqual(loaded['complex_data'].dtype, np.complex64)

    def test_mat_invalid_names_preserve_existing_file(self):
        writer = self.make_mat_writer()
        path = Path(self.tempdir.name) / 'existing.mat'
        path.write_bytes(b'existing file')
        self.values['File Browser'] = str(path)
        for name in ('', '_hidden', '3data', 'coil data', 'end', 'x' * 64, 'in'):
            with self.subTest(name=name):
                self.values['Array Name (in3)'] = name
                self.assertEqual(writer.compute(), 1)
                self.assertEqual(path.read_bytes(), b'existing file')

    def test_mat_write_triggers_and_interface(self):
        writer = self.make_mat_writer()
        writer.addWidget = Mock()
        writer.addInPort = Mock()
        writer.initUI()
        self.assertEqual(writer.addInPort.call_count, 5)
        for port_call in writer.addInPort.call_args_list[1:]:
            self.assertEqual(port_call.kwargs['obligation'], gpi.OPTIONAL)
        path = Path(self.tempdir.name) / 'arrays.mat'
        self.values.update({'File Browser': str(path), 'Write Now': False})
        self.assertEqual(writer.compute(), 0)
        self.assertFalse(path.exists())
        writer.widgetEvents = lambda: {'File Browser'}
        self.assertEqual(writer.compute(), 0)
        self.assertTrue(path.exists())
        self.values['File Browser'] = ''
        self.assertEqual(writer.compute(), 0)

    def test_mat_failed_write_preserves_existing_file(self):
        from scipy.io.matlab import MatWriteError

        writer = self.make_mat_writer()
        path = Path(self.tempdir.name) / 'existing.mat'
        path.write_bytes(b'existing file')
        self.values['File Browser'] = str(path)
        with patch('scipy.io.savemat', side_effect=MatWriteError('Cannot write variable')):
            self.assertEqual(writer.compute(), 1)
        self.assertEqual(path.read_bytes(), b'existing file')
        self.assertEqual(list(Path(self.tempdir.name).iterdir()), [path])

    def test_node_interfaces(self):
        for node in (self.reader, self.writer):
            node.addWidget = Mock()
            node.addInPort = Mock()
            node.addOutPort = Mock()
            node.initUI()
        self.assertEqual(self.writer.addInPort.call_count, 5)
        for call in self.writer.addInPort.call_args_list[1:]:
            self.assertEqual(call.kwargs['obligation'], gpi.OPTIONAL)
        for port in ('in', 'in2', 'in3', 'in4', 'in5'):
            self.writer.addWidget.assert_any_call(
                'StringBox', 'Array Name ({})'.format(port), val=port, visible=False)
        self.assertEqual(self.reader.addOutPort.call_count, 1)


if __name__ == '__main__':
    unittest.main()