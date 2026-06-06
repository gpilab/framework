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
# Date: 2013Aug

import gpi
import numpy as np


class ExternalNode(gpi.NodeAPI):
    """Implements rolloff correction in-house 2D gridding module written in C++.
    This module corrects the image shading created by the Grid module and crops the data by 1/3
    in each Gridded dimension to produce an image of the right matrix size

    INPUT: complex data - typically the output of Grid, Fourier Transformed to image space
           These data can represent 1D, 2D or 3D data, with optional extra dimensions representing (e.g.) coils or slices

    OUTPUT: complex data after Rolloff Correction

    WIDGETS:
    Num Rolloff Dims - Set to 1, 2, or 3 corresponding to 1D, 2D, or 3D gridded data sets
                       Remaining dims are treated independently, e.g. as slices, coils, etc.
    Isotropic FOV - multiplies data by a circular/spherical mask for 2D/3D data
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):

        # Widgets
        self.addWidget('Slider','Num Rolloff Dims',min=1,max=3,val=2)
        self.addWidget('PushButton','Isotropic FOV',toggle=True,val=True)

        # IO Ports
        self.addInPort('data', 'NPYarray', dtype=[np.complex64, np.complex128])
        self.addOutPort('out', 'NPYarray', dtype=[np.complex64, np.complex128])

    def validate(self):
        ''' DHW check if input data, coords and weight have the correct dimentions and sizes.
        '''

        data = self.getData('data')
        nrd = self.getVal('Num Rolloff Dims')

        if data.ndim < nrd:
          self.log.warn(" Error: Too few dimensions! ")
          return 1

        return(0)

    def compute(self):

        import numpy as np
        import gpi_core.gridding.grid as gd

        # force complex64 for underlying c++-routine
        data = self.getData('data')
        in_dtype = data.dtype  # make the out-type the same as the in-type

        dshape = np.array(data.shape)
        oshape = np.copy(dshape)
        nrd = self.getVal('Num Rolloff Dims')
        isofov = self.getVal('Isotropic FOV')

        # dimensions for rolloff - we will loop in this wrapper (below) around multiple sets
        # Note we are reversing the order of dimensions - necessary for python-c
        if nrd == 1:
          oshape[-1] = np.ceil(2*dshape[-1]/3.)
          outdim = np.array([oshape[-1] ],dtype=np.int64)
          nsets = np.prod(oshape)//np.prod(outdim)
          newdshape = np.array((nsets,dshape[-1]))
          outdim1 = outdim
        elif nrd == 2:
          oshape[-1] = np.ceil(2*dshape[-1]/3.)
          oshape[-2] = np.ceil(2*dshape[-2]/3.)
          outdim = np.array([oshape[-1], oshape[-2] ],dtype=np.int64)
          nsets = np.prod(oshape)//np.prod(outdim)
          newdshape = np.array((nsets,dshape[-2],dshape[-1]))
          outdim1 = outdim
        elif nrd == 3:
          oshape[-1] = np.ceil(2*dshape[-1]/3.)
          oshape[-2] = np.ceil(2*dshape[-2]/3.)
          oshape[-3] = np.ceil(2*dshape[-3]/3.)
          outdim = np.array([oshape[-1], oshape[-2], oshape[-3] ],dtype=np.int64)
          outdim1 = np.array([oshape[-3], oshape[-2], oshape[-1] ],dtype=np.int64)
          nsets = np.prod(oshape)//np.prod(outdim)
          newdshape = np.array((nsets,dshape[-3],dshape[-2],dshape[-1]))

        # Reshape data to have the first index be # sets, the rest be the rolled-off data
        data = np.reshape(data,newdshape)

        outshape1 = np.append([nsets], outdim1)
        out = np.zeros(outshape1,  dtype = in_dtype)

        for i in range(int(nsets)):
          # force single precision
          outset = gd.rolloff(data[i,...].astype(np.complex64),outdim,isofov)
          out[i,...] = np.require(outset, dtype=in_dtype)

        out = np.reshape(out, oshape)

        self.setData('out', np.require(out, dtype=in_dtype))

        return(0)
