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

import numpy as np
import gpi


class ExternalNode(gpi.NodeAPI):
    """Generate Statistics for numpy array.

    For complex input all statistics are computed on the magnitude |data|.

    min, max, mean, std, sum, and median are reported in the Data Statistics
    text box and available via separate output ports.
    """
    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'Data Statistics:')

        # IO Ports
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addOutPort('min',    'FLOAT')
        self.addOutPort('max',    'FLOAT')
        self.addOutPort('mean',   'FLOAT')
        self.addOutPort('std',    'FLOAT')
        self.addOutPort('sum',    'FLOAT')
        self.addOutPort('median', 'FLOAT')

    def compute(self):

        data = self.getData('in')

        is_complex = np.iscomplexobj(data)
        d = np.abs(data) if is_complex else data

        dmin   = float(d.min())
        dmax   = float(d.max())
        dmean  = float(d.mean())
        dstd   = float(d.std())
        dsum   = float(d.sum())
        dmed   = float(np.median(d))

        prefix = '|data| ' if is_complex else ''
        info = (f"shape:    {list(data.shape)}\n"
                f"dtype:    {data.dtype}\n"
                f"elements: {data.size}\n\n"
                f"{prefix}min:    {dmin}\n"
                f"{prefix}max:    {dmax}\n"
                f"{prefix}mean:   {dmean}\n"
                f"{prefix}std:    {dstd}\n"
                f"{prefix}sum:    {dsum}\n"
                f"{prefix}median: {dmed}")

        self.setAttr('Data Statistics:', val=info)
        self.setData('min',    dmin)
        self.setData('max',    dmax)
        self.setData('mean',   dmean)
        self.setData('std',    dstd)
        self.setData('sum',    dsum)
        self.setData('median', dmed)

        return 0
