# Author: Guru Krishanmoorthy
# Date: Nov 2026

import os
import tempfile

import gpi
import numpy as np

from gpi_core.examples.Voxel import documentation


class ExternalNode(gpi.NodeAPI):
    """Write/read small NumPy files in a private, automatically cleaned folder."""

    def initUI(self):
        self.addWidget('TextBox', 'Info', val='')
        self.addWidget('PushButton', 'Voxel Documentation',
                       button_title='Open Voxel Documentation', toggle=False)
        self.addInPort('in1', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('integers', 'NPYarray')
        self.addOutPort('floats', 'NPYarray')
        self.addOutPort('complex', 'NPYarray')
        self.addOutPort('out1', 'NPYarray')
        return 0

    def validate(self):
        if ('Voxel Documentation' in self.widgetEvents()
                and self.getVal('Voxel Documentation')):
            self.setAttr('Voxel Documentation', val=False)
            if not documentation.open_documentation(self.log):
                return 1
        data = self.getData('in1')
        if data is None:
            return 0
        if data.dtype not in (np.float32, np.float64) or data.size == 0:
            self.log.warn('Use a non-empty native float32 or float64 array.')
            return 1
        return 0

    def compute(self):
        try:
            from gpi_core.examples.Voxel import voxel_files
        except ImportError as error:
            self.log.error(
                'Run `gpi_make --all` in gpi_core/examples/Voxel before using '
                f'NumpyFiles: {error}')
            return 1

        # TemporaryDirectory removes only this run's private files when the block ends.
        with tempfile.TemporaryDirectory(prefix='voxel_examples_') as folder:
            integers = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)
            print('Integer input:', integers.tolist())
            integers = voxel_files.integer_file(integers, os.path.join(folder, 'integers.npy'))
            print('Integer file result:', integers.tolist())
            self.setData('integers', integers)

            floats = np.array([[1.5, 2.5], [3.5, 4.5]], dtype=np.float32)
            print('Float input:', floats.tolist())
            floats = voxel_files.float_file(floats, os.path.join(folder, 'floats.npy'))
            print('Float file result:', floats.tolist())
            self.setData('floats', floats)

            values = np.array([[[1 + 2j, 3 + 4j]]], dtype=np.complex64)
            print('Complex input:', values.tolist())
            values = voxel_files.complex_file(values, os.path.join(folder, 'complex.npy'))
            print('Complex file result:', values.tolist())
            self.setData('complex', values)

            # Template last.
            data = self.getData('in1')
            if data is None:
                data = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]], dtype=np.float64)
            filename = os.path.join(folder, 'template.npy')
            print('Template input:', data.tolist())
            result = voxel_files.roundtrip_file(data.copy(), filename)
            print('Template file result:', result.tolist(), 'file:', filename)
            self.setData('out1', result)

        self.setAttr('Info', val='Wrote and read int, float, complex, and template .npy files.\n'
                     'Private temporary files have been removed; output arrays remain valid.\n'
                     'No existing user files were overwritten. All results are in the console.')
        return 0

    def execType(self):
        return gpi.GPI_PROCESS
