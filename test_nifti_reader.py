import importlib.util
import os
from pathlib import Path
import pickle
import tempfile
import unittest
from unittest.mock import Mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gpi
from gpi.associate import Bindings, getGPIAssociatedExt, isGPIAssociatedFile
import nibabel as nib
import numpy as np


NODE_PATH = Path(__file__).parent / 'gpi_core/fileIO/GPI/ReadNIfTI_GPI.py'
SPEC = importlib.util.spec_from_file_location('read_nifti_node', NODE_PATH)
NODE_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NODE_MODULE)


class TestReadNIfTI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = gpi.QtWidgets.QApplication.instance() or gpi.QtWidgets.QApplication([])

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.values = {'File Browser': '', 'Read': True}
        self.outputs = {}
        self.attrs = {}
        self.node = NODE_MODULE.ExternalNode.__new__(NODE_MODULE.ExternalNode)
        self.node.getVal = self.values.__getitem__
        self.node.setData = self.outputs.__setitem__
        self.node.setAttr = lambda title, **attrs: self.attrs.setdefault(title, {}).update(attrs)
        self.node.setDetailLabel = Mock()
        self.node.log = Mock()
        self.node.URI = gpi.TranslateFileURI

    def save_image(self, data, suffix='.nii', image_class=nib.Nifti1Image):
        affine = np.diag([-2.0, 3.0, 4.0, 1.0])
        image = image_class(data, affine)
        image.header.set_xyzt_units('mm', 'sec')
        path = Path(self.tempdir.name) / ('image' + suffix)
        nib.save(image, path)
        self.values['File Browser'] = str(path)
        return image, path

    def test_native_dimensions_and_metadata(self):
        for image_class in (nib.Nifti1Image, nib.Nifti2Image):
            for suffix in ('.nii', '.nii.gz'):
                with self.subTest(image_class=image_class, suffix=suffix):
                    data = np.arange(120, dtype=np.int16).reshape(4, 5, 3, 2, 1)
                    image, path = self.save_image(data, suffix, image_class)
                    self.assertEqual(self.node.compute(), 0)
                    np.testing.assert_array_equal(self.outputs['out'], data)
                    metadata = self.outputs['NIfTI Metadata']
                    np.testing.assert_array_equal(metadata['affine'], image.affine)
                    self.assertEqual(metadata['orientation'], ['L', 'A', 'S'])
                    self.assertEqual(metadata['spacing'], [2.0, 3.0, 4.0, 1.0, 1.0])
                    self.assertEqual(metadata['spatial_unit'], 'mm')
                    self.assertEqual(metadata['time_unit'], 'sec')
                    self.assertEqual(metadata['shape'], list(data.shape))
                    self.assertEqual(metadata['storage_dtype'], 'int16')
                    self.assertEqual(self.outputs['NiftiDict']['sizeof_hdr'],
                                     int(image.header['sizeof_hdr']))
                    pickle.loads(pickle.dumps(self.outputs))
                    path.unlink()

    def test_intensity_scaling(self):
        data = np.arange(24, dtype=np.int16).reshape(2, 3, 4)
        image, path = self.save_image(data)
        image.header.set_slope_inter(2.5, -7.0)
        nib.save(image, path)
        self.assertEqual(self.node.compute(), 0)
        np.testing.assert_array_equal(self.outputs['out'], data * 2.5 - 7.0)
        self.assertEqual(self.outputs['NIfTI Metadata']['slope'], 2.5)
        self.assertEqual(self.outputs['NIfTI Metadata']['intercept'], -7.0)

    def test_complex_values(self):
        data = (np.arange(24).reshape(2, 3, 4) + 2j).astype(np.complex64)
        self.save_image(data, '.nii.gz')
        self.assertEqual(self.node.compute(), 0)
        np.testing.assert_array_equal(self.outputs['out'], data)

    def test_disabled_read_clears_outputs(self):
        self.outputs.update({'out': 'old data', 'NiftiDict': {}, 'NIfTI Metadata': {}})
        self.values['Read'] = False
        self.assertEqual(self.node.compute(), 0)
        self.assertTrue(all(value is None for value in self.outputs.values()))

    def test_invalid_files_clear_stale_outputs(self):
        for filename in ('', 'missing.nii', 'invalid.nii', 'wrong.txt'):
            with self.subTest(filename=filename):
                path = Path(self.tempdir.name) / filename
                if filename in ('invalid.nii', 'wrong.txt'):
                    path.write_bytes(b'not a NIfTI image')
                self.values['File Browser'] = str(path) if filename else ''
                self.outputs.update({'out': 'old', 'NiftiDict': {}, 'NIfTI Metadata': {}})
                self.assertEqual(self.node.compute(), 1)
                self.assertTrue(all(value is None for value in self.outputs.values()))
                self.assertIn('Failed to read file:', self.attrs['I/O Info:']['val'])

    def test_node_interface(self):
        self.node.addWidget = Mock()
        self.node.addOutPort = Mock()
        self.node.initUI()
        self.assertEqual(self.node.addWidget.call_count, 3)
        self.assertEqual(self.node.addOutPort.call_count, 3)
        self.assertEqual(self.node.execType(), gpi.GPI_PROCESS)
        self.assertEqual(self.node.validate(), 0)


class TestNIfTIAssociations(unittest.TestCase):
    def test_nifti_default_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            for filename in ('image.nii', 'image.nii.gz', 'IMAGE.NII', 'IMAGE.NII.GZ'):
                with self.subTest(filename=filename):
                    path = Path(directory) / filename
                    path.touch()
                    self.assertTrue(isGPIAssociatedFile(str(path)))
                    ext = getGPIAssociatedExt(str(path))
                    self.assertIn(ext, ('.nii', '.nii.gz'))
                    self.assertEqual(Bindings.get(ext).node, 'gpi_core.fileIO.ReadNIfTI')
                    self.assertEqual(Bindings.get(ext).wdg, 'File Browser')

    def test_existing_associations_and_unknown_files(self):
        with tempfile.TemporaryDirectory() as directory:
            for filename, expected in (('image.dcm', '.dcm'), ('DICOMDIR', '.dicomdir'),
                                       ('array.NPY', '.npy'), ('unknown.gz', '.gz')):
                with self.subTest(filename=filename):
                    path = Path(directory) / filename
                    path.touch()
                    self.assertEqual(getGPIAssociatedExt(str(path)), expected)
                    self.assertEqual(isGPIAssociatedFile(str(path)), filename != 'unknown.gz')
            self.assertFalse(isGPIAssociatedFile(str(Path(directory) / 'missing.nii')))


if __name__ == '__main__':
    unittest.main()