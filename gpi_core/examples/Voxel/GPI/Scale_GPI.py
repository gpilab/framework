# Author: Guru Krishanmoorthy
# Date: Nov 2026

import gpi
import numpy as np

from gpi_core.examples.Voxel import documentation


class ExternalNode(gpi.NodeAPI):
    """Run simple Voxel examples without modifying connected input."""

    def initUI(self):
        self.addWidget('DoubleSpinBox', 'Scale Factor', val=2.0,
                       min=-1e6, max=1e6, decimals=6)
        self.addWidget('TextBox', 'Info', val='')
        self.addWidget('PushButton', 'Voxel Documentation',
                       button_title='Open Voxel Documentation', toggle=False)

        self.addInPort('in1', 'NPYarray', obligation=gpi.OPTIONAL)
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
        if data.dtype not in (np.float32, np.float64):
            self.log.warn('Voxel Scale requires native-endian float32 or float64 input.')
            return 1
        if data.size == 0:
            self.log.warn('Voxel Scale requires a non-empty array.')
            return 1
        return 0

    def compute(self):
        try:
            from gpi_core.examples.Voxel import voxel_scale
        except ImportError as error:
            self.log.error(
                'Cannot load the Voxel Scale extension. Run `gpi_make --all` '
                f'in gpi_core/examples/Voxel with the GPI environment active: {error}')
            self.setData('out1', None)
            return 1

        data = self.getData('in1')
        source = 'connected input'
        if data is None:
            data = np.arange(6, dtype=np.float32).reshape(2, 3)
            source = 'generated sample'
        input_array = data.copy()
        factor = self.getVal('Scale Factor')

        # 1. Integer examples.
        integers = np.array([1, 2, 3], dtype=np.int32)
        print('int: input =', integers, 'factor =', 2)
        print('scale_int result:', voxel_scale.scale_int(integers, 2))
        voxel_scale.scale_int_inplace(integers, 2)
        print('scale_int_inplace result:', integers)

        # 2. Float examples.
        floats = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        print('float: input =', floats, 'factor =', factor)
        print('scale_float result:', voxel_scale.scale_float(floats, factor))
        voxel_scale.scale_float_inplace(floats, factor)
        print('scale_float_inplace result:', floats)

        # 3. Complex examples.
        values = np.array([1 + 2j, 3 + 4j], dtype=np.complex64)
        print('complex: input =', values, 'factor =', 1j)
        print('scale_complex result:', voxel_scale.scale_complex(values, 1j))
        voxel_scale.scale_complex_inplace(values, 1j)
        print('scale_complex_inplace result:', values)

        # 4. Template examples: float32, then float64.
        floats = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        print('template float32: input =', floats, 'factor =', factor)
        print('scale result:', voxel_scale.scale(floats, factor))
        voxel_scale.scale_inplace(floats, factor)
        print('scale_inplace result:', floats)

        doubles = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        print('template float64: input =', doubles, 'factor =', factor)
        print('scale result:', voxel_scale.scale(doubles, factor))
        voxel_scale.scale_inplace(doubles, factor)
        print('scale_inplace result:', doubles)

        print(f'Node input ({source}):', data.tolist())
        result = voxel_scale.scale(input_array, factor)
        print(f'Node output (factor = {factor}):', result.tolist())

        self.setData('out1', result)
        self.setAttr('Info', val=(
            f'Backend: Voxel C++\nShape: {result.shape}\n'
            f'Dtype: {result.dtype}\nScale factor: {factor}\n'
            f'Source: {source}\n'
            'All results are printed in the GPI console.\n'
            'Connected input is unchanged.'
        ))
        return 0

    def execType(self):
        return gpi.GPI_PROCESS
