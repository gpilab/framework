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


# Author: Daniel Borup
# Date: January 2019
# Notes: Adapted from Math node

import numpy as np
import gpi


# name -> (numpy attr, torch attr).  Both backends expose the same call
# signature, so the op table is all that differs between them.
_OP_FUNCS = {
    'Add':         ('add',           'add'),
    'Subtract':    ('subtract',      'subtract'),
    'Multiply':    ('multiply',      'multiply'),
    'Divide':      ('divide',        'divide'),
    'Power':       ('power',         'pow'),
    'Exponential': ('exp',           'exp'),
    'LogN':        ('log',           'log'),
    'Log10':       ('log10',         'log10'),
    'Reciprocal':  ('reciprocal',    'reciprocal'),
    'Conjugate':   ('conj',          'conj_physical'),
    'Magnitude':   ('abs',           'abs'),
    'Sin':         ('sin',           'sin'),
    'Cos':         ('cos',           'cos'),
    'Tan':         ('tan',           'tan'),
    'arcSin':      ('arcsin',        'asin'),
    'arcCos':      ('arccos',        'acos'),
    'arcTan':      ('arctan',        'atan'),
    'arcTan2':     ('arctan2',       'atan2'),
    'Max':         ('maximum',       'maximum'),
    'Min':         ('minimum',       'minimum'),
    '>':           ('greater',       'gt'),
    '<':           ('less',          'lt'),
    '==':          ('equal',         'eq'),
    '!=':          ('not_equal',     'ne'),
    '>=':          ('greater_equal', 'ge'),
    '<=':          ('less_equal',    'le'),
}

# ops that take a second operand (another port, or the Scalar widget)
_BINARY_OPS = {'Add', 'Subtract', 'Multiply', 'Divide', 'Power', 'arcTan2',
               'Max', 'Min', '>', '<', '==', '!=', '>=', '<='}

# ops whose second operand may come from the Scalar widget
_SCALAR_OPS = {'Add', 'Subtract', 'Multiply', 'Divide', 'Power',
               '>', '<', '==', '!=', '>=', '<='}

_ANGLE_IN_OPS = {'Sin', 'Cos', 'Tan'}
_ANGLE_OUT_OPS = {'arcSin', 'arcCos', 'arcTan', 'arcTan2'}

_TRIG_LABELS = ['Deg', 'Rad', 'Cyc']

# Below this many elements the host<->device round trip costs more than the
# elementwise op saves, so 'auto' stays on the CPU.
_GPU_AUTO_MIN_ELEMENTS = 1 << 20


def _device_buttons():
    '''auto/gpu are omitted entirely (not just disabled) when no accelerator
    is enabled/available, so the Device widget never offers a GPU choice
    that would silently no-op back to the CPU.'''
    try:
        devices = gpi.torch_devices(wait=False)
    except Exception:
        devices = ['cpu']
    if any(d != 'cpu' for d in devices):
        return ['auto', 'cpu', 'gpu']
    return ['cpu']


def _op_labels(mode, inputs):
    '''The operations offered for a given Mode and number of connected ports.

    The order of each list is part of the node's saved state (widget index),
    so entries must only ever be appended, never reordered or removed.
    '''
    if inputs == 2:
        return {
            0: ['Add', 'Subtract', 'Multiply', 'Divide', 'Power'],
            1: ['arcTan2'],
            2: ['Max', 'Min', '>', '<', '==', '!=', '>=', '<='],
        }[mode]
    if inputs == 1:
        return {
            0: ['Add', 'Subtract', 'Multiply', 'Divide', 'Power',
                'Exponential', 'LogN', 'Log10', 'Reciprocal', 'Conjugate',
                'Magnitude'],
            1: ['Sin', 'Cos', 'Tan', 'arcSin', 'arcCos', 'arcTan'],
            2: ['>', '<', '==', '!=', '>=', '<='],
        }[mode]
    return list(_OP_FUNCS.keys())


def _is_torch(data):
    if data is None:
        return False
    mod = type(data).__module__
    return mod.split('.')[0] == 'torch'


class ExternalNode(gpi.NodeAPI):
    """Perform real or complex scalar operations on a per element basis.

       Accepts NumPy arrays and/or PyTorch tensors on either port, and can run
       the operation on the GPU.

       Three Modes of Operation:
        1) Standard - basic Arithmetic and exponential operations.
        2) Trigonometric - basic Trigonometric operations.
        3) Comparison - returns maximum, minimum, or bit mask based on
                        comparison between inputs or against Scalar.

       Operations which do not commute (e.g. divide) operate left to right, e.g.:
         output = (left port) / (right port)

       Device:
         auto - GPU when an input is already a CUDA/MPS tensor, or when the
                array is large enough for the transfer to pay off; CPU
                otherwise.
         cpu  - always run on the host.
         gpu  - always run on the accelerator (falls back to CPU, with a
                warning, if none is usable).

       The output is always the same kind (numpy/torch) as the input and is
       always on the CPU: ports never hold device-resident data.
    """

    def initUI(self):
        self.op_labels = _op_labels(0, 0)
        self.inputs = 0

        # Widgets
        self.addWidget('ExclusivePushButtons', 'Mode', buttons=[
                       'Standard', 'Trigonometric', 'Comparison'], val=0)
        self.addWidget('ExclusivePushButtons', 'Units',
                       buttons=_TRIG_LABELS, val=1)
        self.addWidget('ExclusiveRadioButtons', 'Operation',
                       buttons=self.op_labels, val=0)
        self.addWidget('DoubleSpinBox', 'Scalar', val=0.0, decimals=5)
        self.addWidget('ExclusivePushButtons', 'Device',
                       buttons=['auto', 'cpu', 'gpu'], val=0)
        self.addWidget('PushButton', 'compute', toggle=True, val=True)
        self.addWidget('TextBox', 'info', val='')

        # IO Ports
        self.addInPort('inLeft', 'NPYorTorch', obligation=gpi.OPTIONAL)
        self.addInPort('inRight', 'NPYorTorch', obligation=gpi.OPTIONAL)
        self.addOutPort('out', 'NPYorTorch')

    def validate(self):
        '''update the widgets based on the input arrays
        '''
        data1 = self.getData('inLeft')
        data2 = self.getData('inRight')

        mode = self.getVal('Mode')
        self.inputs = (data1 is not None) + (data2 is not None)
        self.op_labels = _op_labels(mode, self.inputs)

        self.setAttr('Operation', buttons=self.op_labels)
        if self.getVal('Operation') >= len(self.op_labels):
            self.setAttr('Operation', val=0)

        opname = self.op_labels[min(self.getVal('Operation'),
                                    len(self.op_labels) - 1)]

        self.setAttr('Scalar',
                     visible=(self.inputs == 1 and opname in _SCALAR_OPS))
        self.setAttr('Units', visible=(mode == 1))

        # set the detail label
        if mode == 1:
            funcStr = '{} ({})'.format(opname,
                                       _TRIG_LABELS[self.getVal('Units')])
        else:
            funcStr = '{}'.format(opname)

        if self.getAttr('Scalar', 'visible'):
            self.setDetailLabel("{}, scalar = {}".format(
                                    funcStr, self.getVal('Scalar')))
        else:
            self.setDetailLabel(funcStr)

        self.device_buttons = _device_buttons()
        self.setAttr('Device', buttons=self.device_buttons)
        if self.getVal('Device') >= len(self.device_buttons):
            self.setAttr('Device', val=0)

        return 0

    def compute(self):
        if not self.getVal('compute'):
            return 0

        data1 = self.getData('inLeft')
        data2 = self.getData('inRight')
        if data1 is None and data2 is None:
            return 0

        mode = self.getVal('Mode')
        op_labels = _op_labels(mode, (data1 is not None) + (data2 is not None))
        opname = op_labels[min(self.getVal('Operation'), len(op_labels) - 1)]

        # remember what the caller sent us, for Output='match input'
        primary_was_torch = _is_torch(data1 if data1 is not None else data2)

        device = self._resolve_device(data1, data2)
        use_torch = device is not None

        try:
            if use_torch:
                import torch
                xp = torch
                data1 = self._as_torch(data1, device)
                data2 = self._as_torch(data2, device)
            else:
                xp = np
                data1 = self._as_numpy(data1)
                data2 = self._as_numpy(data2)

            data1 = self._promote_bool(xp, data1)
            data2 = self._promote_bool(xp, data2)

            if opname in _ANGLE_IN_OPS:
                data1 = self._to_radians(xp, data1)
                data2 = self._to_radians(xp, data2)

            func = getattr(xp, _OP_FUNCS[opname][1 if use_torch else 0])
            primary = data1 if data1 is not None else data2

            if opname in _BINARY_OPS:
                if data1 is not None and data2 is not None:
                    other = data2
                else:
                    other = self._as_operand(xp, self.getVal('Scalar'), primary)
                out = func(primary, other)
            else:
                out = func(primary)

            if opname in _ANGLE_OUT_OPS:
                out = self._from_radians(xp, out)

            out = self._to_output_kind(out, primary_was_torch)
        except Exception as e:
            self.log.error('{} failed: {}'.format(opname, e))
            if 'out of memory' in str(e).lower():
                self._free_device_memory()
                self.log.error('GPU ran out of memory -- set Device to "cpu" '
                               'or use a smaller array.')
            return 1

        self.setAttr('info', val=(
            'op     : {}\n'
            'device : {}\n'
            'kind   : {}\n'
            'dtype  : {}\n'
            'shape  : {}'.format(opname, device or 'cpu',
                                 'torch' if _is_torch(out) else 'numpy',
                                 out.dtype, tuple(out.shape))))
        self.setData('out', out)
        return 0

    def execType(self):
        # GPI_THREAD (not GPI_PROCESS) so that all CUDA work in the app shares
        # a single context -- see the GPU convention in the repo docs.
        return gpi.GPI_THREAD

    # ---- helpers -----------------------------------------------------------

    def _free_device_memory(self):
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def _resolve_device(self, data1, data2):
        '''Return the torch device string to compute on, or None for numpy.'''
        buttons = getattr(self, 'device_buttons', ['auto', 'cpu', 'gpu'])
        choice = buttons[self.getVal('Device')]
        if choice == 'cpu':
            # keep torch data in torch, just on the host
            return 'cpu' if (_is_torch(data1) or _is_torch(data2)) else None

        try:
            devices = gpi.torch_devices()
        except Exception:
            devices = ['cpu']
        accel = [d for d in devices if d != 'cpu']

        if choice == 'gpu':
            if not accel:
                self.log.warn('No usable GPU found, falling back to the CPU.')
                return 'cpu' if (_is_torch(data1) or _is_torch(data2)) else None
            return gpi.torch_auto_device()

        # auto
        if not accel:
            return 'cpu' if (_is_torch(data1) or _is_torch(data2)) else None
        for d in (data1, data2):
            if _is_torch(d) and d.device.type != 'cpu':
                return str(d.device)
        nelem = max((d.size if isinstance(d, np.ndarray) else d.numel())
                    for d in (data1, data2) if d is not None)
        if nelem >= _GPU_AUTO_MIN_ELEMENTS:
            return gpi.torch_auto_device()
        return 'cpu' if (_is_torch(data1) or _is_torch(data2)) else None

    def _as_torch(self, data, device):
        if data is None:
            return None
        import torch
        if _is_torch(data):
            return data.to(device=device)
        # getData() hands back a read-only view; torch.tensor() copies, which
        # avoids the "non-writable array" warning from from_numpy().
        return torch.tensor(np.ascontiguousarray(data), device=device)

    def _as_numpy(self, data):
        if data is None:
            return None
        if _is_torch(data):
            return data.detach().cpu().numpy()
        return data

    def _promote_bool(self, xp, data):
        if data is None:
            return None
        if data.dtype == (xp.bool if xp is not np else np.bool_):
            return data.to(xp.float32) if xp is not np else data.astype(float)
        return data

    def _to_radians(self, xp, data):
        if data is None:
            return None
        units = self.getVal('Units')
        if units == 0:    # Deg
            return xp.deg2rad(data)
        elif units == 2:  # Cyc
            return xp.deg2rad(data * 360)
        return data

    def _from_radians(self, xp, data):
        units = self.getVal('Units')
        if units == 0:    # Deg
            return xp.rad2deg(data)
        elif units == 2:  # Cyc
            return xp.rad2deg(data) / 360
        return data

    def _as_operand(self, xp, scalar, like):
        '''Wrap the Scalar widget value so torch ops that require two tensors
        (maximum/minimum) accept it.'''
        if xp is np:
            return scalar
        return xp.as_tensor(scalar, device=like.device)

    def _to_output_kind(self, out, primary_was_torch):
        '''Match the input kind; ports never hold device-resident data.'''
        if _is_torch(out):
            out = out.detach().cpu()
            if not primary_was_torch:
                out = out.numpy()
        return out
