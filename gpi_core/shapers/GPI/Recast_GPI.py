# Copyright (c) 2014, Dignity Health
#
#     The GPI core node library is licensed under
# either the BSD 3-clause or the LGPL v. 3.
#
#     Under either license, the following additional term applies:
#
#         NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL
# PURPOSES AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
# SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
# PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
# USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT LIMITED
# TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR MAKES NO
# WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE SOFTWARE IN ANY
# HIGH RISK OR STRICT LIABILITY ACTIVITIES.
#
#     If you elect to license the GPI core node library under the LGPL the
# following applies:
#
#         This file is part of the GPI core node library.
#
#         The GPI core node library is free software: you can redistribute it
# and/or modify it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version. GPI core node library is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
#         You should have received a copy of the GNU Lesser General Public
# License along with the GPI core node library. If not, see
# <http://www.gnu.org/licenses/>.


# Author: Dallas Turley
# Date: 2013sep09
# Updated: 2026 — added PyTorch tensor support (numpy↔torch conversion)

import numpy as np
import gpi


class ExternalNode(gpi.NodeAPI):
    """Recast data type or convert between NumPy arrays and PyTorch tensors.

    Accepts either a NumPy array or a PyTorch tensor as input.

    Output Format = NumPy Array
        Converts (or keeps) the data as a NumPy array with the selected dtype.
        If the input is a PyTorch tensor it is moved to CPU first.

    Output Format = PyTorch Tensor
        Converts (or keeps) the data as a PyTorch tensor with the selected
        dtype and device.  Requires PyTorch to be installed.
        Note: GPI worker processes always transfer tensors between nodes as CPU
        tensors.  Use this node to move the tensor to the desired device at the
        start of each GPU-bound compute node.
    """

    _NP_DTYPES = [
        'int8', 'int16', 'int32', 'int64',
        'uint8', 'uint16', 'uint32', 'uint64',
        'float16', 'float32', 'float64',
        'complex64', 'complex128',
    ]

    _TORCH_DTYPES = [
        'float16', 'bfloat16', 'float32', 'float64',
        'int8', 'int16', 'int32', 'int64',
        'uint8', 'complex64', 'complex128', 'bool',
    ]

    def initUI(self):
        self.addWidget('ExclusiveRadioButtons', 'Output Format',
                       buttons=['NumPy Array', 'PyTorch Tensor'], val=0)

        self.addWidget('ExclusiveRadioButtons', 'NumPy dtype',
                       buttons=self._NP_DTYPES, val=10)  # float64

        self.addWidget('ExclusiveRadioButtons', 'Torch dtype',
                       buttons=self._TORCH_DTYPES, val=2,   # float32
                       visible=False)

        self.addWidget('StringBox', 'Device', val='cpu', visible=False)

        self.addWidget('TextBox', 'info', val='')

        self.addInPort('in',  'NPYorTorch', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'PASS')

    def compute(self):
        out_format = self.getVal('Output Format')  # 0 = NumPy, 1 = Torch

        # Update widget visibility whenever Output Format changes —
        # widget events also trigger compute() so this fires immediately.
        self.setAttr('NumPy dtype', visible=(out_format == 0))
        self.setAttr('Torch dtype', visible=(out_format == 1))
        self.setAttr('Device',      visible=(out_format == 1))

        data = self.getData('in')
        if data is None:
            return 0

        if out_format == 0:
            out = self._to_numpy(data)
            if out is None:
                return 1
            self.setAttr('info',
                         val=f'input : {_describe(data)}\noutput: {out.dtype}  {tuple(out.shape)}')
            self.setData('out', out)

        else:
            out = self._to_torch(data)
            if out is None:
                return 1
            self.setAttr('info',
                         val=f'input : {_describe(data)}\noutput: {out.dtype}  {tuple(out.shape)}  {out.device}')
            self.setData('out', out)

        return 0

    # ── helpers ───────────────────────────────────────────────────────────────

    def _to_numpy(self, data):
        """Return data as a NumPy array with the selected dtype."""
        np_dtype = self._NP_DTYPES[self.getVal('NumPy dtype')]

        # torch → numpy
        try:
            import torch
            if isinstance(data, torch.Tensor):
                data = data.detach().cpu().contiguous().numpy()
        except ImportError:
            pass

        if not isinstance(data, np.ndarray):
            self.log.error('Recast: input is neither a NumPy array nor a PyTorch tensor.')
            return None

        return data.astype(np_dtype)

    def _to_torch(self, data):
        """Return data as a PyTorch tensor with the selected dtype and device."""
        if not self.moduleExists('torch'):
            self.log.error('Recast: PyTorch is not installed.')
            return None

        import torch

        _dtype_map = {
            'float16':   torch.float16,
            'bfloat16':  torch.bfloat16,
            'float32':   torch.float32,
            'float64':   torch.float64,
            'int8':      torch.int8,
            'int16':     torch.int16,
            'int32':     torch.int32,
            'int64':     torch.int64,
            'uint8':     torch.uint8,
            'complex64':  torch.complex64,
            'complex128': torch.complex128,
            'bool':      torch.bool,
        }

        torch_dtype = _dtype_map[self._TORCH_DTYPES[self.getVal('Torch dtype')]]
        device = self.getVal('Device').strip() or 'cpu'

        if isinstance(data, np.ndarray):
            # numpy complex arrays need real-only dtypes warned about
            if np.iscomplexobj(data) and torch_dtype not in (torch.complex64, torch.complex128):
                self.log.warn('Recast: complex input — imaginary part discarded for real torch dtype.')
                data = data.real
            return torch.from_numpy(np.ascontiguousarray(data)).to(dtype=torch_dtype, device=device)

        if isinstance(data, torch.Tensor):
            return data.detach().to(dtype=torch_dtype, device=device)

        self.log.error('Recast: input is neither a NumPy array nor a PyTorch tensor.')
        return None

    def execType(self):
        return gpi.GPI_PROCESS


def _describe(data):
    """One-line summary of data type and shape."""
    try:
        import torch
        if isinstance(data, torch.Tensor):
            return f'torch.{data.dtype}  {tuple(data.shape)}  {data.device}'
    except ImportError:
        pass
    if isinstance(data, np.ndarray):
        return f'{data.dtype}  {tuple(data.shape)}'
    return type(data).__name__
