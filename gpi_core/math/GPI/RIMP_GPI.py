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


# Author: Jim Pype
# Date: 2012sep02

import numpy as np
import gpi


class ExternalNode(gpi.NodeAPI):
    """Output the Real, Imaginary, Magnitude, or Phase of a Complex array, element-wise
    INPUT - complex data array

    OUTPUT - real-valued array

    WIDGETS:
    R I M P - select Real, Imaginary, Magnitude, or Phase
    Units - for Phase, select Degrees, Radians, or Cycles
    Unwrap - for Phase, you can do simple phase unwrapping in one direction
    Unwrap Dimension - for Phase, choose the dimension for phase unwrapping
    """

    def initUI(self):

        # Widgets
        self.addWidget('ExclusivePushButtons', 'R I M P', buttons=[
                       'R', 'I', 'M', 'P'], val=2)
        self.addWidget('ExclusivePushButtons', 'Units', buttons=[
                       'Deg', 'Rad', 'Cyc'], val=1)
        self.addWidget('PushButton', 'UnWrap', toggle=True)
        self.addWidget('Slider', 'UnWrap Dimension', val = 0, min=0)

        # IO Ports
        self.addInPort('in', 'NPYarray', dtype=[np.complex64, np.complex128],
                       obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray', dtype=[np.float32, np.float64])

        # operations
        self.op = [np.real, np.imag, np.abs, np.angle]

    def validate(self):
        data = self.getData('in')

        self.setAttr('UnWrap Dimension', max=(len(data.shape)-1), min=(-len(data.shape)))

        if self.getVal('R I M P') == 3:
          self.setAttr('Units',visible=True)
          self.setAttr('UnWrap',visible=True)
          self.setAttr('UnWrap Dimension',visible=self.getVal('UnWrap'))
        else:
          self.setAttr('Units',visible=False)
          self.setAttr('UnWrap',visible=False)
          self.setAttr('UnWrap Dimension',visible=False)

        L = ['Real', 'Imaginary', 'Magnitude', 'Phase']
        self.setDetailLabel(L[self.getVal('R I M P')])

        return(0)

    def compute(self):

        import numpy as np

        data = self.getData('in')

        out = self.op[self.getVal('R I M P')](data)
        if self.getVal('R I M P') == 3:
          if self.getVal('UnWrap'):
            out = np.unwrap(out, discont = np.pi, axis = self.getVal('UnWrap Dimension'))
          if self.getVal('Units') == 0:
            out = 180*out/np.pi
          if self.getVal('Units') == 2:
            out = out/(2.*np.pi)

        self.setData('out', out)
        return(0)
