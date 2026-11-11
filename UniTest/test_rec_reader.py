import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import xml.etree.ElementTree as ET

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gpi
from gpi.associate import Bindings, getGPIAssociatedExt, isGPIAssociatedFile
import numpy as np


NODE_PATH = Path(__file__).resolve().parent.parent / 'gpi_core' / 'fileIO' / 'GPI' / 'ReadREC_GPI.py'
SPEC = importlib.util.spec_from_file_location('read_rec_node', NODE_PATH)
NODE_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NODE_MODULE)


class TestReadREC(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'image.xml'

    def save_pair(self, dtype='<u2'):
        data = np.arange(18, dtype=np.dtype(dtype)).reshape(3, 2, 3)
        root = ET.Element('PRIDE_V5')
        images = ET.SubElement(root, 'Image_Array')
        for index, slice_number in ((2, 2), (0, 3), (1, 1)):
            image = ET.SubElement(images, 'Image_Info')
            key = ET.SubElement(image, 'Key')
            for name, value in (('Index', index), ('Slice', slice_number)):
                ET.SubElement(key, 'Attribute', Name=name).text = str(value)
            attrs = {
                'Resolution X': 3, 'Resolution Y': 2,
                'Pixel Size': data.dtype.itemsize * 8,
                'Pixel Representation': int(data.dtype.kind == 'i'),
                'Rescale Slope': index + 1, 'Rescale Intercept': -7,
            }
            for name, value in attrs.items():
                ET.SubElement(image, 'Attribute', Name=name).text = str(value)
        ET.ElementTree(root).write(self.path)
        data.tofile(self.path.with_suffix('.rec'))
        return data, root

    def test_storage_types_order_offsets_and_per_image_scaling(self):
        for dtype in ('<u2', '<i2', 'u1', 'i1'):
            with self.subTest(dtype=dtype):
                data, _ = self.save_pair(dtype)
                if np.dtype(dtype).kind == 'i':
                    data -= 9
                    data.tofile(self.path.with_suffix('.rec'))
                expected = np.stack([data[1] * 2.0 - 7,
                                     data[2] * 3.0 - 7, data[0] - 7.0])
                for suffix in ('.xml', '.rec'):
                    out = NODE_MODULE.read_rec(str(self.path.with_suffix(suffix)))
                    self.assertEqual(out.shape, (3, 2, 3))
                    self.assertEqual(out.dtype, np.float32)
                    np.testing.assert_array_equal(out, expected)

    def test_xml_without_pixel_representation_defaults_to_unsigned(self):
        data, root = self.save_pair('<u2')
        data += np.uint16(40000)
        data.tofile(self.path.with_suffix('.rec'))
        for image in root.findall('.//Image_Info'):
            image.remove(image.find("Attribute[@Name='Pixel Representation']"))
        ET.ElementTree(root).write(self.path)
        expected = np.stack([data[1].astype(np.float32) * 2 - 7,
                             data[2].astype(np.float32) * 3 - 7,
                             data[0].astype(np.float32) - 7])
        for suffix in ('.xml', '.rec'):
            with self.subTest(suffix=suffix):
                np.testing.assert_array_equal(
                    NODE_MODULE.read_rec(self.path.with_suffix(suffix)), expected)

    def test_missing_companion(self):
        self.save_pair()
        self.path.with_suffix('.rec').unlink()
        with self.assertRaisesRegex(ValueError, 'Both XML and REC'):
            NODE_MODULE.read_rec(self.path)

    def test_wrong_rec_size(self):
        self.save_pair()
        for content in (b'', b'\0' * 34, b'\0' * 38):
            with self.subTest(size=len(content)):
                self.path.with_suffix('.rec').write_bytes(content)
                with self.assertRaisesRegex(ValueError, 'REC size'):
                    NODE_MODULE.read_rec(self.path)

    def test_invalid_image_attributes(self):
        for name, value in (
                ('Resolution X', '0'), ('Resolution X', '4'),
                ('Pixel Size', '32'), ('Pixel Representation', '2'),
                ('Rescale Slope', 'nan'), ('Rescale Intercept', 'bad')):
            with self.subTest(name=name, value=value):
                _, root = self.save_pair()
                root.find(".//Image_Info/Attribute[@Name='{}']".format(name)).text = value
                ET.ElementTree(root).write(self.path)
                with self.assertRaises(ValueError):
                    NODE_MODULE.read_rec(self.path)

    def test_duplicate_or_invalid_indices(self):
        for index in ('0', '-1', '7'):
            with self.subTest(index=index):
                _, root = self.save_pair()
                root.find(".//Key/Attribute[@Name='Index']").text = index
                ET.ElementTree(root).write(self.path)
                with self.assertRaises(ValueError):
                    NODE_MODULE.read_rec(self.path)

    def test_missing_required_attribute(self):
        _, root = self.save_pair()
        image = root.find('.//Image_Info')
        image.remove(image.find("Attribute[@Name='Resolution X']"))
        ET.ElementTree(root).write(self.path)
        with self.assertRaisesRegex(ValueError, 'Missing or invalid'):
            NODE_MODULE.read_rec(self.path)

    def test_invalid_xml_and_format(self):
        self.save_pair()
        for xml in ('not xml', '<Other/>', '<PRIDE_V5/>'):
            self.path.write_text(xml)
            with self.assertRaises((ValueError, ET.ParseError)):
                NODE_MODULE.read_rec(self.path)
        with self.assertRaisesRegex(ValueError, 'Select a PRIDE'):
            NODE_MODULE.read_rec(self.path.with_suffix('.txt'))


class TestRECAssociations(unittest.TestCase):
    def test_rec_default_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            for filename in ('image.rec', 'IMAGE.REC', 'image.ReC'):
                with self.subTest(filename=filename):
                    path = Path(directory) / filename
                    path.touch()
                    self.assertTrue(isGPIAssociatedFile(str(path)))
                    ext = getGPIAssociatedExt(str(path))
                    self.assertEqual(ext, '.rec')
                    self.assertEqual(Bindings.get(ext).node, 'gpi_core.fileIO.ReadREC')
                    self.assertEqual(Bindings.get(ext).wdg, 'File Browser')
            self.assertFalse(isGPIAssociatedFile(str(Path(directory) / 'missing.rec')))


class TestReadRECNode(unittest.TestCase):
    def setUp(self):
        self.values = {'File Browser': '', 'Read': True}
        self.outputs = {'out': 'stale'}
        self.attrs = {}
        self.node = NODE_MODULE.ExternalNode.__new__(NODE_MODULE.ExternalNode)
        self.node.getVal = self.values.__getitem__
        self.node.setData = self.outputs.__setitem__
        self.node.setAttr = lambda title, **attrs: self.attrs.setdefault(title, {}).update(attrs)
        self.node.setDetailLabel = Mock()
        self.node.log = Mock()
        self.node.URI = gpi.TranslateFileURI

    def test_failure_clears_output_and_reports_error(self):
        self.assertEqual(self.node.compute(), 1)
        self.assertIsNone(self.outputs['out'])
        self.node.log.error.assert_called_once()
        self.assertIn('Failed to read file:', self.attrs['I/O Info:']['val'])

    def test_disabled_read_clears_output(self):
        self.values['Read'] = False
        self.assertEqual(self.node.compute(), 0)
        self.assertIsNone(self.outputs['out'])

    def test_interface(self):
        self.node.addWidget = Mock()
        self.node.addOutPort = Mock()
        self.node.initUI()
        self.assertEqual(self.node.addWidget.call_count, 3)
        self.node.addOutPort.assert_called_once_with(title='out', type='NPYarray')
        self.assertEqual(self.node.execType(), gpi.GPI_PROCESS)
        self.assertEqual(self.node.validate(), 0)

    def test_success(self):
        pair = TestReadREC()
        pair.setUp()
        self.addCleanup(pair.doCleanups)
        pair.save_pair()
        self.values['File Browser'] = str(pair.path)
        self.assertEqual(self.node.compute(), 0)
        np.testing.assert_array_equal(self.outputs['out'], NODE_MODULE.read_rec(pair.path))
        self.assertIn('[3, 2, 3]', self.attrs['I/O Info:']['val'])


if __name__ == '__main__':
    unittest.main()
