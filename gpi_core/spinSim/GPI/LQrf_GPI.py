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
# Date: 2013Jun13

import gpi
from gpi import QtWidgets


class ExternalNode(gpi.NodeAPI):
    """Module to generate LQ rf pulse
    """

    def initUI(self):
        # Widgets
        self.addWidget('SpinBox', 'resolution', val=500, min=100)
        self.addWidget('DoubleSpinBox', 'M', val=8.)
        self.addWidget('DoubleSpinBox', 'Window', val=0.1 , min=0., max=1.)

        # IO Ports
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        '''This function runs before compute() as a GPI_APPLOOP exec-type.
        Here, widgets (bounds, limits, etc...) can be modified to ensure they
        are correctly validated before the widget values are used in the
        compute() routine -where widgets are buffered and any modifications are
        applied after compute() runs.
        '''

        # validate widget bounds
        return 0

    def compute(self):
       '''This is where the main algorithm should be implemented.
       '''

       import numpy as np

       dims = self.getVal('resolution')
       mval = self.getVal('M')
       win  = 0.5*self.getVal('Window')

       out = np.zeros((dims,),dtype=np.complex128)

       for i in range(dims):
         t = (float(i)+0.5)/float(dims)
         if (t<win):
           mag = t/win
         elif (t>1.-win): 
           mag = (1.-t)/win
         else:
           mag = 1.

         t2 = 4.*(t-.5)*(t-.5)
         phs = 2.*np.pi*t2*(mval/8.)
         out[i] = mag * np.exp(1j * phs)
       

       # SETTING PORT INFO
       self.setData('out', out)

       return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
