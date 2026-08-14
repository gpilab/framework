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

import numpy as np
import gpi


class ExternalNode(gpi.NodeAPI):
    """Convert a NumPy array to a PyTorch tensor.

    Widgets:
        dtype  — target torch dtype (keep input dtype by default).
        Device — dropdown of devices detected at node load time: always
                 'cpu', plus 'cuda:N' for each GPU with working CUDA drivers,
                 or 'mps' on Apple Silicon.
        info   — shows resulting dtype, shape, and device.

    Note: use GPI_THREAD execType if the downstream pipeline is GPU-only so
    that tensors share memory without a CPU round-trip between processes.
    """

    def initUI(self):
        dtype_options = [
            'keep', 'float16', 'float32', 'float64',
            'int8', 'int16', 'int32', 'int64',
            'uint8', 'complex64', 'complex128', 'bool',
        ]
        self.dtype_options = dtype_options
        self.addWidget('ExclusiveRadioButtons', 'dtype', buttons=dtype_options, val=0)
        self.addWidget('ComboBox', 'Device', items=gpi.torch_devices(), val='cpu')
        self.addWidget('TextBox', 'info', val='')

        self.addInPort('in',  'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'TorchTensor')

    def compute(self):
        import torch

        data   = self.getData('in')
        device = self.getVal('Device').strip() or 'cpu'
        choice = self.getVal('dtype')
        dtype_name = self.dtype_options[choice]

        _dtype_map = {
            'float16':   torch.float16,
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

        arr = np.array(data, copy=True, order='C')
        tensor = torch.from_numpy(arr)

        if dtype_name != 'keep':
            tensor = tensor.to(dtype=_dtype_map[dtype_name])

        tensor = tensor.to(device=device)

        self.setAttr('info', val=(
            f'dtype  : {tensor.dtype}\n'
            f'shape  : {tuple(tensor.shape)}\n'
            f'device : {tensor.device}'
        ))
        self.setData('out', tensor)
        return 0

    def execType(self):
        return gpi.GPI_THREAD
