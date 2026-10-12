import os

import gpi
import numpy as np


class ExternalNode(gpi.NodeAPI):
    """Read a NIfTI-1 or NIfTI-2 image from .nii or .nii.gz.

    out: Array in native NIfTI (X, Y, Z, ...) axis order, with header
        intensity scaling applied. Singleton and time dimensions are preserved.
    NiftiDict: Original header fields, converted to Python values.
    NIfTI Metadata: Affine, voxel spacing, orientation and scaling information.

    The affine maps the first three output indices to RAS+ world coordinates.
    No anatomical reorientation, transpose or squeezing is performed.
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('OpenFileBrowser', 'File Browser',
                       button_title='Browse', caption='Open File',
                       filter='NIfTI files (*.nii *.nii.gz);;All files (*)')
        self.addWidget('PushButton', 'Read', toggle=True, val=0)

        self.addOutPort(title='out', type='NPYarray')
        self.addOutPort(title='NiftiDict', type='DICT')
        self.addOutPort(title='NIfTI Metadata', type='DICT')
        self.URI = gpi.TranslateFileURI

    def validate(self):
        fname = self.URI(self.getVal('File Browser'))
        self.setDetailLabel(fname)
        return 0

    def compute(self):
        if not self.getVal('Read'):
            self._clear_outputs()
            return 0

        fname = self.URI(self.getVal('File Browser'))
        try:
            if not fname or not os.path.isfile(fname):
                raise ValueError('File not found: {}'.format(fname))
            if not fname.lower().endswith(('.nii', '.nii.gz')):
                raise ValueError('Select a .nii or .nii.gz file.')

            import nibabel as nib

            image = nib.load(fname)
            if not isinstance(image, (nib.Nifti1Image, nib.Nifti2Image)):
                raise ValueError('The selected file is not a NIfTI image.')

            out = np.array(np.asanyarray(image.dataobj), copy=True)
            header = {key: image.header[key].tolist()
                      for key in image.header.keys()}
            spatial_unit, time_unit = image.header.get_xyzt_units()
            metadata = {
                'filename': fname,
                'shape': list(out.shape),
                'dtype': str(out.dtype),
                'storage_dtype': str(image.get_data_dtype()),
                'affine': image.affine.tolist(),
                'spacing': [float(value) for value in image.header.get_zooms()],
                'orientation': list(nib.aff2axcodes(image.affine)),
                'spatial_unit': spatial_unit,
                'time_unit': time_unit,
                'slope': float(image.dataobj.slope),
                'intercept': float(image.dataobj.inter),
                'qform_code': int(image.header['qform_code']),
                'sform_code': int(image.header['sform_code']),
                'axis_order': 'Native NIfTI (X, Y, Z, ...)',
            }
            info = ('file: {}\nfile size (bytes): {}\ndimensions: {}\n'
                    'type: {}\nvoxel spacing: {}\norientation: {}\n'
                    'spatial unit: {}\ntime unit: {}\n'
                    'axis order: {}\nscaling (slope, intercept): ({}, {})').format(
                        fname, os.path.getsize(fname), list(out.shape), out.dtype,
                        metadata['spacing'], ''.join(metadata['orientation']),
                        spatial_unit, time_unit, metadata['axis_order'],
                        metadata['slope'], metadata['intercept'])
        except Exception as error:
            self._clear_outputs()
            self.log.error('ReadNIfTI: failed to read {}: {}'.format(fname, error))
            self.setAttr('I/O Info:', val='Failed to read file:\n{}\n\n{}'.format(
                fname, error))
            return 1

        self.setData('out', out)
        self.setData('NiftiDict', header)
        self.setData('NIfTI Metadata', metadata)
        self.setAttr('I/O Info:', val=info)
        return 0

    def _clear_outputs(self):
        self.setData('out', None)
        self.setData('NiftiDict', None)
        self.setData('NIfTI Metadata', None)