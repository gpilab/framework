# Author: Guru Krishanmoorthy
# Date: Nov 2026

import gpi
import numpy as np

from gpi_core.examples.Voxel import documentation


class ExternalNode(gpi.NodeAPI):
    """Run a few multidimensional Voxel walkthroughs in increasing difficulty."""

    def initUI(self):
        self.addWidget('DoubleSpinBox', 'Factor', val=2.0,
                       min=-1e6, max=1e6, decimals=6)
        self.addWidget('TextBox', 'Info', val='')
        self.addWidget('PushButton', 'Voxel Documentation',
                       button_title='Open Voxel Documentation', toggle=False)
        self.addInPort('in1', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('integers', 'NPYarray')
        self.addOutPort('real2d', 'NPYarray')
        self.addOutPort('complex3d', 'NPYarray')
        self.addOutPort('matrix', 'NPYarray')
        self.addOutPort('spectrum', 'NPYarray')
        self.addOutPort('inverse_fft', 'NPYarray')
        self.addOutPort('wavelet', 'NPYarray')
        self.addOutPort('denoised', 'NPYarray')
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
            from gpi_core.examples.Voxel import voxel_basics
        except ImportError as error:
            self.log.error(
                'Run `gpi_make --all` in gpi_core/examples/Voxel before using '
                f'ArrayBasics: {error}')
            return 1

        integers = voxel_basics.integer_1d()
        print('1D integers:', integers.tolist(), 'shape:', integers.shape)
        self.setData('integers', integers)

        real = voxel_basics.real_2d()
        print('2D real:', real.tolist(), 'shape:', real.shape)
        self.setData('real2d', real)

        values = voxel_basics.complex_3d()
        print('3D complex conjugates:', values.tolist(), 'shape:', values.shape)
        self.setData('complex3d', values)

        product = voxel_basics.matrix_2d()
        print('Matrix product:', product.tolist())
        self.setData('matrix', product)

        volume = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]], dtype=np.complex64)
        print('3D FFT input:', volume.tolist())
        spectrum = voxel_basics.fft_example(volume, False)
        print('3D FFT spectrum:', spectrum.tolist())
        recovered = voxel_basics.fft_example(spectrum, True)
        print('3D inverse FFT:', recovered.tolist())
        self.setData('spectrum', spectrum)
        self.setData('inverse_fft', recovered)

        image = np.array([[1.5, 1, 0, 0], [1, 1, 0, 0],
                          [0, 0, 2, 2], [0, 0, 2, 2.5]], dtype=np.complex64)
        print('2D wavelet input:', image.tolist())
        reconstructed = voxel_basics.wavelet_example(image, 0.0)
        print('Haar reconstruction, threshold 0:', reconstructed.tolist())
        denoised = voxel_basics.wavelet_example(image, 0.5)
        print('Haar reconstruction, threshold 0.5:', denoised.tolist())
        self.setData('wavelet', reconstructed)
        self.setData('denoised', denoised)

        # Templates come last; optional input can have any number of dimensions.
        data = self.getData('in1')
        if data is None:
            data = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]], dtype=np.float32)
        factor = self.getVal('Factor')
        print('Template input:', data.tolist(), 'shape:', data.shape, 'factor:', factor)
        result = voxel_basics.array_template(data.copy(), factor)
        print('Template result, (input + input) * factor:', result.tolist())
        self.setData('out1', result)

        doubles = np.array([[1, 2], [3, 4]], dtype=np.float64)
        print('Template float64 input:', doubles.tolist())
        print('Template float64 result:',
              voxel_basics.array_template(doubles, factor).tolist())
        self.setAttr('Info', val='1D int, 2D real, 3D complex, matrices, FFT, Haar, templates.\n'
                     'FFT uses unshifted frequency order; phase is in radians.\n'
                     'out1 = (input + input) * Factor; connected input is unchanged.\n'
                     'All results are printed in the console.')
        return 0

    def execType(self):
        return gpi.GPI_PROCESS
