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


# Author: Nick Zwart
# Date: 2012dec02
# Brief: A module for reading Philips Scanner data sets.

import gpi
import numpy as np
from gpi import QtWidgets


# WIDGET
class FFTW_GROUP(gpi.GenericWidgetGroup):
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

        self.pb = gpi.BasicPushButton()
        self.pb.set_toggle(True)

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
        vbox.setStretch(0, 0)
        vbox.setStretch(1, 0)
        vbox.setStretch(2, 0)
        vbox.setContentsMargins(0, 0, 0, 0)  # we don't need margins here
        vbox.setSpacing(0)
        self.setLayout(vbox)

    # setters
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
            self.setCompQuietly(val['compute'])
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
    """A module that implements the FFTW C++ package.
    Cropping and zero-padding only work on transformed dimensions.

    INPUT - data to be transformed, can be real or complex.  DC is assumed to be at index N/2 (starting at 0)

    OUTPUT - transformed data, complex.  DC is at index N/2 (starting at 0)

    WIDGETS:
    Dimension i - button turns off/on tranform in ith dimension
                  factor and length are redundant parameters, length is the output dimension size
                  factor = length/(input dimension size)
                  factors < 1 result in cropping data before transformation
                  factors > 1 result in zero-padding before transformation
    compute - compute
    direction - select whether you want a Forward or Inverse FFT
    """

    def execType(self):
        # default executable type
        # return GPI_THREAD
        return gpi.GPI_PROCESS
        # return GPI_APPLOOP

    def initUI(self):

        # Widgets
        self.dim_base_name = 'Dimension['
        self.ndim = 10  # underlying c-code is only 10-dim
        for i in range(self.ndim):
            self.addWidget('FFTW_GROUP', self.dim_base_name+str(-i-1)+']')

        self.addWidget('PushButton', 'inverse', toggle=True)
        self.addWidget('PushButton', 'compute', toggle=True)

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray', dtype=np.complex64)

    def validate(self):
        '''update the widget bounds based on the input data
        '''

        # only update bounds if the 'in' port changed.
        if 'in' in self.portEvents():

            data = self.getData('in')

            # visibility and bounds
            for i in range(self.ndim):
                if i < len(data.shape):
                    val = {'in_len': data.shape[-i-1]}
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=True, val=val)
                else:
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=False)

        # only change bounds if the 'direction' widget changed.
        if 'direction' in self.widgetEvents():
            direction = self.getVal('direction')
            if direction:
                self.setAttr('direction', button_title="INVERSE")
            else:
                self.setAttr('direction', button_title="FORWARD")

        return(0)

    def compute(self):

        data = self.getData('in')
        data = np.require(data, dtype=np.complex64, requirements='C')

        if self.getVal('compute'):

            # build the fft.fft argument list
            kwargs = {}

            # Direction | 0:FWD, 1:BKWD
            if self.getVal('inverse'):
                kwargs['dir'] = 1
            else:
                kwargs['dir'] = 0

            out_dims = np.array([], np.int64)

            # load up the dimension args
            for i in range(self.ndim):
                kwargs['dim'+str(i+1)] = 0
                val = self.getVal(self.dim_base_name+str(-i-1)+']')
                if i < len(data.shape):
                    out_dims = np.append(out_dims, val['length'])
                    if val['compute']:
                        kwargs['dim'+str(i+1)] = 1


            # import in thread to save namespace
            import gpi_core.math.fft as ft

            out = ft.fftw(data, out_dims, **kwargs)

            self.setData('out', out)

        return(0)
