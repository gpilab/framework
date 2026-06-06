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
# Date: 2013 Aug

import gpi
import numpy as np

class ExternalNode(gpi.NodeAPI):
    """Inverse Gridding module for Post-Cartesian Data using DFT - works with 2D data
    This is to create exact k-space data corresponding to any image, often for simulation and testing

    INPUTS:
    image - k-space complex data - if not supplied, Grid uses "1" for all of its data
    coords - k-space coordinates, normalized in units of "1/resolution", i.e. ranging from -0.5 to 0.5
               Last dimension must be 2 or 3 (corresponding to kx/ky or kx/ky/kz, respectively)
               Coordinates at the very edge of gridded k-space then have values of -/+ 0.5

    OUTPUTS:
    out - gridded data, same dimensions as coords
    
    WIDGETS:
    Eff Mtx - effective matrix of coords (specifies Nyquist distance)
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):

        # Widgets
        self.addWidget('SpinBox','Eff Mtx',min=10,val = 100)

        # IO Ports
        self.addInPort('data', 'NPYarray', ndim=2, dtype=[np.complex64, np.complex128])
        self.addInPort('coords', 'NPYarray', dtype=[np.float32, np.float64])
        self.addInPort('weighting', 'NPYarray', dtype=[np.float32, np.float64], obligation=gpi.OPTIONAL)
        self.addOutPort('image', 'NPYarray', dtype= np.complex128)

    def validate(self):
        crds = self.getData('coords')

        if crds.shape[-1] != 2:
          self.log.warn(" Error: only 2 dimensional gridding implemented")
          return 1
        
        return 0

    def compute(self):

        import numpy as np
        import gpi_core.gridding.dft as dft

        effmtx = self.getVal('Eff Mtx')
        data = self.getData('data').astype(np.complex128)
        crds = self.getData('coords').astype(np.float64)
        wghts = self.getData('weighting')
        newcrds = np.reshape(crds,(crds[...,0].size,2))

        if wghts is not None:
          if wghts.ndim != crds.ndim - 1:
            self.log.warn("# of dimensions of weights must match crds")
            return 1
          else: 
            for i in range(crds.ndim-1):
              if crds.shape[i] != wghts.shape[i]:
                self.log.warn("sizes of weights and coords don't match")
                return 1

        # Make wghts or reshape it
        if wghts is None:
            wghts = np.ones((crds[...,0].size,), dtype=np.float32)
        else:
            # Reshape wghts to be 2 dimensional
            wghts = np.reshape(wghts.astype(np.float32),(crds[...,0].size,))

        #outdim = np.array([crds[...,0].size],dtype=np.int64)
        outdim = np.array([effmtx,effmtx],dtype=np.int64)

        out = dft.dft_grid(data,newcrds,outdim,effmtx,wghts.astype(np.float64))

        #out = np.reshape(out,crds[...,0].shape)
        self.setData('image', out)

        return(0)
