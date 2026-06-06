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


#Author: Jim Pipe
#Date: 2014Mar

import gpi
import numpy as np
from scipy import interpolate
from gpi import QtWidgets


class Interpolate_GROUP(gpi.GenericWidgetGroup):
    """A combination of SpinBoxes, DoubleSpinBoxes, and PushButtons
    to form a unique widget suitable for interpolation options on dimensions.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        # Widgets
        self._val = {}
        self._val['length'] = 1
        self._val['in_len'] = 1  # the original array length

        self.db = gpi.BasicDoubleSpinBox()  # factor
        self.db.set_label('factor:')
        self.db.set_min(0.001)
        self.db.set_max(gpi.GPI_FLOAT_MAX)
        self.db.set_decimals(8)
        self.db.set_singlestep(0.1)
        self.db.set_val(1)

        self.sb = gpi.BasicSpinBox()  # length
        self.sb.set_label('length:')
        self.sb.set_min(1)
        self.sb.set_val(1)
        self.sb.set_max(gpi.GPI_INT_MAX)

        self.db.valueChanged.connect(self.factChange)
        self.sb.valueChanged.connect(self.lenChange)

        vbox = QtWidgets.QHBoxLayout()
        vbox.addWidget(self.db)
        vbox.addWidget(self.sb)
        vbox.setStretch(0, 0)
        vbox.setStretch(1, 0)
        vbox.setStretch(2, 0)
        vbox.setContentsMargins(0, 0, 0, 0)  # we don't need margins here
        vbox.setSpacing(0)
        self.setLayout(vbox)

    def set_val(self, val):
        """A python-dict containing: in_len, length, and compute parms. """
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
            sig = True
        if sig:
            self.valueChanged.emit()

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

    def setFactQuietly(self, val):
        self.db.blockSignals(True)
        self.db.set_val(val)
        self.db.blockSignals(False)

    def setLenQuietly(self, val):
        self.sb.blockSignals(True)
        self.sb.set_val(val)
        self.sb.blockSignals(False)

class ExternalNode(gpi.NodeAPI):
    """A node to linearly interpolate in specified directions.

    INPUT: input numpy array

    OUTPUT: interpolated data in the specified directions.

    WIDGETS:
    Dimension[n]:  For each dimension,
      factor - (desired output length)/(input length)
      length - desired output length
    kind - what type or order of interpolation to apply.
        'slinear', 'quadratic', and 'cubic' are all spline interpolations
        'sinc' interpolation uses zero-padding and FFTW
    Compute - compute
    """


    def initUI(self):

        # Widgets
        self.dim_base_name = 'Dimension['
        self.ndim = 6  # underlying c-code is only 6-dim
        for i in range(self.ndim):
            self.addWidget('Interpolate_GROUP', self.dim_base_name+str(i)+']')
        interp_modes =  ('linear', 'nearest', 'zero', 'slinear', 'quadratic', 'cubic', 'sinc')
        self.addWidget('ComboBox', 'interpolation-mode', items=interp_modes, val='slinear')
        windows =  ('none', 'hann', 'hamming', 'blackman', 'lanczos', 'tukey')
        self.addWidget('ComboBox', 'window', items=windows, val='lanczos', visible=False)
        self.addWidget('DoubleSpinBox', 'alpha', min=0.0, max=1.0, val=0.5, visible=False)
        self.addWidget('PushButton', 'compute', toggle=True)

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addInPort('size', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        if 'in' in self.portEvents() or 'size' in self.portEvents():
            data = self.getData('in')
            out_shape = self.getData('size')

            # visibility and bounds
            for i in range(self.ndim):
                if i < len(data.shape):
                    val = {'in_len': data.shape[i]}

                    # assign output lengths based on optional input array
                    if out_shape is not None:
                        offset = len(data.shape)-len(out_shape.shape)
                        if offset < 0:
                            if i < len(out_shape.shape):
                                val['length'] = out_shape.shape[i-offset]
                        else:
                            if i >= offset:
                                val['length'] = out_shape.shape[i-offset]

                    self.setAttr(self.dim_base_name+str(i)+']', visible=True, quietval=val)
                else:
                    self.setAttr(self.dim_base_name+str(i)+']',visible=False)

        if self.getVal('interpolation-mode') == 'sinc':
            self.setAttr('window', visible=True)
            if self.getVal('window') == 'tukey':
                self.setAttr('alpha', visible=True)
            else:
                self.setAttr('alpha', visible=False)
        else:
            self.setAttr('window', visible=False)
            self.setAttr('alpha', visible=False)

        return(0)

    def compute(self):
        data_in = self.getData('in')
        kind = self.getVal('interpolation-mode')

        self.dimm = data_in.shape
        self.ndim = data_in.ndim

        data_out = data_in.copy()
        if self.getVal('compute'):
            if kind in ('linear', 'nearest'):
                for i in range(self.ndim):
                    val = self.getVal(self.dim_base_name+str(i)+']')
                    interpnew = val['length']
                    axisnew = self.dimm[i]
                    x = np.linspace(0, axisnew-1, axisnew)
                    xnew = np.linspace(0, axisnew-1, interpnew)
                    if axisnew == 1:
                        reps = np.ones((self.ndim,))
                        reps[i] = interpnew
                        ynew = np.tile(data_out, reps)
                    elif axisnew == interpnew:
                        continue
                    else:
                        yinterp = interpolate.interp1d(x, data_out,
                                                       kind=kind, axis=i)
                        ynew = yinterp(xnew)

                    data_out = ynew
            elif kind in ('zero', 'slinear', 'quadratic', 'cubic'):
                from scipy.ndimage.interpolation import map_coordinates
                orders = {'zero': 0, 'slinear': 1, 'quadratic': 2, 'cubic': 3}
                o = orders[kind]

                # if the data is complex, interp real and imaginary separately
                if data_in.dtype in (np.complex64, np.complex128):
                    data_real = np.real(data_in)
                    data_imag = np.imag(data_in)
                else:
                    data_real = data_in
                    data_imag = None

                new_dims = []
                for i in range(self.ndim):
                    val = self.getVal(self.dim_base_name + str(i) + ']')
                    new_dims.append(np.linspace(0, val['in_len']-1, val['length']))

                coords = np.meshgrid(*new_dims, indexing='ij')
                data_out = map_coordinates(data_real, coords, order=o)

                if data_imag is not None:
                    data_out = (data_out +
                                1j*map_coordinates(data_imag, coords, order=o))

            else:
                # use zero-padding and FFTW to sinc-interpolate
                import gpi_core.math.fft as ft
                data_in_c64 = np.require(data_in,
                                         dtype=np.complex64, requirements='C')

                old_dims = np.asarray(self.dimm[::-1], dtype=np.int64)
                new_dims = old_dims.copy()
                fftargs = {}
                win = np.ones(data_in.shape)
                scale = 1
                for i in range(self.ndim):
                    val = self.getVal(self.dim_base_name + str(i) + ']')
                    new_dims[self.ndim-i-1] = np.int64(val['length'])
                    if val['length'] == val['in_len']:
                        fftargs['dim{}'.format(self.ndim-i)] = 0
                    else:
                        win *= self.window(i)
                        fftargs['dim{}'.format(self.ndim-i)] = 1
                        scale *= val['length'] / val['in_len']

                # forward FFT with original dimensions
                fftargs['dir'] = 0
                data_out = ft.fftw(data_in_c64, old_dims, **fftargs)

                data_out *= win.astype(np.complex64)
                # inverse FFT with new dimensions (zero-pad kspace)
                fftargs['dir'] = 1
                data_out = ft.fftw(data_out, new_dims, **fftargs)

                if data_in.dtype in (np.float32, np.float64):
                    data_out = np.real(data_out)

                # data needs to be scaled since we changed the size between the
                # forward and inverse FT
                data_out *= scale

            self.setData('out', data_out)
        else:
            pass

        return(0)


    def execType(self):
        return gpi.GPI_PROCESS

    def window(self, axis):
        kind = self.getVal('window')
        N = self.dimm[axis]

        win = np.ones(N) # kind = 'none' is a rectangular window

        if kind == 'hann':
            win = np.hanning(N)
        elif kind == 'hamming':
            win = np.hamming(N)
        elif kind == 'blackman':
            win = np.blackman(N)
        elif kind == 'lanczos':
            n = np.arange(N)
            win = np.sinc(2. * np.arange(N) / (N - 1) - 1)
        elif kind == 'tukey':
            a = self.getVal('alpha')
            if a != 0.0:
                l_edge = a * (N - 1) // 2
                r_edge = round((N - 1) * (1 - a / 2))
                n = np.arange(N)
                win[0:l_edge] = 0.5*(1 +
                                np.cos(np.pi * (2*n[0:l_edge] / a / (N - 1) - 1)))
                win[l_edge:r_edge] = 1
                win[r_edge::] = 0.5*(1 +
                                np.cos(np.pi * (2*n[r_edge::] / a / (N - 1)  - 2/a + 1)))

        for ax in range(self.ndim):
            if ax < axis:
                win = win[np.newaxis, ...]
            elif ax > axis:
                win = win[..., np.newaxis]

        return win



