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
# Date: 2014Apr

import numpy as np
import sys
import gpi
import math

class ExternalNode(gpi.NodeAPI):
  
    """Node to get compare 2 numpy arrays
    
    INPUT - Two data sets to be compared - they must be the same size and type

    OUTPUT:
    diff - Difference image (L - R) after optional normalization

    WIDGETS:
    Info: gives RSS Difference and Dot Product after optional normalization
          define D = L - R
          define A* as an array with conjugate element values of the array A
          define A A* as the element-wise product of A and A*
          RSS Difference = sqrt(sum(D D*)), where the sum is over all elements
          Dot Product = sum(L R*), where the sum is over all elements

          When data are normalized, the Dot product is the correlation (assuming 0 mean)

    Normalize: Divide each array A by sqrt(sum(A A*)), where A* is the conjugate of A, and the sum is over all elements
          this effectively makes each array have "unit length"
    """

    def initUI(self):
      self.addWidget('TextBox', 'Info')
      self.addWidget('PushButton', 'Normalize', toggle=True, val=1)
      self.addInPort('inLeft', 'NPYarray', dtype=[np.complex64, np.complex128, np.float32, np.float64])
      self.addInPort('inRight','NPYarray', dtype=[np.complex64, np.complex128, np.float32, np.float64])
      self.addOutPort('diff', 'NPYarray')
        
    def validate(self):
      data1 = self.getData('inLeft')
      data2 = self.getData('inRight')
        
      data1_shape = list(data1.shape)
      data2_shape = list(data2.shape)
      if data1_shape != data2_shape:
        self.log.warn("Two data sets must be the same size")
        return(1)
      if np.iscomplexobj(data1) != np.iscomplexobj(data2):
        self.log.warn("Two data sets must both be complex or both be real")
        return(1)
        
      return(0)

    def compute(self):
      
        import sys
        import numpy as np
        import scipy as sp
        
        data1 = self.getData('inLeft')
        data2 = self.getData('inRight')
        normalize = self.getVal('Normalize')

        if np.iscomplexobj(data1): # This means they both are complex
          if normalize:
            # Dividing arrays by their root-sum-square values makes them "unit vectors" in n-dim space
            rss1 = np.sqrt(np.sum(data1*np.conj(data1)))
            rss2 = np.sqrt(np.sum(data2*np.conj(data2)))
            if rss1 > 0:
              data1 = data1/rss1
            if rss2 > 0:
              data2 = data2/rss2
          datdiff = data1-data2
          rssd = np.sqrt(np.sum(datdiff*np.conj(datdiff)))
          dot = np.sum(data1*np.conj(data2))
      
        else: # Data are real-valued
          if normalize:
            rss1 = np.sqrt(np.sum(data1*data1))
            rss2 = np.sqrt(np.sum(data2*data2))
            if rss1 > 0:
              data1 = data1/rss1
            if rss2 > 0:
              data2 = data2/rss2
          datdiff = data1-data2
          rssd = np.sqrt(np.sum(datdiff*datdiff))
          dot = np.sum(data1*data2)

        self.setData('diff',datdiff)
        info = "RSS Difference = "+str(rssd)+'\n\n'+"Dot Product ="+str(dot)
        self.setAttr('Info', val=info)
    
        return(0)
