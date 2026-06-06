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


# Author: Nick Zwart
# Date: 2012sep02

import gpi


class ExternalNode(gpi.NodeAPI):
    """Generate Statistics for numpy array

    min,max,mean,and std are reported in the Data Statistics Text box, also via separate Outputs
    """
    def execType(self):
        return gpi.GPI_PROCESS
        #return gpi.GPI_THREAD

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'Data Statistics:')

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('min', 'FLOAT')
        self.addOutPort('max', 'FLOAT')
        self.addOutPort('mean', 'FLOAT')
        self.addOutPort('std', 'FLOAT')

    def compute(self):

        data = self.getData('in')

        dmin = data.min()
        dmax = data.max()
        dmean = data.mean()
        dstd = data.std()
        d1 = list(data.shape)

        info = "dimensions: "+str(d1)+"\n\n" \
               "min: "+str(dmin)+", max: "+str(dmax)+"\n" \
               "mean: "+str(dmean)+"\n" \
               "std: "+str(dstd)

        self.setAttr('Data Statistics:', val=info)
        self.setData('min', float(dmin))
        self.setData('max', float(dmax))
        self.setData('mean', float(dmean))
        self.setData('std', float(dstd))

        return(0)
