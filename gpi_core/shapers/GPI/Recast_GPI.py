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


# Author: Dallas Turley
# Date: 2013sep09

import numpy as np
import gpi

class ExternalNode(gpi.NodeAPI) :
  """Change the NPY array data type (dtype) from any type to int<n>, uint<n>, float<n> and complex<n>, where 'n' represents the numbe of bits.
  """

  def initUI(self) :
    self.addWidget('TextBox', 'info', val = '\n\n ')
    self.opbuttons = ['int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64', 'float16', 'float32', 'float64', 'complex64', 'complex128']
    self.addWidget('ExclusiveRadioButtons', 'OutType', buttons=self.opbuttons,val=9)

    self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
    self.addOutPort('out', 'NPYarray')

  def compute(self) :

    data = self.getData('in')
    intype = data.dtype

    choice = self.getVal('OutType')
    typ = self.opbuttons[choice]

    out = data.astype(typ)
    outtype = out.dtype

    text = "Input data type    :  " +str(intype)+"\nOutput data type :  " +str(outtype)+"\n"
    self.setAttr('info',val=text)


    self.setData('out', out)

    return 0
    
  def execType(self) :
    return gpi.GPI_PROCESS
