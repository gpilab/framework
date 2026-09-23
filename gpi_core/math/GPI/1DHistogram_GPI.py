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


# Author: Sudarshan Ragunathan
# Date: 2014may28

import contextlib
import numpy as np
import gpi
from gpi import QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvas

# Below this many elements the host<->device round trip costs more than the
# histogram op saves, so 'auto' stays on the CPU.
_GPU_AUTO_MIN_ELEMENTS = 1 << 20


class HistogramPlot(gpi.GenericWidgetGroup):
    """Embeds a small matplotlib bar-plot of the histogram values/bins."""
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self._val = None
        self._fig = Figure(figsize=(4, 2.5), facecolor='#353535')
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setMinimumHeight(200)
        self._ax = self._fig.add_subplot(111)
        self._style_axes()
        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self._canvas)
        self.setLayout(vbox)

    def _style_axes(self):
        ax = self._ax
        ax.set_facecolor('#1e1e1e')
        for spine in ax.spines.values():
            spine.set_color('#555555')
        ax.tick_params(colors='#aaaaaa')
        ax.xaxis.label.set_color('#dcdcdc')
        ax.yaxis.label.set_color('#dcdcdc')

    def set_val(self, val):
        """(hist_val, hist_bin) | Draw the histogram as a bar plot."""
        self._val = val
        if val is None:
            return
        hist_val, hist_bin = val
        hist_val = np.asarray(hist_val)
        hist_bin = np.asarray(hist_bin)
        self._ax.clear()
        self._style_axes()
        if hist_val.size and hist_bin.size >= 2:
            centers = (hist_bin[:-1] + hist_bin[1:]) / 2.0
            width = hist_bin[1] - hist_bin[0]
            self._ax.bar(centers, hist_val, width=width, color='#5599ff', edgecolor='none')
        self._ax.set_xlabel('Value')
        self._ax.set_ylabel('Count')
        self._fig.tight_layout()
        self._canvas.draw_idle()

    def get_val(self):
        return self._val


def _device_buttons():
    '''auto/gpu are omitted entirely (not just disabled) when no accelerator
    is enabled/available.'''
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


def _decimals_for(value):
    """QDoubleSpinBox.setValue() rounds to its 'decimals' precision, so sub-unity
    magnitudes need more than the default 2 or distinct bounds can collapse to
    the same rounded value."""
    mag = abs(value)
    if mag == 0 or mag >= 1:
        return 2
    return min(12, int(np.ceil(-np.log10(mag))) + 3)


class ExternalNode(gpi.NodeAPI):
    """Performs a 1D-histogram of the non-zero values in an array.

    INPUT - NumPy array or PyTorch tensor (data type : int, float or complex)

    OUTPUT:
    HistVal - Values in each histogram bin
    HistBin - Vector of bin edges

    WIDGETS:
    R I M - Choose from Real, Imaginary or Magnitude data (Visible for complex input)
    Bins - Number of bins
    Range - Lower and Upper range of the bins. The user has the option of specifying
            the range or using the max and min of the input
    Device - auto/cpu/gpu, only offered when an accelerator is available
    """

    def initUI(self):

        # Widgets
        self.addWidget('ExclusivePushButtons', 'R I M', buttons=['R', 'I', 'M'], val=2)
        self.addWidget('DoubleSpinBox', '# Bins', val=500)
        self.addWidget('DoubleSpinBox', 'Lower Bound', val=0.)
        self.addWidget('DoubleSpinBox', 'Upper Bound', val=255.)
        self.bin_op = ['Set Range','Use Min/Max']
        self.addWidget('ExclusiveRadioButtons', 'Bin Range', buttons=self.bin_op, val=0)
        self.addWidget('ExclusivePushButtons', 'Device', buttons=['auto', 'cpu', 'gpu'], val=0)
        self.addWidget('HistogramPlot', 'Histogram Plot')

        # IO Ports
        self.addInPort('Data In', 'NPYorTorch', obligation=gpi.REQUIRED)
        self.addOutPort('HistVal', 'NPYorTorch')
        self.addOutPort('HistBin', 'NPYorTorch')

    def _select_component(self, data, is_torch, is_complex):
        '''Reduce complex data to the selected R/I/M component; leave
        real/int data untouched regardless of the R I M selection.'''
        if not is_complex:
            return data
        op = self.getVal('R I M')
        if is_torch:
            if op == 0:
                return data.real
            elif op == 1:
                return data.imag
            return data.abs()
        if op == 0:
            return np.real(data)
        elif op == 1:
            return np.imag(data)
        return np.abs(data)

    def _resolve_device(self, data):
        buttons = getattr(self, 'device_buttons', ['auto', 'cpu', 'gpu'])
        choice = buttons[self.getVal('Device')]
        if choice == 'cpu':
            return 'cpu' if _is_torch(data) else None

        try:
            devices = gpi.torch_devices()
        except Exception:
            devices = ['cpu']
        accel = [d for d in devices if d != 'cpu']

        if choice == 'gpu':
            if not accel:
                self.log.warn('No usable GPU found, falling back to the CPU.')
                return 'cpu' if _is_torch(data) else None
            return gpi.torch_auto_device()

        # auto
        if not accel:
            return 'cpu' if _is_torch(data) else None
        if _is_torch(data) and data.device.type != 'cpu':
            return str(data.device)
        nelem = data.size if isinstance(data, np.ndarray) else data.numel()
        if nelem >= _GPU_AUTO_MIN_ELEMENTS:
            return gpi.torch_auto_device()
        return 'cpu' if _is_torch(data) else None

    def _as_torch(self, data, device):
        import torch
        if _is_torch(data):
            return data.to(device=device)
        return torch.tensor(np.ascontiguousarray(data), device=device)

    def validate(self):
        im_input = self.getData('Data In')

        is_torch = _is_torch(im_input)
        is_complex = 'complex' in str(im_input.dtype)
        self.setAttr('R I M', visible=is_complex)

        data_in = self._select_component(im_input, is_torch, is_complex)
        nz = data_in[data_in != 0] if is_torch else data_in[np.nonzero(data_in)]
        nz_empty = (nz.numel() if is_torch else nz.size) == 0
        if nz_empty:
            data_min, data_max = 0., 1.
        else:
            data_min = float(nz.min()) if is_torch else float(np.amin(nz))
            data_max = float(nz.max()) if is_torch else float(np.amax(nz))
            if data_min == data_max:
                # constant nonzero data (e.g. a mask) - widen so Upper > Lower
                pad = abs(data_min) * 1e-3 if data_min != 0 else 1.
                data_min -= pad
                data_max += pad

        decimals = max(_decimals_for(data_min), _decimals_for(data_max))

        bin_range = self.getVal('Bin Range')
        if bin_range == 1:
            self.setAttr('Lower Bound', visible=False)
            self.setAttr('Upper Bound', visible=False)
            self.setAttr('Lower Bound', decimals=decimals)
            self.setAttr('Upper Bound', decimals=decimals)
            self.setAttr('Lower Bound', val=data_min)
            self.setAttr('Upper Bound', val=data_max)
        else:
            self.setAttr('Lower Bound', visible=True)
            self.setAttr('Upper Bound', visible=True)

        # Check for Lower >= Upper Bound (decimals rounding can also collapse them)
        lbound = self.getVal('Lower Bound')
        ubound = self.getVal('Upper Bound')
        if lbound >= ubound:
            fix_decimals = max(_decimals_for(lbound), _decimals_for(ubound), decimals)
            self.setAttr('Lower Bound', decimals=fix_decimals)
            self.setAttr('Upper Bound', decimals=fix_decimals)
            self.setAttr('Lower Bound', val=lbound)
            self.setAttr('Upper Bound', val=lbound + 1.)

        self.device_buttons = _device_buttons()
        self.setAttr('Device', buttons=self.device_buttons)
        if self.getVal('Device') >= len(self.device_buttons):
            self.setAttr('Device', val=0)

        return(0)

    def compute(self):
        im_input = self.getData('Data In')
        if im_input is None:
            return 0

        is_torch_in = _is_torch(im_input)
        is_complex = 'complex' in str(im_input.dtype)

        bins = int(self.getVal('# Bins'))
        lbound = self.getVal('Lower Bound')
        ubound = self.getVal('Upper Bound')
        if bins < 1:
            self.log.warn('# Bins must be >= 1.')
            return 1
        if ubound <= lbound:
            self.log.warn('Upper Bound must be greater than Lower Bound.')
            return 1

        device = self._resolve_device(im_input)
        use_torch = device is not None
        needs_gpu_lock = use_torch and device != 'cpu'

        try:
            with (gpi.gpu_exclusive() if needs_gpu_lock else contextlib.nullcontext()):
                if use_torch:
                    import torch
                    data = self._as_torch(im_input, device)
                    data = self._select_component(data, True, is_complex)
                    data = data[data != 0].float()
                    if data.numel() == 0:
                        hist_val = torch.zeros(bins, device=device)
                    else:
                        hist_val = torch.histc(data, bins=bins, min=lbound, max=ubound)
                    hist_bin = torch.linspace(lbound, ubound, bins + 1, device=device)
                    if is_torch_in:
                        hist_val = hist_val.cpu()
                        hist_bin = hist_bin.cpu()
                    else:
                        hist_val = hist_val.cpu().numpy()
                        hist_bin = hist_bin.cpu().numpy()
                else:
                    data = self._select_component(im_input, False, is_complex)
                    data = data[np.nonzero(data)]
                    hist_val, hist_bin = np.histogram(data, bins, range=(lbound, ubound))
        except Exception as e:
            self.log.error('Histogram failed: {}'.format(e))
            return 1

        self.setData('HistVal', hist_val)
        self.setData('HistBin', hist_bin)

        plot_val = hist_val.numpy() if _is_torch(hist_val) else hist_val
        plot_bin = hist_bin.numpy() if _is_torch(hist_bin) else hist_bin
        self.setAttr('Histogram Plot', val=(plot_val, plot_bin))
        return(0)

    def execType(self):
        # GPI_THREAD (not GPI_PROCESS) so that all CUDA work in the app
        # shares a single context -- see the GPU convention in the repo docs.
        return gpi.GPI_THREAD




