# Author: Guru Krishanmoorthy
# Date: Nov 2026

import gpi
import numpy as np

from gpi_core.examples.Voxel import documentation


class ExternalNode(gpi.NodeAPI):
    """Explore grouped array, math, vector, and matrix options."""

    def initUI(self):
        self.addWidget('DoubleSpinBox', 'Offset', val=1.0, min=-1e6, max=1e6)
        self.addWidget('DoubleSpinBox', 'Divisor', val=2.0, min=0.001, max=1e6)
        self.addWidget('TextBox', 'Info', val='')
        self.addWidget('PushButton', 'Voxel Documentation',
                       button_title='Open Voxel Documentation', toggle=False)
        self.addInPort('in1', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('layout', 'NPYarray')
        self.addOutPort('math', 'NPYarray')
        self.addOutPort('mask', 'NPYarray')
        self.addOutPort('outer', 'NPYarray')
        self.addOutPort('hermitian', 'NPYarray')
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
            from gpi_core.examples.Voxel import voxel_array_options
        except ImportError as error:
            self.log.error(
                'Run `gpi_make --all` in gpi_core/examples/Voxel before using '
                f'ArrayOptions: {error}')
            return 1

        layout = voxel_array_options.layout_options()
        print('Converted, resized, and sliced:', layout.tolist(), 'shape:', layout.shape)
        self.setData('layout', layout)

        math = voxel_array_options.math_options()
        print('Subtract, divide, and clamp:', math.tolist())
        self.setData('math', math)

        mask = voxel_array_options.mask_options()
        print('Mask for values > 3:', mask.tolist())
        self.setData('mask', mask)

        outer = voxel_array_options.vector_options()
        print('Outer product:', outer.tolist())
        self.setData('outer', outer)

        hermitian = voxel_array_options.matrix_options()
        print('Hermitian (conjugate transpose):', hermitian.tolist())
        self.setData('hermitian', hermitian)

        # Template last.
        data = self.getData('in1')
        if data is None:
            data = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]], dtype=np.float64)
        offset = self.getVal('Offset')
        divisor = self.getVal('Divisor')
        print('Template input:', data.tolist(), 'offset:', offset, 'divisor:', divisor)
        result = voxel_array_options.subtract_and_divide(data.copy(), offset, divisor)
        print('Template result:', result.tolist())
        self.setData('out1', result)
        self.setAttr('Info', val='Layout, pointwise math, masks, vectors, SVD modes, Hermitian.\n'
                     'C++ prints scalar comparisons and matrix-mode details.\n'
                     'out1 = (input - Offset) / Divisor; connected input is unchanged.')
        return 0

    def execType(self):
        return gpi.GPI_PROCESS
