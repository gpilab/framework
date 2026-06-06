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
# Date: 2015nov13

import numpy as np
import gpi


class NonExclusivePushButtons2(gpi.NonExclusivePushButtons):
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

    # overwrite set_val
    def set_val(self, value):
        if type(value) is not list:
            value = [value]

        # remove any values that don't have a corresponding button
        names = [button.text() for button in self.buttons]
        temp = []
        for i in range(len(value)):
            if value[i] in names:
                temp.append(value[i])
        value = temp

        self._value = value
        for button_ind in range(len(self.buttons)):
            name = self.buttons[button_ind].text()
            if name in value:
                self.buttons[button_ind].setChecked(True)
            else:
                self.buttons[button_ind].setChecked(False)

    # overwrite findValue
    def findValue(self, value):
        valarr = []
        for button in self.buttons:
            if button.isChecked():
                valarr.append(button.text())
        self._value = valarr
        return


class ExternalNode(gpi.NodeAPI):
    """Flips/mirrors data along specified dimension(s)
    INPUT - input array
    OUTPUT - output array

    WIDGETS:
    """

    def initUI(self):

        # Widgets
        self.ndim = 9  # 9 for now
        self.button_labels = [str(dim) for dim in (list(range(-9,0)))]
        # self.button_labels = ['-2', '-1']
        self.addWidget('NonExclusivePushButtons2', 'Flip Dimensions:',
                       buttons=self.button_labels, val=[])

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        '''update the widgets based on the input arrays
        '''

        data = self.getData('in')
        fdims = self.getVal('Flip Dimensions:')

        # find max selected dim
        if self.portEvents() and len(fdims) > 0:
            max_fdim = max([-int(dim) for dim in fdims])
            if max_fdim > data.ndim:
                self.log.warn('Data dimensionality has changed! The selected \
flip dimensions are not supported by current data \
dimensionality.')
                return(1)

        # update dim button labels, remove buttons if only 1D
        dim_buttons = list(np.arange(-data.ndim, 0).astype('str'))
        if data.ndim > 1:
            self.setAttr('Flip Dimensions:', buttons=dim_buttons, val=fdims,
                         visible=True)
        else:
            fdims = ['-1']
            self.setAttr('Flip Dimensions:', val=fdims, visible=False)

        return(0)

    def compute(self):

        data = self.getData('in')
        fdims = self.getVal('Flip Dimensions:')

        flip_string = 'out = data['
        for i in range(-data.ndim, 0):
            if str(i) in fdims:
                flip_string = flip_string+'::-1, '
            else:
                flip_string = flip_string+':, '
        flip_string = flip_string[:-2]+']'

        g = globals()
        l = locals()
        exec(flip_string, g, l)
        out = l['out']
        self.setData('out', out)

        return(0)

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
