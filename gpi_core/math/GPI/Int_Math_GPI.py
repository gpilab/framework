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


#Author: Daniel Borup
#Date: Jan2019
#Notes: Adapted from Float_Math

import numpy as np
import gpi
import math
from math import exp

class ExternalNode(gpi.NodeAPI):
    """A node to do integer math

    INPUT: input int

    OUTPUT: output float

    WIDGETS:
    For two inputs - math operations - add, subtract, multiply, divide, mod and power
    For single input - math operations - add, subtract, multiply, divide, mod, power by integer and do absolute, exponent, square root

    """

    def initUI(self):

        # Widgets
        self.inputs = 0

        self.addWidget('ExclusiveRadioButtons', 'Operation', buttons=['Add', 'Subtract','Multiply', 'Divide', 'Mod', 'Power','Absolute', 'Exponential', 'Square Root'],val=0)

        self.addWidget('SpinBox', 'Integer', val=1)
        self.addWidget('PushButton', 'compute', toggle=True, val=1)

        # IO Ports
        self.addInPort('inLeft','INT', obligation=gpi.OPTIONAL)
        self.addInPort('inRight','INT', obligation=gpi.OPTIONAL)
        self.addOutPort('out', 'INT')

        # operations

    def validate(self):
        '''update the widgets based on the input arrays
        '''

        data1 = self.getData('inLeft')
        data2 = self.getData('inRight')

        if (set(self.portEvents()).intersection(set(['inLeft','inRight'])) or
            'Mode' in self.widgetEvents()):

            if (data1 is None and data2 is None):
                self.inputs = 0
            elif (data1 is None or data2 is None):
                self.inputs = 1
            else:
                self.inputs = 2

        if self.inputs == 2:
                self.setAttr('Operation', buttons=['Add', 'Subtract','Multiply', 'Divide', 'Mod', 'Power'])

        elif self.inputs == 1:
                self.setAttr('Operation', buttons=['Add', 'Subtract','Multiply', 'Divide', 'Mod', 'Power','Absolute', 'Exponential', 'Square Root'])

        operation = self.getVal('Operation')
        if self.inputs == 1:
            self.setAttr('Integer', visible=True)
        else:
            self.setAttr('Integer', visible=False)

        if operation > 5:
            self.setAttr('Integer', visible=False)

        return(0)


    def compute(self):

        import numpy as np

        data1 = self.getData('inLeft')
        data2 = self.getData('inRight')
        operation = self.getVal('Operation')

        if self.getVal('compute'):
            if self.inputs == 1:
                if data2 is not None:
                    data1 = data2
                data2 = self.getVal('Integer')

            try:
                if self.inputs != 0:
                    if operation == 0:
                        out = data1+data2
                    if operation == 1:
                        out = data1-data2
                    if operation == 2:
                        out = data1*data2
                    if operation == 3:
                        out = data1//data2
                    if operation == 4:
                        out = data1%data2
                    if operation == 5:
                        out = data1**data2
                    if operation == 6:
                        out = abs(data1)
                    if operation == 7:
                        out = math.floor(exp(data1))
                    if operation == 8:
                        out = math.floor(math.sqrt(data1))

                    self.setData('out', out)
            except:
                return 1
        return(0)

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
