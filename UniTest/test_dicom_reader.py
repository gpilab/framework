import pickle
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, EnhancedMRImageStorage, generate_uid

from gpi_core.fileIO import dicomlib


class TestReadDICOM(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def save_dataset(self, name, values):
        meta = FileMetaDataset()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        meta.MediaStorageSOPClassUID = EnhancedMRImageStorage
        meta.MediaStorageSOPInstanceUID = generate_uid()
        path = Path(self.tempdir.name) / name
        dataset = FileDataset(str(path), {}, file_meta=meta, preamble=b'\0' * 128)
        dataset.SOPClassUID = meta.MediaStorageSOPClassUID
        dataset.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
        dataset.Rows = 2
        dataset.Columns = 3
        dataset.SamplesPerPixel = 1
        dataset.PhotometricInterpretation = 'MONOCHROME2'
        dataset.BitsAllocated = 16
        dataset.BitsStored = 16
        dataset.HighBit = 15
        dataset.PixelRepresentation = 0
        if len(values) > 1:
            dataset.NumberOfFrames = len(values)
        pixels = np.array(values, dtype='<u2')[:, None, None] * np.ones((1, 2, 3), dtype='<u2')
        dataset.PixelData = pixels.tobytes()
        return path, dataset

    def enhanced_dataset(self, coordinates, geometry=True):
        values = [10 * dynamic + location for dynamic, location in coordinates]
        path, dataset = self.save_dataset('enhanced.dcm', values)
        shared = Dataset()
        orientation = Dataset()
        orientation.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        shared.PlaneOrientationSequence = [orientation]
        measures = Dataset()
        measures.PixelSpacing = [2, 3]
        measures.SliceThickness = 5
        shared.PixelMeasuresSequence = [measures]
        dataset.SharedFunctionalGroupsSequence = [shared]
        dataset.PerFrameFunctionalGroupsSequence = []
        for dynamic, location in coordinates:
            group = Dataset()
            content = Dataset()
            content.TemporalPositionIndex = dynamic
            content.InStackPositionNumber = location
            content.StackID = '1'
            group.FrameContentSequence = [content]
            if geometry:
                position = Dataset()
                position.ImagePositionPatient = [0, 0, 5 * (location - 1)]
                group.PlanePositionSequence = [position]
            dataset.PerFrameFunctionalGroupsSequence.append(group)
        return path, dataset

    def load(self, path, dataset):
        dataset.save_as(path, enforce_file_format=True)
        return dicomlib.load_dicom([str(path)], False, return_metadata=True)

    def assert_dynamic_grid(self, out, metadata):
        self.assertEqual(out.shape, (2, 2, 2, 3))
        np.testing.assert_array_equal(out[:, :, 0, 0], [[11, 12], [21, 22]])
        self.assertEqual(metadata['dim_labels'], ['dynamic', 'slice'])
        self.assertEqual(metadata['dim_values'][0], [1, 2])
        self.assertEqual(metadata['missing_frames'], 0)
        self.assertEqual(metadata['colliding_frames'], 0)
        pickle.loads(pickle.dumps(metadata))

    def test_enhanced_dynamics_have_separate_index(self):
        for coordinates in ([(1, 1), (2, 1), (1, 2), (2, 2)],
                            [(2, 2), (2, 1), (1, 2), (1, 1)]):
            with self.subTest(coordinates=coordinates):
                path, dataset = self.enhanced_dataset(coordinates)
                out, _, metadata = self.load(path, dataset)
                self.assert_dynamic_grid(out, metadata)
                self.assertEqual(metadata['dim_values'][1], [0, 5])
                self.assertEqual(metadata['spacing'], [2, 3, 5])
                self.assertEqual(metadata['origin'], [0, 0, 5 * (coordinates[0][1] - 1)])
                self.assertEqual(metadata['orientation'], [1, 0, 0, 0, 1, 0])
                expected_frames = [coordinates.index(coordinate)
                                   for coordinate in [(1, 1), (1, 2), (2, 1), (2, 2)]]
                self.assertEqual([frame['frame'] for frame in metadata['frames']], expected_frames)

    def test_in_stack_position_without_geometry(self):
        path, dataset = self.enhanced_dataset([(2, 2), (1, 1), (2, 1), (1, 2)], geometry=False)
        out, _, metadata = self.load(path, dataset)
        self.assert_dynamic_grid(out, metadata)
        self.assertEqual(metadata['dim_values'][1], [1, 2])

    def test_per_frame_tags_override_shared_and_top_level_tags(self):
        path, dataset = self.enhanced_dataset([(1, 1), (2, 1), (1, 2), (2, 2)])
        dataset.TemporalPositionIdentifier = 9
        dataset.ImagePositionPatient = [0, 0, 99]
        content = Dataset()
        content.TemporalPositionIndex = 8
        dataset.SharedFunctionalGroupsSequence[0].FrameContentSequence = [content]
        out, _, metadata = self.load(path, dataset)
        self.assert_dynamic_grid(out, metadata)
        self.assertEqual(dataset.TemporalPositionIdentifier, 9)
        self.assertEqual(dataset.ImagePositionPatient, [0, 0, 99])
        resolved = dicomlib._frame_dataset(dataset, 0)
        self.assertEqual(resolved.TemporalPositionIndex, 1)
        self.assertFalse(hasattr(dataset, 'TemporalPositionIndex'))

    def test_classic_dynamics_are_unchanged(self):
        for tag in ('TemporalPositionIdentifier', 'AcquisitionNumber'):
            with self.subTest(tag=tag):
                paths = []
                for index, (dynamic, location) in enumerate([(2, 2), (1, 1), (2, 1), (1, 2)]):
                    path, dataset = self.save_dataset('classic{}.dcm'.format(index), [10 * dynamic + location])
                    setattr(dataset, tag, dynamic)
                    dataset.ImagePositionPatient = [0, 0, 5 * (location - 1)]
                    dataset.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
                    dataset.save_as(path, enforce_file_format=True)
                    paths.append(str(path))
                out, _, metadata = dicomlib.load_dicom(paths, False, return_metadata=True)
                self.assert_dynamic_grid(out, metadata)

    def test_single_dynamic_has_no_extra_axis(self):
        path, dataset = self.enhanced_dataset([(1, 2), (1, 1)])
        out, _, metadata = self.load(path, dataset)
        self.assertEqual(out.shape, (2, 2, 3))
        self.assertEqual(metadata['dim_labels'], ['slice'])
        np.testing.assert_array_equal(out[:, 0, 0], [11, 12])


if __name__ == '__main__':
    unittest.main()