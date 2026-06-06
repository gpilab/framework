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


# Author: Ryan Robison
# Date: 2013mar20

import gpi
from gpi import QtWidgets

# WIDGET
class SHAPES_GROUP(gpi.GenericWidgetGroup):
    """A combination of Sliders and SpinBoxes to form a
    unique widget suitable for defining the filter shape.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self._val = {}
        self._val['size'] = 1
        self._val['width'] = 1

        self.sb = gpi.BasicSpinBox()  # size
        self.sb.set_label('size:')
        self.sb.set_min(1)
        self.sb.set_val(1)
        self.sb.set_max(gpi.GPI_INT_MAX)

        self.slb = gpi.BasicSlider()  # width
        self.slb.set_min(1)
        self.slb.set_val(1)
        self.slb.set_max(1)

        self.slider_label = QtWidgets.QLabel('width:')

        self.sb.valueChanged.connect(self.sizeChange)
        self.slb.valueChanged.connect(self.widthChange)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.slider_label)
        hbox.addWidget(self.slb)
        hbox.setStretch(0, 0)
        hbox.setSpacing(5)

        hboxGroup = QtWidgets.QHBoxLayout()
        hboxGroup.addWidget(self.sb)
        hboxGroup.addLayout(hbox)
        hboxGroup.setStretch(0, 0)
        hboxGroup.setContentsMargins(0, 0, 0, 0)  # we don't need margins here
        hboxGroup.setSpacing(30)
        self.setLayout(hboxGroup)

    # setters
    def set_val(self, val):
        """A python-dict containing: size, and width parms. """
        sig = False
        if 'size' in val:
            self._val['size'] = val['size']
            self.setSizeQuietly(val['size'])
            sig = True
        if 'width' in val:
            self._val['width'] = val['width']
            self.setWidthQuietly(val['width'])
            sig = True
        if sig:
            self.valueChanged.emit()

    # getters
    def get_val(self):
        return self._val

    # support
    def sizeChange(self, val):
        self._val['size'] = val
        self.setSizeQuietly(val)
        self.valueChanged.emit()

    def widthChange(self, val):
        self._val['width'] = val
        self.setWidthQuietly(val)
        self.valueChanged.emit()

    def setSizeQuietly(self, val):
        self.sb.blockSignals(True)
        self.sb.set_val(val)
        self.slb.set_max(val)
        self.sb.blockSignals(False)

    def setWidthQuietly(self, val):
        self.slb.blockSignals(True)
        self.slb.set_val(val)
        self.slb.blockSignals(False)

# End of WIDGET declaration


class ExternalNode(gpi.NodeAPI):
    """Geometric function generator (used to make different shapes in 1, 2, or 3 dimensions).

    INPUT:  Optional input - data are not used, but the shape of this array (ndim and array shape) are used for the output array

    OUTPUT: 1D, 2D, or 3D real-valued numpy array

    WIDGETS: (some of these parameters change in special-use cases)
    Dimensions - specify whether output data is 1D, 2D, or 3D
    Function - type of Geometric function to create
    Compute - turn off to change parameters without generating new data (turn on to generate data)
    Dimension: i - for the ith dimesion:
                   size is the length of that dimension for the output data
                   width is (usually) the width of the Geometric Function, <= size

                   Note for some Functions, only Dimension: 1 is shown even for 2D and 3D dimensions,
                      implying that the output data will have the same size/width in all dimensions

    Pass Value: Maximum value in function
    Stop Value: Value in data outside of function
    Window: allows one to taper function, creates a linear ramp between the pass and stop value.
            Window units are in %, from 0 (creating a sharp edge)
                                   to 100 (tapering from the edge to the middle of the object)

    Some Special Use Cases:
      For Sinc function, width specifies the width of the main lobe.
                         Window allows for additional tapering of the edges
      For Poly, one can specify the 0th, 1st, and 2nd order coefficients of an N-dimensional polynomial
      For Noise, one can specify the Noise standard deviation.  Everytime the module is poked, it generates a
                 new pseudo-random instance of noise
    """

    def initUI(self):
        # Widgets
        self.dim_base_name = 'Dimension['
        self.ndim = 3  # max of 3 dims for now
        self.addWidget('ExclusivePushButtons', 'Dimensions',
                       buttons=['1D', '2D', '3D'],
                       val=1)
        self.addWidget('ExclusiveRadioButtons', 'Function',
                       buttons=['Ellipse', 'Rectangle', 'Hanning',
                                'Gaussian', 'Sinc', 'Poly', 'Riesz', 'Noise'],
                       val=0)
        self.addWidget(
            'PushButton', 'Compute', button_title='OFF', toggle=True)
        self.addWidget('PushButton', 'Equal Dimensions', toggle=True, val=0)
        for i in range(self.ndim):
            self.addWidget('SHAPES_GROUP', self.dim_base_name+str(-i-1)+']')
        self.addWidget('DoubleSpinBox', 'Pass Value:', val=1.0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Stop Value:', val=0.0, decimals=5)
        self.addWidget('Slider', 'Window:', val=1.0)
        self.addWidget('DoubleSpinBox', 'Poly Const:', val=0.0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Poly i:', val=0.0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Poly i^2:', val=0.0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Poly j:', val=0.0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Poly j^2:', val=0.0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Poly k:', val=0.0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Poly k^2:', val=0.0, decimals=5)
        self.addWidget('DoubleSpinBox', 'Noise Std:', val=1.0, decimals=5)
        self.addWidget('PushButton', 'Real/Complex', toggle=True, val=0)
        self.addWidget('PushButton', 'Fixed Seed', toggle=True, val=0)
        self.addWidget('SpinBox', 'Seed', val = 0)
        
        # IO Ports
        self.addInPort('in', 'NPYarray', obligation = gpi.OPTIONAL)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        '''update the widgets based on the selected options
        '''

        # If input data is present, set size accordingly
        indat = self.getData('in')
        if indat is not None:
          #if indat.ndim not in [1,2,3]:
          #  self.log.warn('input must be 1D, 2D, or 3D')
          #  return(1)
          #self.setAttr('Dimensions',val=indat.ndim-1)
          #for i in range(indat.ndim):
          for i in range(self.getVal('Dimensions')+1):
              try:
                dval = self.getVal(self.dim_base_name+str(-i-1)+']')
                dval['size'] = indat.shape[-i-1]
                self.setAttr(self.dim_base_name+str(-i-1)+']',quietval=dval)
              except:
                pass

        # GETTING WIDGET INFO
        ndim = self.getVal('Dimensions') + 1
        function = self.getVal('Function')
        same_dim = self.getVal('Equal Dimensions')

        # visibility and bounds
        if self.widgetEvents() or self.portEvents():
            for i in range(self.ndim):
                if i < ndim and (i == 0 or not same_dim):
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=True)
                else:
                    self.setAttr(self.dim_base_name+str(-i-1)+']',
                                      visible=False)

            if function in [5, 7]:
                self.setAttr('Pass Value:', visible=False)
                self.setAttr('Stop Value:', visible=False)
            else:
                self.setAttr('Pass Value:', visible=True)
                self.setAttr('Stop Value:', visible=True)

            if function in [3, 5, 7]:
                self.setAttr('Window:', visible=False)
            else:
                self.setAttr('Window:', visible=True)

            if function == 5:
                self.setAttr('Poly Const:', visible=True)
                self.setAttr('Poly i:', visible=True)
                self.setAttr('Poly i^2:', visible=True)
                if ndim > 1:
                    self.setAttr('Poly j:', visible=True)
                    self.setAttr('Poly j^2:', visible=True)
                else:
                    self.setAttr('Poly j:', visible=False)
                    self.setAttr('Poly j^2:', visible=False)
                if ndim > 2:
                    self.setAttr('Poly k:', visible=True)
                    self.setAttr('Poly k^2:', visible=True)
                else:
                    self.setAttr('Poly k:', visible=False)
                    self.setAttr('Poly k^2:', visible=False)
            else:
                self.setAttr('Poly Const:', visible=False)
                self.setAttr('Poly i:', visible=False)
                self.setAttr('Poly i^2:', visible=False)
                self.setAttr('Poly j:', visible=False)
                self.setAttr('Poly j^2:', visible=False)
                self.setAttr('Poly k:', visible=False)
                self.setAttr('Poly k^2:', visible=False)

            if function == 7:
                self.setAttr('Noise Std:', visible=True)
                self.setAttr('Real/Complex', visible=True)
                self.setAttr('Fixed Seed', visible=True)
                if(self.getVal('Fixed Seed')):
                    self.setAttr('Seed', visible=True)
            else:
                self.setAttr('Noise Std:', visible=False)
                self.setAttr('Real/Complex', visible=False)
                self.setAttr('Fixed Seed', visible=False)
                self.setAttr('Seed', visible=False)

        return(0)

    def compute(self):

        import numpy as np

        # GETTING WIDGET INFO
        compute = self.getVal('Compute')
        function = self.getVal('Function')
        ndim = self.getVal('Dimensions') + 1
        same_dim = self.getVal('Equal Dimensions')
        complex = self.getVal('Real/Complex')
        fixedSeed = self.getVal('Fixed Seed')

        self.dims = {}
        self.widths = {}
        for i in range(self.ndim):
            if not same_dim:
                val = self.getVal(self.dim_base_name+str(-i-1)+']')
            else:
                val = self.getVal(self.dim_base_name+str(-1)+']')

            self.dims[i+1] = val['size']
            self.widths[i+1] = val['width']

        if function in [5, 7]:
            passVal = 1.0
            stopVal = 0.0
        else:
            passVal = self.getVal('Pass Value:')
            stopVal = self.getVal('Stop Value:')

        if function not in [3, 5, 7]:
            window = float(self.getVal('Window:')) / 100

        if function == 5:
            polyC = self.getVal('Poly Const:')
            polyi = self.getVal('Poly i:')
            polyi2 = self.getVal('Poly i^2:')
            polyk = 0.0
            polyk2 = 0.0
            if ndim > 1:
                polyj = self.getVal('Poly j:')
                polyj2 = self.getVal('Poly j^2:')
            else:
                polyj = 0.0
                polyj2 = 0.0
            if ndim > 2:
                polyk = self.getVal('Poly k:')
                polyk2 = self.getVal('Poly k^2:')
            else:
                polyk = 0.0
                polyk2 = 0.0

        if function == 7:
            std = self.getVal('Noise Std:')

        if function == 7 and same_dim:
            for i in range(self.ndim):
                self.dims[i + 1] = self.dims[1]

        # SETTING WIDGET INFO
        if compute:
            self.setAttr('Compute', button_title="ON")
        else:
            self.setAttr('Compute', button_title="OFF")
            
        if complex:
            self.setAttr('Real/Complex', button_title="Complex")
        else:
            self.setAttr('Real/Complex', button_title="Real")
            
        if fixedSeed:
            self.setAttr('Fixed Seed', button_title="ON")
        else:
            self.setAttr('Fixed Seed', button_title="OFF")

        # SETTING PORT INFO
        if compute:
            dim1 = self.dims[1]
            dim2 = self.dims[2]
            dim3 = self.dims[3]
            # ranges are 0 in the middle, and 1. at the index = prescribed width
            range1 = (2 * np.linspace(-(dim1 / 2), (dim1 - 1 - dim1/2), dim1) /
                      self.widths[1])
            range2 = (2 * np.linspace(-(dim2 / 2), (dim2 - 1 - dim2/2), dim2) /
                      self.widths[2])
            range3 = (2 * np.linspace(-(dim3 / 2), (dim3 - 1 - dim3/2), dim3) /
                      self.widths[3])

            # JGP for sinc function windowing
            radnorm = float(self.widths[1])/float(dim1)

            if function != 7:
                if ndim == 1:
                    cart = np.zeros([self.dims[1], 1])
                    cart[:, 0] = range1
                    radius = abs(cart[:, 0])
                    out = stopVal * np.ones(self.dims[1])
                elif ndim == 2:
                    cart = np.zeros([self.dims[2], self.dims[1], 2])
                    cart[:, :, 0] = np.tile(range1, self.dims[2])\
                                      .reshape(self.dims[2], self.dims[1])
                    cart[:, :, 1] = np.tile(range2, self.dims[1])\
                                      .reshape(self.dims[1], self.dims[2])\
                                      .transpose(1, 0)
                    radius = np.sqrt(np.square(cart[:, :, 0]) +
                                     np.square(cart[:, :, 1]))
                    out = stopVal * np.ones([self.dims[2], self.dims[1]])
                else:
                    cart = np.zeros([self.dims[3], self.dims[2],
                                     self.dims[1], 3])
                    cart[:, :, :, 0] = np.tile(range1, (self.dims[2] *
                                                        self.dims[3]))\
                                         .reshape(self.dims[3], self.dims[2],
                                                  self.dims[1])
                    cart[:, :, :, 1] = np.tile(range2, (self.dims[1] *
                                                        self.dims[3]))\
                                         .reshape(self.dims[3], self.dims[1],
                                                  self.dims[2])\
                                         .transpose(0, 2, 1)
                    cart[:, :, :, 2] = np.tile(range3, (self.dims[1] *
                                                        self.dims[2]))\
                                         .reshape(self.dims[2], self.dims[1],
                                                  self.dims[3])\
                                        .transpose(2, 0, 1)
                    radius = np.sqrt(np.square(cart[:, :, :, 0]) +
                                     np.square(cart[:, :, :, 1]) +
                                     np.square(cart[:, :, :, 2]))
                    out = stopVal * np.ones([self.dims[3], self.dims[2],
                                            self.dims[1]])
            if function == 0:  # elipse
                windIdx = radius <= 1.0
                passIdx = radius <= (1.0 - window)
                out[windIdx] = (stopVal + ((1.0 - radius[windIdx]) / window) *
                                (passVal - stopVal))
                out[passIdx] = passVal

            elif function == 1:  # rectangle
                windIdx = np.amax(abs(cart), -1) <= 1.0
                passIdx = np.amax(abs(cart), -1) <= (1.0 - window)
                out[windIdx] = (stopVal +
                                ((1.0 - np.amax(abs(cart[windIdx]), -1)) /
                                window) * (passVal - stopVal))
                out[passIdx] = passVal

            elif function == 2:  # hanning
                windIdx = radius <= 1.0
                passIdx = radius <= (1.0 - window)
                func = 0.5 * (1.0 - np.cos(np.pi * (1.0 - radius[windIdx]) /
                                           window))
                out[windIdx] = stopVal + func * (passVal - stopVal)
                out[passIdx] = passVal

            elif function == 3:  # gaussian
                func = np.exp(-np.square(radius))
                out[...] = stopVal + func * (passVal - stopVal)

            elif function == 4:  # sinc
                windIdx = radius != 0.0
                func = np.pi * radius[windIdx]
                out[windIdx] = passVal * np.sin(func) / func
                out[radius == 0.0] = passVal

                # JGP Now window sinc function
                windIdx = radnorm*radius <= 1.0
                passIdx = radnorm*radius <= (1.0 - window)
                out2 = 0.*out
                func = 0.5 * (1.0 - np.cos(np.pi * (1.0 - radnorm*radius[windIdx]) / window))
                out2[windIdx] = func
                out2[passIdx] = 1.
                out *= out2

            elif function == 5:  # poly
                if ndim == 1:
                    i = cart[:,0] * self.widths[1]
                    j = 0
                    k = 0
                elif ndim == 2:
                    i = cart[:, :, 0] * self.widths[1]
                    j = cart[:, :, 1] * self.widths[2]
                    k = 0
                else:
                    i = cart[:, :, :, 0] * self.widths[1]
                    j = cart[:, :, :, 1] * self.widths[2]
                    k = cart[:, :, :, 2] * self.widths[3]
                ifunc = 0.5 * polyi * i + 0.25 * polyi2 * np.square(i)
                jfunc = 0.5 * polyj * j + 0.25 * polyj2 * np.square(j)
                kfunc = 0.5 * polyk * k + 0.25 * polyk2 * np.square(k)
                out[...] = polyC + ifunc + jfunc + kfunc

            elif function == 6:  # riesz
                if not same_dim:
                    windIdx = np.amax(abs(cart), -1) <= 1.0
                    passIdx = np.amax(abs(cart), -1) <= (1.0 - window)
                    func = (np.amax(abs(cart[windIdx]), -1) - (1.0 - window))
                else:
                    windIdx = radius <= 1.0
                    passIdx = radius <= (1.0 - window)
                    func = radius[windIdx] - (1.0 - window)
                if window != 0.0:
                    func = np.square(func / window) * (passVal - stopVal)
                else:
                    func = 0.0
                out[windIdx] = passVal - func
                out[passIdx] = passVal

            else:  # noise
                if(fixedSeed):
                    np.random.seed(self.getVal('Seed'))
                else:
                    np.random.seed()
                if ndim == 1:
                    out = std * np.random.randn(self.dims[1])
                    if complex:
                        out = out + 1j * std * np.random.randn(self.dims[1])
                elif ndim == 2:
                    out = std * np.random.randn(self.dims[2], self.dims[1])
                    if complex:
                        out = out + 1j * std * np.random.randn(self.dims[2], 
                                                               self.dims[1])
                else:
                    out = std * np.random.randn(self.dims[3], self.dims[2],
                                                self.dims[1])
                    if complex:
                        out = out + 1j * std * np.random.randn(self.dims[3], 
                                                    self.dims[2],self.dims[1])
        else:
            out = None

        self.setData('out', out)
        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
