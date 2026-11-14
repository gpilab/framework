# Author: Guru Krishanmoorthy
# Date: Nov 2026

from contextlib import nullcontext

import gpi
import numpy as np

from gpi_core.examples.PyTorch import benchmark


_GPU_AUTO_MIN_ELEMENTS = 262144


class ExternalNode(gpi.NodeAPI):
    """Call small LibTorch C++ functions with NumPy arrays or PyTorch tensors."""

    def initUI(self):
        self.addWidget('DoubleSpinBox', 'Factor', val=2.0,
                       min=-1e6, max=1e6, decimals=6)
        self.addWidget('ExclusivePushButtons', 'Device', buttons=['auto', 'cpu', 'gpu'], val=0)
        self.addWidget('SpinBox', 'Benchmark Elements', val=1000000, min=1, max=16000000)
        self.addWidget('SpinBox', 'Benchmark Repeats', val=10, min=1, max=100)
        self.addWidget('PushButton', 'Compare CPU/GPU',
                       button_title='Compare CPU/GPU', toggle=False)
        self.addWidget('TextBox', 'Info', val='')
        self.addInPort('in1', 'NPYorTorch', obligation=gpi.OPTIONAL)
        self.addInPort('torch_in', 'TorchTensor', obligation=gpi.OPTIONAL)
        self.addOutPort('out1', 'NPYorTorch')
        return 0

    def validate(self):
        data = self.getData('in1')
        torch_data = self.getData('torch_in')
        if data is not None and torch_data is not None:
            self.log.warn('Connect either in1 or torch_in, not both.')
            return 1
        if data is None:
            data = torch_data
        if data is None:
            return 0
        if isinstance(data, np.ndarray):
            valid = data.dtype in (np.float32, np.float64) and data.size > 0
        else:
            import torch
            valid = (isinstance(data, torch.Tensor)
                     and data.dtype in (torch.float32, torch.float64) and data.numel() > 0)
        if not valid:
            self.log.warn('Use a non-empty float32 or float64 NumPy array or PyTorch tensor.')
            return 1
        return 0

    def compute(self):
        try:
            import torch
            from gpi_core.examples.PyTorch import libtorch_basics
        except ImportError as error:
            self.log.error(
                'Cannot load the LibTorch example. Run `gpi_make --all` in '
                f'gpi_core/examples/PyTorch with the GPI environment active: {error}')
            self.setData('out1', None)
            return 1

        if self.getVal('Compare CPU/GPU'):
            self.setAttr('Compare CPU/GPU', val=False)
            report = benchmark.compare_cpu_gpu(
                'libtorch', self.getVal('Benchmark Elements'), self.getVal('Benchmark Repeats'))
            report += '\nBenchmark uses private data; out1 is unchanged.'
            print(report)
            self.setAttr('Info', val=report)
            return 0

        factor = self.getVal('Factor')
        data = self.getData('in1')
        source = 'in1'
        if data is None:
            data = self.getData('torch_in')
            source = 'torch_in'
        if data is None:
            data = np.arange(6, dtype=np.float32).reshape(2, 3)
            source = 'generated sample'
        is_numpy = isinstance(data, np.ndarray)

        device = 'cpu'
        choice = self.getVal('Device')
        if choice == 0:  # auto
            size = data.size if is_numpy else data.numel()
            if not is_numpy and data.device.type != 'cpu':
                if str(data.device) in gpi.torch_devices():
                    device = str(data.device)
            elif size >= _GPU_AUTO_MIN_ELEMENTS:
                device = gpi.torch_auto_device()
        elif choice == 2:  # gpu
            device = gpi.torch_auto_device()
            if device == 'cpu':
                self.log.warn('No usable GPU found; running on CPU.')
        uses_gpu = device != 'cpu' or (not is_numpy and data.device.type != 'cpu')

        with gpi.gpu_exclusive() if uses_gpu else nullcontext():
            print('LibTorch device:', device)

            # 1. Integer functions.
            integers = torch.tensor([1, 2, 3], dtype=torch.int32, device=device)
            print('int input:', integers.tolist(), 'factor:', 2)
            print('int copy:', libtorch_basics.scale_int(integers, 2).tolist())
            libtorch_basics.scale_int_inplace(integers, 2)
            print('int in-place:', integers.tolist())

            # 2. Float functions.
            floats = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32, device=device)
            print('float input:', floats.tolist(), 'factor:', factor)
            print('float copy:', libtorch_basics.scale_float(floats, factor).tolist())
            libtorch_basics.scale_float_inplace(floats, factor)
            print('float in-place:', floats.tolist())

            # 3. Complex functions.
            values = torch.tensor([1 + 2j, 3 + 4j], dtype=torch.complex64, device=device)
            print('complex input:', values.tolist(), 'factor:', 1j)
            print('complex copy:', libtorch_basics.scale_complex(values, 1j).tolist())
            libtorch_basics.scale_complex_inplace(values, 1j)
            print('complex in-place:', values.tolist())

            # 4. Template functions last, on a private copy of connected data.
            print('Node input:', data.tolist(), 'source:', source, 'factor:', factor)
            if is_numpy:
                tensor = torch.from_numpy(data.copy()).to(device)
            else:
                tensor = data.to(device).clone()
            scaled = libtorch_basics.scale(tensor, factor)
            result = scaled.cpu().numpy() if is_numpy else scaled
            print('Template copy result:', result.tolist())
            libtorch_basics.scale_inplace(tensor, factor)
            print('Template in-place result:', tensor.tolist())

        self.setData('out1', result)
        self.setAttr('Info', val=(
            f'Backend: LibTorch C++ {device}\nShape: {result.shape}\nDtype: {result.dtype}\n'
            f'Factor: {factor}\nSource: {source}\n'
            'Integer, float, complex, then template C++ functions.\n'
            'NumPy input gives NumPy output; tensor input gives tensor output.\n'
            'Connect either in1 or torch_in, not both; leave both empty for a sample.\n'
            'Auto follows the FFT node: keep enabled GPU tensors on GPU;\n'
            'otherwise use GPU if available at 262144+ elements, CPU for smaller arrays.\n'
            'Connected input is unchanged. Python and C++ results are in the console.'
        ))
        return 0

    def execType(self):
        return gpi.GPI_THREAD
