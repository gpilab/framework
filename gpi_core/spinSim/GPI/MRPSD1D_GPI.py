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
# Date: 2013Jun18

import gpi
import numpy as np

class ExternalNode(gpi.NodeAPI):
    """Reformats pulse sequence information from  Bloch- (potentially cascaded
    Bloch-) node(s) for plotting in 1D viewer/plotter nodes.
    """

    def initUI(self):
        # Widgets

        # IO Ports
        self.addInPort('M_in', 'NPYarray',obligation=gpi.REQUIRED)
        self.addOutPort('B_out', 'NPYarray')

        return 0

    def validate(self):
        return 0

    def compute(self):

        # New data
        m_in = self.getData('M_in')
        mdim = list(m_in.shape)

# X Axis
        xval = m_in[6,slice(1,mdim[1]),0,0,0,0,0,0,0,0,0]
# Y Axes
        outvals = m_in[:,slice(1,mdim[1]),0,0,0,0,0,0,0,0,0]
        zr = np.zeros(mdim[1]-1)
        gx = outvals[7,:]
        gy = outvals[8,:]
        gz = outvals[9,:]
        rfx = 1000.*outvals[10,:] # in units of uT
        rfy = 1000.*outvals[11,:] # in units of uT
        y0 = np.column_stack((zr,gx,gy,gz,rfx,rfy))
        x0 = np.column_stack((xval,xval,xval,xval,xval,xval))

        b_out = np.append(x0[:,:,np.newaxis],y0[:,:,np.newaxis],axis=2)

        self.setData('B_out', b_out)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
