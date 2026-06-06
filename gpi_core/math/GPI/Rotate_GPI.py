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
# Date: 2013Dec
# Mods: Jim Pipe, 2013 Dec

import numpy as np
import gpi
import math
import scipy.ndimage as scnd

class ExternalNode(gpi.NodeAPI):

    """A node to rotate data about a plane specified by two axes

    INPUT: input numpy array

    OUTPUT: output numpy array

    WIDGETS:
    Theta is entered in degrees
    Output can be reshaped to contain the input after rotation
    Modes of rotation - constant, nearest, reflect and wrap can be chosen
    Order for interpolation can be specified.

    """

    def initUI(self):
        self.addInPort('in', 'NPYarray')
        self.addOutPort('out', 'NPYarray')

        self.addWidget('DoubleSpinBox', 'Theta', val=0.0, decimals = 5)
        self.addWidget('ExclusivePushButtons', 'Units', buttons=['Deg','Rad','Cyc'], val = 0)
        self.dim_buttons = ['[0-1]', '[0-2]', '[0-3]', '[0-4]', '[0-5]', '[1-2]', '[1-3]', '[1-4]', '[1-5]', '[2-3]','[2-4]','[2-5]','[3-4]','[3-5]','[4-5]']
        self.addWidget('ExclusivePushButtons', 'Plane of Rotation:', buttons=self.dim_buttons, val=0)
        self.addWidget('PushButton', 'Reshape', toggle=True, val=0, collapsed = True)
        self.op_buttons_1 = ['constant','nearest','reflect','wrap']
        self.addWidget('ExclusiveRadioButtons','Mode', buttons=self.op_buttons_1, val=0, collapsed = True)
        self.addWidget('Slider', 'Order', val = 1, min=0, max=5, collapsed = True)

    def validate(self):
        data = self.getData('in')
        self.setAttr('Theta', max=1000., min=-1000.0)
        ddim = (data.ndim)

        if ('in' in self.portEvents()):
          if ddim == 2 or self.getVal('Plane of Rotation:') > ddim-2:
            self.setAttr('Plane of Rotation:', buttons=self.dim_buttons, val=0)
        if ddim == 2:
          self.dim_buttons = ['[0-1]']
        if ddim == 3:
          self.dim_buttons = ['[0-1]','[1-2]','[0-2]']
        if ddim == 4:
          self.dim_buttons = ['[0-1]','[1-2]', '[0-2]', '[1-3]', '[2-3]', '[0-3]']
        if ddim == 5:
          self.dim_buttons = ['[0-1]', '[1-2]', '[0-2]', '[1-3]', '[2-3]', '[0-3]','[0-4]', '[1-4]', '[2-4]', '[3-4]']
        op = self.getVal('Plane of Rotation:')
        self.setAttr('Plane of Rotation:', buttons=self.dim_buttons, val=op)

        return(0)

    def compute(self):
        import numpy as np

        units = self.getVal('Units')
        if units == 0: # degrees
            unitConv = 1
        elif units == 1: # radians
            unitConv = 180/np.pi
        else: # cycles
            unitConv = 360

        data = self.getData('in')
        Theta = self.getVal('Theta') * unitConv
        valueorder = self.getVal('Order')
        value = self.getVal('Reshape')
        self.shape = list(data.shape)
        op = self.getVal('Plane of Rotation:')
        mode_val = self.getVal('Mode')


        if op == 0:
            ax0 = 0
            ax1 = 1

        if op == 1:
            ax0 = 1
            ax1 = 2

        if op == 2:
            ax0 = 0
            ax1 = 2

        if op == 3:
            ax0 = 1
            ax1 = 3

        if op == 4:
            ax0 = 2
            ax1 = 3

        if op == 5:
            ax0 = 0
            ax1 = 3

        if op == 6:
            ax0 = 0
            ax1 = 4

        if op == 7:
            ax0 = 1
            ax1 = 4

        if op == 8:
            ax0 = 2
            ax1 = 4

        if op == 9:
            ax0 = 3
            ax1 = 4

        if np.iscomplexobj(data):
          if mode_val == 0:
            RD = scnd.rotate(data.real,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='constant')
            ID = scnd.rotate(data.imag,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='constant')
          elif mode_val == 1:
            RD = scnd.rotate(data.real,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='nearest')
            ID = scnd.rotate(data.imag,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='nearest')
          elif mode_val == 2:
            RD = scnd.rotate(data.real,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='reflect')
            ID = scnd.rotate(data.imag,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='reflect')
          elif mode_val == 3:
            RD = scnd.rotate(data.real,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='wrap')
            ID = scnd.rotate(data.imag,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='wrap')
          out = RD + 1j*ID
        else:
          if mode_val == 0:
            out = scnd.rotate(data,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='constant')
          elif mode_val == 1:
            out = scnd.rotate(data,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='nearest')
          elif mode_val == 2:
            out = scnd.rotate(data,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='reflect')
          elif mode_val == 3:
            out = scnd.rotate(data,Theta,(ax0,ax1), reshape=value, order = valueorder, mode='wrap')

        self.setData('out', out.astype(data.dtype))

        return(0)
