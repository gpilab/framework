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
from gpi.arrayops import concatenate as _concatenate, expand_dims as _expand_dims


class ExternalNode(gpi.NodeAPI):
    """Combine two data sets along any dimension.
    e.g. put two images side-by-side

    Both ports accept a NumPy array or a PyTorch tensor (matching kinds);
    the output is the same kind as the input.

    Several restrictions are in place requiring arrays to be of the same size;
      this module should be updated to be more flexible in the future
    """

    def initUI(self):
        # Widgets
        self.addWidget('TextBox', 'Info', val='Ready')
        self.addWidget('Slider', 'Combine Dimension',min=-1,max=0,val=0)

        # IO Ports
        self.addInPort('indata1', 'NPYorTorch', obligation=gpi.REQUIRED)
        self.addInPort('indata2', 'NPYorTorch', obligation=gpi.REQUIRED)

        self.addOutPort('outdata', 'NPYorTorch')

    def validate(self):
        
        indata1  = self.getData('indata1')
        indata2  = self.getData('indata2')
        if indata1 is None or indata2 is None:
            return 0
        comb_dim = self.getVal('Combine Dimension')
        self.setAttr('Combine Dimension', max = indata1.ndim, val=comb_dim)

        if comb_dim == indata1.ndim or comb_dim == -1:
            output_shape = (tuple(indata1.shape) if comb_dim == indata1.ndim else () )
            output_shape = ((1,) + tuple(indata1.shape) if comb_dim == -1 else
                            tuple(indata1.shape) + (1,))
        else:
            output_shape = list(indata1.shape)
            output_shape[comb_dim] += indata2.shape[comb_dim]
            output_shape = tuple(output_shape)
        info = ("input1 : " + str(tuple(indata1.shape)) + "\n" +
                "input2 : " + str(tuple(indata2.shape)) + "\n" +
                "output : " + str(output_shape))
        self.setAttr('Info', val=info)

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''
        indata1  = self.getData('indata1')
        indata2  = self.getData('indata2')
        comb_dim = self.getVal('Combine Dimension')
        
        try:
            if comb_dim == indata1.ndim:
                temp1 = _expand_dims(indata1, comb_dim)
                temp2 = _expand_dims(indata2, comb_dim)
                outdata = _concatenate([temp1, temp2], comb_dim)
            elif comb_dim == -1:
                temp1 = _expand_dims(indata1, 0)
                temp2 = _expand_dims(indata2, 0)
                outdata = _concatenate([temp1, temp2], 0)
            else:
                outdata = _concatenate([indata1, indata2], comb_dim)
        except (ValueError, RuntimeError, TypeError) as dim_err:
            self.log.warn('Combine error: ' + str(dim_err))
        else:
            info = ("input1 : " + str(tuple(indata1.shape)) + "\ninput2 : " +
                    str(tuple(indata2.shape)) + "\noutput : " + str(tuple(outdata.shape)))
            self.setAttr('Info', val=info)
            self.setData('outdata', outdata)

        
        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_THREAD
