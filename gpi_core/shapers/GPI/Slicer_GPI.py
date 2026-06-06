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
# Date: 2012sep02

import gpi


class ExternalNode(gpi.NodeAPI):
    """A module for slicing through numpy arrays.
    INPUT - input
    OUTPUT - sliced data

    WIDGETS:
    I/O Info: - size of input, output arrays
    Dimension# - dimension along which to slice
    Slice# - index along that dimension to slice
    """

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('Slider', 'Dimension #', val=1)
        self.addWidget('Slider', 'Slice #', val=1)

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray')

    def compute(self):

        data = self.getData(0)

        # set current slice dimension
        self.setAttr('Dimension #', min=1, max=data.ndim)
        userdim = self.getVal('Dimension #')-1

        # reset sliders based on input data
        self.setAttr('Slice #', min=1, max=data.shape[userdim])

        # slice the dimension of interest
        s = self.getVal('Slice #')-1

        xi = []
        for i in range(len(data.shape)-1-userdim):
            xi += [slice(None)]
        outdim = [Ellipsis, s] + xi
        out = data[outdim]

        # update UI info
        self.setAttr('I/O Info:', val="input: "+str(
            data.shape)+"\noutput: "+str(out.shape))

        self.setData('out', out)

        return(0)
