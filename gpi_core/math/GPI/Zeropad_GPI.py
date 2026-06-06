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


# Author: Payal Bhavsar
# Date: Dec2013
# built of Ryan Robison's FFT code

import gpi
from gpi import QtWidgets


# WIDGET (code from FFTW_GPI.py)
class FFTW_GROUP(gpi.GenericWidgetGroup):

    """A combination of SpinBoxes, DoubleSpinBoxes, and PushButtons
    to form a unique widget suitable for FFT options on dimensions.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self._val = {}
        self._val['length'] = 1
        self._val['in_len'] = 1  # the original array length

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

        vbox = QtWidgets.QHBoxLayout()
        vbox.addWidget(self.db)
        vbox.addWidget(self.sb)
        vbox.setStretch(0, 0)
        vbox.setStretch(1, 0)
        vbox.setStretch(2, 0)
        vbox.setContentsMargins(0, 0, 0, 0)  # we don't need margins here
        vbox.setSpacing(0)
        self.setLayout(vbox)

    # setters
    def set_val(self, val):
        """A python-dict containing: in_len and length parms. """
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
            self.setFactQuietly(
                float(val['length']) / float(self._val['in_len']))
            sig = True
        if sig:
            self.valueChanged.emit()

    # getters
    def get_val(self):
        return self._val

    # support
    def factChange(self, val):
        self._val['length'] = int(self._val['in_len'] * val)
        self.setLenQuietly(self._val['length'])
        self.valueChanged.emit()

    def lenChange(self, val):
        self._val['length'] = val
        self.setFactQuietly(float(val) / float(self._val['in_len']))
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

    """Fast Fourier Transformation of N-dimensional data via scipy library.


    INPUT - data to be zeropadded or sinc-interpolated, can be real or complex.  DC is assumed to be at index N/2 (starting at 0)

    OUTPUT - Return Sinc interpolated data - zero-padding or cropping is applied in the transform domain.

    WIDGETS:
    Dimension i - button turns off/on tranform in ith dimension
                  factor and length are redundant parameters, length is the output dimension size
                  factor = length/(input dimension size)
                  factors < 1 result in cropping data before transformation
                  factors > 1 result in zero-padding before transformation

    compute - return sinc interpolated data after FFT forward the input data -> zero-pad -> FFT backward

    """

    def initUI(self):

        # Widgets
        self.dim_base_name = 'Dimension['
        self.ndim = 9  # limit to 9 for now
        for i in range(self.ndim):
            self.addWidget('FFTW_GROUP', self.dim_base_name +
                           str(-i - 1) + ']')

        self.addWidget('ExclusivePushButtons','Domain', buttons=['Transform','Image'],val=0)
        self.addWidget('PushButton', 'compute', toggle=True)

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        '''update the widget bounds based on the input data
        '''

        # only update bounds if the 'in' port changed.
        if 'in' in self.portEvents():

            data = self.getData('in')

            # visibility and bounds
            for i in range(self.ndim):
                if i < len(data.shape):
                    val = {'in_len': data.shape[-i - 1]}
                    self.setAttr(self.dim_base_name + str(-i - 1) + ']',
                                 visible=True, val=val)
                else:
                    self.setAttr(self.dim_base_name + str(-i - 1) + ']',
                                 visible=False)

        # only change label if the 'direction' widget changed.

        return(0)

    def compute(self):

        import numpy as np

        data = self.getData('in')

        if self.getVal('compute'):

            fftAxes = ()
            ifftAxes = ()

            intype = data.dtype

            temp = data

            for i in range(data.ndim):
                val = self.getVal(self.dim_base_name + str(-i - 1) + ']')

                if val['length'] != val['in_len']:
                    fftAxes = (-i - 1,)
                    ifftAxes = ifftAxes + (-i - 1,)

                    if self.getVal('Domain') == 0:
                        temp = np.fft.fftshift(np.fft.ifftn(np.fft.ifftshift(temp),
                                                        axes=fftAxes))

                    zpad_length = val['length'] - temp.shape[-i - 1]
                    if zpad_length >= 0:
                        zpad_before = int(zpad_length / 2.0 + 0.5)
                        zpad_after = int(zpad_length / 2.0)
                    else:
                        zpad_before = int(zpad_length / 2.0 - 0.5)
                        zpad_after = int(zpad_length / 2.0)
                    if zpad_after > 0:
                        temp = np.insert(temp, temp.shape[-i - 1] *
                                         np.ones(zpad_after, dtype=int), 0.0, (-i - 1))
                    elif zpad_after < 0:
                        temp = np.delete(temp, list(range(temp.shape[-i - 1] +
                                         zpad_after, temp.shape[-i - 1])), (-i - 1))
                    if zpad_before > 0:
                        temp = np.insert(temp, np.zeros(zpad_before, dtype=int), 0.0,
                                         (-i - 1))
                    elif zpad_before < 0:
                        temp = np.delete(temp, list(range(-zpad_before)), (-i - 1))

            if self.getVal('Domain') == 0:
                out = np.fft.fftshift(np.fft.fftn(np.fft.ifftshift(temp),
                                              axes=ifftAxes))
            else:
                out = temp
            self.setData('out', out)

        else:

            self.setData('out', data)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
