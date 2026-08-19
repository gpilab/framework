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


# Authors: Nick Zwart, Ryan Robison (original FFTW_GPI/FFT_NUMPY_GPI)
# Merged into a single CPU/GPU node: 2026-08-18
# Replaces FFTW_GPI (pyfftw C-extension) and FFT_NUMPY_GPI (numpy-only) with
# one node: same per-dimension crop/zero-pad/transform UI, backend picked
# automatically (numpy on CPU, torch.fft on GPU) based on hardware and size.

import numpy as np
import gpi
from gpi import QtWidgets

# Below this many elements the host<->device round trip costs more than the
# transform saves, so 'auto' stays on the CPU (same threshold as Math_GPI).
_GPU_AUTO_MIN_ELEMENTS = 1 << 18


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


def _is_torch(data):
    if data is None:
        return False
    return type(data).__module__.split('.')[0] == 'torch'


# WIDGET
class FFT_GROUP(gpi.GenericWidgetGroup):
    """A combination of SpinBoxes, DoubleSpinBoxes, and PushButtons
    to form a unique widget suitable for FFT options on dimensions.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self._val = {}
        self._val['compute'] = False
        self._val['length'] = 1
        self._val['in_len'] = 1  # the original array length
        self._val['shift'] = True  # fftshift/ifftshift around the transform

        self.pb = gpi.BasicPushButton()
        self.pb.set_toggle(True)

        self.cb = QtWidgets.QCheckBox('shift')
        self.cb.setChecked(True)
        self.cb.stateChanged.connect(self.shiftChange)

        self.db = gpi.BasicDoubleSpinBox()  # factor
        self.db.set_label('factor:')
        self.db.set_min(0.001)
        self.db.set_max(gpi.GPI_FLOAT_MAX)
        self.db.set_decimals(3)
        self.db.set_singlestep(0.001)
        self.db.set_val(1)

        self.sb = gpi.BasicSpinBox()  # length
        self.sb.set_label('length:')
        self.sb.set_min(1)
        self.sb.set_val(1)
        self.sb.set_max(gpi.GPI_INT_MAX)

        self.db.valueChanged.connect(self.factChange)
        self.sb.valueChanged.connect(self.lenChange)
        self.pb.valueChanged.connect(self.compChange)

        vbox = QtWidgets.QHBoxLayout()
        vbox.addWidget(self.pb)
        vbox.addWidget(self.db)
        vbox.addWidget(self.sb)
        vbox.addSpacing(10)
        vbox.addWidget(self.cb)
        vbox.setStretch(0, 0)
        vbox.setStretch(1, 0)
        vbox.setStretch(2, 0)
        vbox.setStretch(4, 0)
        vbox.setContentsMargins(0, 0, 0, 0)  # we don't need margins here
        vbox.setSpacing(0)
        self.setLayout(vbox)

    # setters
    def set_val(self, val):
        """A python-dict containing: in_len, length, compute, and shift
        parms. """
        sig = False
        if 'in_len' in val:
            # otherwise this would change every time compute() was called
            if self._val['in_len'] != val['in_len']:
                self._val['in_len'] = val['in_len']
                fact = self.db.get_val()  # set len based on factor
                fact *= self._val['in_len']
                self.setLenQuietly(int(fact))
                self._val['length'] = int(fact)
        if 'length' in val:
            self._val['length'] = val['length']
            self.setLenQuietly(val['length'])
            self.setFactQuietly(float(val[
                                'length'])/float(self._val['in_len']))
            sig = True
        if 'compute' in val:
            self._val['compute'] = val['compute']
            self.setCompQuietly(val['compute'])
            sig = True
        if 'shift' in val:
            self._val['shift'] = val['shift']
            self.setShiftQuietly(val['shift'])
            sig = True
        if sig:
            self.valueChanged.emit()

    def set_reset(self):
        """An override that communicates with the embedded pushbutton. """
        self.pb.set_reset()

    # getters
    def get_val(self):
        return self._val

    # support
    def factChange(self, val):
        self._val['length'] = int(self._val['in_len']*val)
        self.setLenQuietly(self._val['length'])
        self.valueChanged.emit()

    def lenChange(self, val):
        self._val['length'] = val
        self.setFactQuietly(float(val)/float(self._val['in_len']))
        self.valueChanged.emit()

    def compChange(self, val):
        self._val['compute'] = val
        self.valueChanged.emit()
        if val:
            self.pb.set_button_title('ON')
        else:
            self.pb.set_button_title('')

    def shiftChange(self, state=None):
        self._val['shift'] = self.cb.isChecked()
        self.valueChanged.emit()

    def setShiftQuietly(self, val):
        self.cb.blockSignals(True)
        self.cb.setChecked(val)
        self.cb.blockSignals(False)

    def setFactQuietly(self, val):
        self.db.blockSignals(True)
        self.db.set_val(val)
        self.db.blockSignals(False)

    def setLenQuietly(self, val):
        self.sb.blockSignals(True)
        self.sb.set_val(val)
        self.sb.blockSignals(False)

    def setCompQuietly(self, val):
        self.pb.blockSignals(True)
        self.pb.set_val(val)
        self.pb.blockSignals(False)


class ExternalNode(gpi.NodeAPI):
    """N-dimensional FFT. Cropping and zero-padding only work on transformed
    dimensions.

    INPUT - data to be transformed, can be real or complex.  DC is assumed to
            be at index N/2 (starting at 0), for each transformed dimension.

    OUTPUT - transformed data, complex64.  DC is at index N/2 (starting at 0).

    WIDGETS:
    Dimension i - button turns off/on transform in ith dimension
                  factor and length are redundant parameters, length is the
                  output dimension size
                  factor = length/(input dimension size)
                  factors < 1 result in cropping data before transformation
                  factors > 1 result in zero-padding before transformation
                  shift - fftshift/ifftshift around the transform for this
                  dimension (enabled by default); disable if DC is already
                  centered, or already at the origin, on that axis
    direction - select whether you want a Forward or Inverse FFT
    compute - compute

    Device:
      auto - GPU when the transformed array is large enough for the
             host<->device transfer to pay off; CPU otherwise.
      cpu  - always run on the host (numpy).
      gpu  - always run on the accelerator (falls back to CPU, with a
             warning, if none is usable).
    """

    def execType(self):
        # GPI_THREAD (not GPI_PROCESS) so that all CUDA work in the app
        # shares a single context -- see the GPU convention in the repo docs.
        return gpi.GPI_THREAD

    def initUI(self):

        # Widgets
        self.dim_base_name = 'Dimension['
        self.ndim = 10
        for i in range(self.ndim):
            self.addWidget('FFT_GROUP', self.dim_base_name+str(-i-1)+']')

        self.addWidget(
            'PushButton', 'direction', button_title='FORWARD', toggle=True)
        self.addWidget('PushButton', 'compute', toggle=True, val=True)
        self.addWidget('ExclusivePushButtons', 'Device',
                       buttons=['auto', 'cpu', 'gpu'], val=0)
        self.addWidget('TextBox', 'info', val='')

        # IO Ports
        self.addInPort('in', 'NPYorTorch', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYorTorch', dtype=np.complex64)

    def validate(self):
        '''update the widget bounds based on the input data
        '''

        # only update bounds if the 'in' port changed.
        if 'in' in self.portEvents():

            # shape/ndim read the same on a numpy array and a torch tensor
            data = self.getData('in')
            if data is None:
                return 0

            # visibility and bounds
            for i in range(self.ndim):
                if i < len(data.shape):
                    val = {'in_len': data.shape[-i-1]}
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=True, val=val)
                else:
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=False)

        # only change label if the 'direction' widget changed.
        if 'direction' in self.widgetEvents():
            direction = self.getVal('direction')
            if direction:
                self.setAttr('direction', button_title="INVERSE")
            else:
                self.setAttr('direction', button_title="FORWARD")

        self.device_buttons = _device_buttons()
        self.setAttr('Device', buttons=self.device_buttons)
        if self.getVal('Device') >= len(self.device_buttons):
            self.setAttr('Device', val=0)

        return(0)

    def compute(self):

        if not self.getVal('compute'):
            return 0

        data = self.getData('in')
        if data is None:
            return 0

        direction = self.getVal('direction')
        was_torch = _is_torch(data)
        if was_torch:
            import torch
            xp = torch
        else:
            xp = np

        # crop/zero-pad + collect the axes to transform -- only dimensions
        # with their button 'on' are touched, matching the widget semantics.
        # Resizing stays in the input's own kind (and device, for torch) so a
        # GPU-resident tensor never makes an unnecessary host round trip here.
        fftAxes = ()
        shiftAxes = ()
        temp = data
        for i in range(min(self.ndim, data.ndim)):
            val = self.getVal(self.dim_base_name+str(-i-1)+']')
            if val['compute']:
                axis = -i-1
                fftAxes = fftAxes + (axis,)
                if val['shift']:
                    shiftAxes = shiftAxes + (axis,)
                temp = self._resize_axis(xp, temp, axis, val['length'])

        if not fftAxes:
            out = temp.to(xp.complex64) if was_torch else temp.astype(xp.complex64)
            self.setAttr('info', val='no dimensions selected')
            self.setData('out', out)
            return 0

        device = self._resolve_device(temp)

        try:
            if device is not None:
                import torch  # no-op re-import if already imported above
                t = temp.to(device=device) if was_torch else \
                    torch.tensor(np.ascontiguousarray(temp), device=device)
                if shiftAxes:
                    t = torch.fft.ifftshift(t, dim=shiftAxes)
                if direction:
                    t = torch.fft.ifftn(t, dim=fftAxes)
                else:
                    t = torch.fft.fftn(t, dim=fftAxes)
                if shiftAxes:
                    t = torch.fft.fftshift(t, dim=shiftAxes)
                t = t.detach().cpu()  # ports never hold device-resident data
                out = t if was_torch else t.numpy()
                backend = 'torch (' + device + ')'
            else:
                if was_torch:
                    temp = temp.detach().cpu().numpy()
                if shiftAxes:
                    temp = np.fft.ifftshift(temp, axes=shiftAxes)
                if direction:
                    temp = np.fft.ifftn(temp, axes=fftAxes)
                else:
                    temp = np.fft.fftn(temp, axes=fftAxes)
                out = np.fft.fftshift(temp, axes=shiftAxes) if shiftAxes else temp
                if was_torch:
                    out = torch.tensor(out)
                backend = 'numpy'
        except Exception as e:
            self.log.error('FFT failed: {}'.format(e))
            if 'out of memory' in str(e).lower():
                self._free_device_memory()
                self.log.error('GPU ran out of memory -- set Device to '
                                '"cpu" or use a smaller array.')
            return 1

        out = out.to(xp.complex64) if was_torch else out.astype(xp.complex64)
        self.setAttr('info', val='backend : {}\nkind    : {}\nshape   : {}'.format(
            backend, 'torch' if was_torch else 'numpy', tuple(out.shape)))
        self.setData('out', out)

        return 0

    # ---- helpers -----------------------------------------------------------

    def _resize_axis(self, xp, data, axis, new_len):
        '''Crop or zero-pad a single axis in place with the data's own kind
        (numpy or torch), keeping a torch tensor on its current device.'''
        old_len = data.shape[axis]
        diff = new_len - old_len
        if diff == 0:
            return data
        if diff < 0:
            crop = -diff
            before = (crop + 1) // 2
            after = crop // 2
            sl = [slice(None)] * data.ndim
            sl[axis] = slice(before, old_len - after if after else None)
            return data[tuple(sl)]

        before = (diff + 1) // 2
        shape = list(data.shape)
        shape[axis] = new_len
        if xp is np:
            out = np.zeros(shape, dtype=data.dtype)
        else:
            out = xp.zeros(shape, dtype=data.dtype, device=data.device)
        sl = [slice(None)] * data.ndim
        sl[axis] = slice(before, before + old_len)
        out[tuple(sl)] = data
        return out

    def _resolve_device(self, data):
        '''Return the torch device string to compute on, or None for numpy.'''
        buttons = getattr(self, 'device_buttons', ['auto', 'cpu', 'gpu'])
        choice = buttons[self.getVal('Device')]
        is_torch = _is_torch(data)
        if choice == 'cpu':
            return 'cpu' if is_torch else None

        try:
            devices = gpi.torch_devices()
        except Exception:
            devices = ['cpu']
        accel = [d for d in devices if d != 'cpu']

        if choice == 'gpu':
            if not accel:
                self.log.warn('No usable GPU found, falling back to the CPU.')
                return 'cpu' if is_torch else None
            return gpi.torch_auto_device()

        # auto
        if is_torch and data.device.type != 'cpu':
            return str(data.device)
        if not accel:
            return 'cpu' if is_torch else None
        nelem = data.numel() if is_torch else data.size
        if nelem >= _GPU_AUTO_MIN_ELEMENTS:
            return gpi.torch_auto_device()
        return 'cpu' if is_torch else None

    def _free_device_memory(self):
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
