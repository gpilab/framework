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


# Author: Sudarshan Ragunathan
# Date: 2014may28

import numpy as np
import gpi


class ExternalNode(gpi.NodeAPI):
    """Performs a 1D-histogram of the non-zero values in a Numpy Array.

    INPUT - numpy array (data type : float or complex)
    
    OUTPUT:
    HistVal - Values in each histogram bin (1D numpy array)
    HistBin - Vector of bins (1D numpy array)

    WIDGETS:
    R I M - Choose from Real, Imaginary or Magnitude data (Visible for complex input)
    Bins - Number of bins
    Range - Lower and Upper range of the bins. The user has the option of specifying
            the range or using the max and min of the input
    """

    def initUI(self):

        # Widgets
        self.addWidget('ExclusivePushButtons', 'R I M', buttons=['R', 'I', 'M'], val=2)
        self.addWidget('DoubleSpinBox', '# Bins', val=500)
        self.addWidget('DoubleSpinBox', 'Lower Bound', val=0.)
        self.addWidget('DoubleSpinBox', 'Upper Bound', val=255.)
        self.bin_op = ['Set Range','Use Min/Max']
        self.addWidget('ExclusiveRadioButtons', 'Bin Range', buttons=self.bin_op, val=0)

        # IO Ports
        self.addInPort('Data In', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('HistVal', 'NPYarray')
        self.addOutPort('HistBin', 'NPYarray')

    def validate(self):
        im_input = self.getData('Data In')
        
        # Check for dtype of Input (Visibility of R I M op)
        im_type = str(im_input.dtype)
        if 'float' in im_type:
            self.setAttr('R I M', visible=False)
            data_in = im_input
        elif 'complex' in im_type:
            self.setAttr('R I M', visible=True)
            op = self.getVal('R I M')
            if op == 0:
                data_in = np.real(im_input)
            elif op == 1:
                data_in = np.imag(im_input)
            else:
                data_in = np.abs(im_input)
        data = data_in[np.nonzero(data_in)] 
        data_min = np.amin(data)
        data_max = np.amax(data)

        # Reset the min and max of the lower and upper bounds of bins
        #self.setAttr('Lower Bound', val=data_min)
        #self.setAttr('Upper Bound', val=data_max)
        bin_range = self.getVal('Bin Range')
        if bin_range == 1:
            self.setAttr('Lower Bound', visible=False)
            self.setAttr('Upper Bound', visible=False)
            self.setAttr('Lower Bound', val=data_min)
            self.setAttr('Upper Bound', val=data_max)
        else:
            self.setAttr('Lower Bound', visible=True)
            self.setAttr('Upper Bound', visible=True)

        # Check for Lower > Upper Bound
        lbound = self.getVal('Lower Bound')
        ubound = self.getVal('Upper Bound')
        if lbound > ubound:
            self.setAttr('Lower Bound', val=np.maximum(lbound,ubound))
            self.setAttr('Upper Bound', val=np.maximum(lbound,ubound))

        return(0)

    def compute(self):

        import numpy as np
        
        im_input = self.getData('Data In')
        op = self.getVal('R I M')
        if op == 0:
            data_in = np.real(im_input)
        elif op == 1:
            data_in = np.imag(im_input)
        else:
            data_in = np.abs(im_input)
        data = data_in[np.nonzero(data_in)]
        lbound = self.getVal('Lower Bound')
        ubound = self.getVal('Upper Bound')
        bins = self.getVal('# Bins')

        hist_out = np.histogram(data,bins,range=(lbound,ubound))
        self.setData('HistVal', hist_out[0])
        self.setData('HistBin', hist_out[1])
        return(0)




