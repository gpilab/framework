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


# Author: Zhiqiang Li 
# Date: 2015nov20
# Note: Modified from Dimensions witten by Ryan Robison.

import gpi
import numpy as np

#################################
#################################

class ExternalNode(gpi.NodeAPI):
    """A module for splitting a specified dimension of the input data.
       InData: The data to be splitted.
       Split Dimension: The specific dimension to be splitted.
       Fix: User specifies either new low or high dimension size.
       Fixed Dim Size: the "new size" of the fixed low or high dimension.
    """

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'Info:')
        self.maxdim = 8
        self.ndim = self.maxdim
        dim_buttons = []
        for i in range(-self.maxdim, 0):
           dim_buttons.append(str(i))
        self.addWidget('ExclusivePushButtons', 'Split Dimension',
                buttons=dim_buttons, val=-1)
        self.addWidget('ExclusivePushButtons', 'Fix',
                buttons=['Low Dim', 'High Dim'],val=0)
        self.addWidget('Slider', 'Fixed Dim Size', val=1, min=1, max=32)
        self.addWidget('PushButton', 'Compute', toggle=True, val=0)

        # IO Ports
        self.addInPort('InData', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('outData', 'NPYarray')

    def validate(self):
        self.log.info("Start Validation")
        data = self.getData('InData')
        if data is not None:
            self.log.info("    Validate selected dimenions")
            sel = self.getVal('Split Dimension')
            if sel >= 0:
                sel = sel - self.ndim
            if (-sel) > data.ndim:
                self.log.warn("Try to split a dimension beyond " + \
                        "the input dimensions!")
                return (1)

            dim_buttons = []
            for i in range(-data.ndim, 0):
                dim_buttons.append(str(i))
            self.setAttr('Split Dimension', buttons=dim_buttons, val=sel)
            self.maxdim = data.ndim
            self.ndim = self.maxdim

            self.log.info("    Validate desired new size")
            fixedDimSize = self.getVal("Fixed Dim Size")
            size0 = int(data.shape[sel]/fixedDimSize)*fixedDimSize
            if data.shape[sel] != size0:
                self.log.warn("Can't split " + str(int(data.shape[sel])) + \
                        " to " + str(fixedDimSize))
                return (1)
            sel = self.getVal('Split Dimension')
            if sel >= 0:
                sel = sel - self.ndim
            LowHighFlag = self.getVal("Fix")
            if LowHighFlag == 0: # set low dimension to new size
                lowDimSize = fixedDimSize
                highDimSize = data.shape[sel]/lowDimSize
            else:
                highDimSize = fixedDimSize
                lowDimSize = data.shape[sel]/highDimSize
            newDim = list(data.shape[-data.ndim:sel]) + [int(highDimSize)] + \
                    [int(lowDimSize)]
            if sel < -1:
                newDim = newDim + list(data.shape[(sel+1):])

            info = "Input:  " + str(data.shape) + "\n" \
                   "Output: " + str(newDim)
            self.setAttr("Info:", val=info)
        return (0)
         
    def compute(self):

        if self.getVal('Compute') is True:
            data = self.getData('InData')
            sel = self.getVal('Split Dimension')
            if sel >= 0:
                sel = sel - self.ndim
            fixedDimSize = self.getVal("Fixed Dim Size")
            LowHighFlag = self.getVal("Fix")
            if LowHighFlag == 0: # set low dimension to new size
                lowDimSize = fixedDimSize
                highDimSize = data.shape[sel]/lowDimSize
            else:
                highDimSize = fixedDimSize
                lowDimSize = data.shape[sel]/highDimSize
            newDim = list(data.shape[-data.ndim:sel]) + [int(highDimSize)] + [int(lowDimSize)]
            if sel < -1:
                newDim = newDim + list(data.shape[(sel+1):])
            splittedData = data.reshape(newDim)
            self.setData("outData", splittedData)
        return(0)

    def execType(self):
        return gpi.GPI_PROCESS
