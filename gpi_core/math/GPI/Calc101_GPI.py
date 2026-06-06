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


# Author: Jim Pipe
# Date: 2013Jul

import numpy as np
import scipy
from scipy import integrate as int
import gpi

class ExternalNode(gpi.NodeAPI):
    """Integrate or Differentiate along a given axis

    INPUT - numpy array to operate on

    OUTPUT - numpy array after operation

    WIDGETS:
    Operation - select Integerate or Differentiate operation
    Dimension - select axis along with to integerate or differentiate
    """

    def initUI(self):

        # Widgets
        # Edge clause default setting
        self.edgeMode = 0
        self.func = 0
        self.op_labels = ['Integrate', 'Derivative','Discrete Diff.']
        self.addWidget('ExclusivePushButtons', 'Operation', buttons=self.op_labels
                        , val = 0)
        self.addWidget('Slider', 'Dimension', val = 0, min=0)
        self.addWidget('ExclusivePushButtons', 'Endpoint Treatment', buttons = [
                       '1st order','2nd order'], val = self.edgeMode)
        self.addWidget('ExclusivePushButtons', 'Method', buttons = [
                       'Rect.','Trap.'], val = self.edgeMode)

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        data = self.getData('in')

        if self.getVal('Operation') == 0:
            self.setAttr('Endpoint Treatment', visible = False)
            self.setAttr('Method', visible = True)
        elif self.getVal('Operation') == 1:
            self.setAttr('Endpoint Treatment', visible = True)
            self.setAttr('Method', visible = False)
        else:
            self.setAttr('Endpoint Treatment', visible = False)
            self.setAttr('Method', visible = False)

        if data is not None:
            self.setAttr('Dimension', max=(len(data.shape)-1), min=(-len(data.shape)))

        self.setDetailLabel('{}'.format(self.op_labels[self.getVal('Operation')]))
        return(0)

    def compute(self):
        import numpy as np

        data = self.getData('in')
        if data is not None:
            if self.getVal('Operation') == 0:
                if self.getVal('Method') == 0:
                    out = np.cumsum(data, axis=self.getVal('Dimension'))
                else:
                    out = int.cumtrapz(data, axis=self.getVal('Dimension'),
                                        initial = 0)
            elif self.getVal('Operation') == 1:
                order = self.getVal('Endpoint Treatment') + 1;
                out = np.gradient(data, axis=self.getVal('Dimension'),
                                edge_order=order)
            else:
                out = np.diff(data,axis=self.getVal('Dimension'))
            self.setData('out', out)

        return(0)

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
