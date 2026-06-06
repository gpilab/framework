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
# Date: 2013Aug

import gpi


class ExternalNode(gpi.NodeAPI):
    """Combine two data sets along any dimension.
    e.g. put two images side-by-side
    
    Several restrictions are in place requiring arrays to be of the same size;
      this module should be updated to be more flexible in the future
    """

    def initUI(self):
        # Widgets
        self.addWidget('TextBox', 'Info', val='Ready')
        self.addWidget('Slider', 'Combine Dimension',min=-1,max=0,val=0)

        # IO Ports
        self.addInPort('indata1', 'NPYarray', obligation=gpi.REQUIRED)
        self.addInPort('indata2', 'NPYarray', obligation=gpi.REQUIRED)

        self.addOutPort('outdata', 'NPYarray')

    def validate(self):
        
        indata1  = self.getData('indata1')
        indata2  = self.getData('indata2')
        comb_dim = self.getVal('Combine Dimension')
        self.setAttr('Combine Dimension', max = indata1.ndim, val=comb_dim)

        info = "input1 : " +str(indata1.shape) + "\n" + "input2 : " +str(indata2.shape)
        self.setAttr('Info', val=info)

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''
        import numpy as np

        indata1  = self.getData('indata1')
        indata2  = self.getData('indata2')
        comb_dim = self.getVal('Combine Dimension')
        
        if comb_dim == indata1.ndim:
            temp1 = np.expand_dims(indata1, comb_dim)
            temp2 = np.expand_dims(indata2, comb_dim)

            try:
                outdata = np.append(temp1, temp2, axis = comb_dim)
            except ValueError as dim_err:
                self.log.warn('Combine error: '+str(dim_err))
            else:
                info = "input1 : " +str(indata1.shape) + "\ninput2 : " +str(indata2.shape) + "\noutput : " +str(outdata.shape)
                self.setAttr('Info', val=info)
                self.setData('outdata',outdata)
        elif comb_dim == -1 :
            temp1 = np.expand_dims(indata1, 0)
            temp2 = np.expand_dims(indata2, 0)

            try:
                outdata = np.append(temp1, temp2, axis = 0)
            except ValueError as dim_err:
                self.log.warn('Combine error: '+str(dim_err))
            else:
                info = "input1 : " +str(indata1.shape) + "\ninput2 : " +str(indata2.shape) + "\noutput : " +str(outdata.shape)
                self.setAttr('Info', val=info)
                self.setData('outdata',outdata)
        else:
            try:
                outdata = np.append(indata1, indata2, axis = comb_dim)
            except ValueError as dim_err:
                self.log.warn('Combine error: '+str(dim_err))
            else:
                info = "input1 : " +str(indata1.shape) + "\ninput2 : " +str(indata2.shape) + "\noutput : " +str(outdata.shape)
                self.setAttr('Info', val=info)
                self.setData('outdata',outdata)

        
        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
