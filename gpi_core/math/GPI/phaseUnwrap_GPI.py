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
# Date: 2013jul01

import numpy as np
import gpi


class ExternalNode(gpi.NodeAPI):
    """Unwraps the data of a numpy array containg phase along the specified dimension.

    Widgets:
    Dimension: dimension to unwrap along
    Units:  choose degrees or radians
    """

    def initUI(self):

        # Widgets
        self.addWidget('SpinBox', 'Dimension', val = 0)
        self.addWidget('ExclusivePushButtons', 'Units',buttons=
                        ['degrees','radians','cycles'],val=1)

        # IO Ports
        self.addInPort('in', 'NPYarray', dtype=[np.float64, np.float32],
                       obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray', dtype=[np.float64, np.float32])

    def validate(self):
        data = self.getData('in')

        self.setAttr('Dimension', max=(len(data.shape)-1),
                          min=(-len(data.shape)))

        return(0)

    def compute(self):

        import numpy as np
        from skimage.restoration import unwrap_phase

        data = self.getData('in')
        dim = self.getVal('Dimension')

        # if self.getVal('Units') == 0: #degrees
        #   out = np.rad2deg(np.unwrap(np.deg2rad(data), discont = np.pi, axis = dim))
        # elif self.getVal('Units') == 2: #cycles
        #   out = np.rad2deg(np.unwrap(np.deg2rad(data*360), discont = np.pi,
        #                     axis = dim)) / 360
        # else: #radians
        #   out = np.unwrap(data, discont = np.pi, axis = dim)
          
        out = unwrap_phase(data)

        self.setData('out', out)
        return(0)

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
