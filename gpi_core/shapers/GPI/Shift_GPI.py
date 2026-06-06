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

class ExternalNode(gpi.NodeAPI):
    """Shifts data along each dimension by user specified amount.
    Shift can be linear or circular.
    INPUT - input array
    OUTPUT - output array

    WIDGETS:
    """

    def initUI(self):

        # Widgets
        self.dim_base_name = 'Dimension['
        self.ndim = 13  # 13 for now
        self.addWidget('ExclusivePushButtons', 'Type', 
                buttons=['Linear', 'Circular'], val=0)
        for i in range(self.ndim):
            self.addWidget('SpinBox', self.dim_base_name+str(-i-1)+']', val=0)

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        '''update the widgets based on the input arrays
        '''

        data = self.getData('in')

        # visibility and bounds
        for i in range(self.ndim):
            if i < len(data.shape):
                shift = self.getVal(self.dim_base_name+str(-i-1)+']')
                self.setAttr(self.dim_base_name+str(-i-1)+']',
                        visible=True, val=shift)
            else:
                self.setAttr(self.dim_base_name+str(-i-1)+']',
                        visible=False)

        return(0)

    def compute(self):

        data = self.getData('in')
        out = data
        stype = self.getVal('Type')

        for i in range(data.ndim):
            shift = self.getVal(self.dim_base_name+str(-i-1)+']')

            if stype == 0:
                if shift <= 0:
                    shift = max(0, -shift)
                    del_range = list(range(shift))
                    insert_vals = [data.shape[-i-1]] * shift
                    out = np.insert(out, insert_vals, 0, axis = -i-1)
                    out = np.delete(out, del_range, axis = -i-1)
                else:
                    shift = min(shift, data.shape[-i-1])
                    insert_vals = [0] * shift
                    del_range = list(range(data.shape[-i-1] - shift,
                                      data.shape[-i-1] + 1))
                    out = np.delete(out, del_range, axis = -i-1)
                    out = np.insert(out, insert_vals, 0, axis = -i-1)

            if stype == 1:
                out = np.roll(out, shift, axis = -i-1)

        self.setData('out', out)

        return(0)

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
