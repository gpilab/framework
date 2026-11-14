# Author: Guru Krishanmoorthy
# Date: Nov 2026

import gpi
import numpy as np

from gpi_core.examples.Voxel import documentation


class ExternalNode(gpi.NodeAPI):
    """Explore FFT options and multilevel 3D Daubechies D4 wavelets."""

    def initUI(self):
        self.addWidget('DoubleSpinBox', 'Threshold', val=0.5, min=0.0, max=1000.0)
        self.addWidget('TextBox', 'Info', val='')
        self.addWidget('PushButton', 'Voxel Documentation',
                       button_title='Open Voxel Documentation', toggle=False)
        self.addInPort('in1', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('last_axis', 'NPYarray')
        self.addOutPort('centered', 'NPYarray')
        self.addOutPort('ortho', 'NPYarray')
        self.addOutPort('no_normalization', 'NPYarray')
        self.addOutPort('planned', 'NPYarray')
        self.addOutPort('d4_recovered', 'NPYarray')
        self.addOutPort('d4_thresholded', 'NPYarray')
        self.addOutPort('d4_skip_coarse', 'NPYarray')
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
        if data.dtype != np.complex64 or data.size == 0 or data.ndim == 0:
            self.log.warn('Use a non-empty native complex64 array with at least one axis.')
            return 1
        return 0

    def compute(self):
        try:
            from gpi_core.examples.Voxel import voxel_transform_options
        except ImportError as error:
            self.log.error(
                'Run `gpi_make --all` in gpi_core/examples/Voxel before using '
                f'TransformOptions: {error}')
            return 1

        data = self.getData('in1')
        if data is None:
            data = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.complex64)
        data = data.copy()
        print('FFT input:', data.tolist())

        last_axis = voxel_transform_options.last_axis_fft(data)
        print('Last-axis FFT:', last_axis.tolist())
        self.setData('last_axis', last_axis)

        centered = voxel_transform_options.centered_fft_2d()
        print('Centered FFT of [[1,2,3],[4,5,6],[7,8,9]]:', centered.tolist())
        self.setData('centered', centered)

        ortho = voxel_transform_options.orthonormal_fft(data)
        print('Orthonormal FFT:', ortho.tolist())
        self.setData('ortho', ortho)

        unnormalized = voxel_transform_options.unnormalized_roundtrip(data)
        print('Unnormalized round trip (input * size):', unnormalized.tolist())
        self.setData('no_normalization', unnormalized)

        planned = voxel_transform_options.planned_roundtrip(data)
        print('Two round trips with one orthonormal plan:', planned.tolist())
        self.setData('planned', planned)

        volume = np.arange(64, dtype=np.complex64).reshape(4, 4, 4)
        threshold = self.getVal('Threshold')
        print('3D D4 input:', volume.tolist(), 'threshold:', threshold)
        recovered = voxel_transform_options.d4_volume(volume, 0.0, False)
        print('Two-level D4 reconstruction:', recovered.tolist())
        self.setData('d4_recovered', recovered)

        thresholded = voxel_transform_options.d4_volume(volume, threshold, False)
        print('D4 thresholds [threshold, threshold / 2]:', thresholded.tolist())
        self.setData('d4_thresholded', thresholded)

        skip_coarse = voxel_transform_options.d4_volume(volume, threshold, True)
        print('D4 with the coarsest detail level skipped:', skip_coarse.tolist())
        self.setData('d4_skip_coarse', skip_coarse)
        self.setAttr('Info', val='FFT input is used for last-axis, normalization, and plan examples.\n'
                     'Centered FFT uses a fixed 3x3 image; D4 uses a fixed 4x4x4 volume.\n'
                     'D4 uses two levels and automatic internal padding.\n'
                     'Connected input is unchanged. All results are in the console.')
        return 0

    def execType(self):
        return gpi.GPI_PROCESS
