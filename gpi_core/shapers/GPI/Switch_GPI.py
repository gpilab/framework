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


class ExternalNode(gpi.NodeAPI):
    """Perform real or complex scalar operations on a per element basis.
       Three Modes of Operation:
        1) Standard - basic Arithmetic and exponential operations.
        2) Trigonometric - basic Trigonometric operations.
        3) Comparison - returns maximum, minimum, or bit mask based on
                        comparison between inputs or against Scalar.

       Operations which do not commute (e.g. divide) operate left to right, e.g.:
         output = (left port) / (right port)
    """

    def initUI(self):
        # operations
        self.button_labels = ['Left','Right']

        # Widgets
        self.choice = 0
        self.addWidget('ExclusivePushButtons', 'Choice',
                            buttons=self.button_labels, val = 0, visible = False)
        # IO Ports
        self.addInPort('inLeft', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addInPort('inRight', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        '''update the widgets based on the input arrays
        '''

        data1 = self.getData('inLeft')
        data2 = self.getData('inRight')

        if (set(self.portEvents()).intersection(set(['inLeft','inRight'])) or
            'Choice' in self.widgetEvents()):
            if (data1 is None and data2 is None):
                self.setAttr('Choice', visible = False)
                self.setDetailLabel('No Data')
            else:
                if data2 is None:
                    self.setAttr('Choice', visible = False)
                    self.setAttr('Choice', val=0)
                elif data1 is None:
                    self.setAttr('Choice', visible = False)
                    self.setAttr('Choice', val=1)
                else:
                    self.setAttr('Choice', visible = True)
                    if data1.shape != data2.shape:
                        self.log.warn('Array Sizes Unequal')
                self.choice = self.getVal('Choice')
                self.setDetailLabel(format(self.button_labels[self.choice]))

        return 0

    def compute(self):

        import numpy as np

        data1 = self.getData('inLeft')
        data2 = self.getData('inRight')
        self.choice = self.getVal('Choice')
        try:
            if self.choice == 0:
                self.setData('out', data1)
            else:
                self.setData('out', data2)
        except:
            return 1

        return(0)

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_THREAD
