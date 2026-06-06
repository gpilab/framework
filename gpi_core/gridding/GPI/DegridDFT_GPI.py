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
    offres - off-resonance map (in delta-Hz)
    coords - k-space coordinates, normalized in units of "1/resolution", i.e. ranging from -0.5 to 0.5
               Last dimension must be 2 or 3 (corresponding to kx/ky or kx/ky/kz, respectively)
               Coordinates at the very edge of gridded k-space then have values of -/+ 0.5

    OUTPUTS:
    out - gridded data, same dimensions as coords
    
    WIDGETS:
    Eff Mtx - effective matrix of coords (specifies Nyquist distance)
    dwell (us) - time per sample, required for off-resonance degridding
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):

        # Widgets
        self.addWidget('SpinBox','Eff Mtx',min=10,val = 240)
        self.addWidget('DoubleSpinBox','dwell (us)', min=0.0, val = 2.0)

        # IO Ports
        self.addInPort('image', 'NPYarray', ndim=2, dtype=[np.complex64, np.complex128])
        self.addInPort('offres', 'NPYarray', ndim=2, dtype=[np.float32, np.float64],obligation=gpi.OPTIONAL)
        self.addInPort('coords', 'NPYarray', dtype=[np.float32, np.float64])

        self.addOutPort('data', 'NPYarray', dtype= np.complex128)

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
        dwell = self.getVal('dwell (us)') * 1e-6
        image = self.getData('image').astype(np.complex128)
        offres = self.getData('offres')
        crds = self.getData('coords').astype(np.float64)
        narms, npts, ndim = crds.shape

        time = np.linspace(0, dwell*npts, npts)
        time = np.tile(time, (narms,1))

        if offres is None:
            offres = np.zeros(image.shape)

        newcrds = np.reshape(crds,(crds[...,0].size,2))
        outdim = np.array([crds[...,0].size],dtype=np.int64)

        # out = dft.dftgrid(image,newcrds,outdim,effmtx)
        out = dft.dftgrid(image,offres,newcrds,time,outdim,effmtx)

        out = np.reshape(out,crds[...,0].shape)
        self.setData('data', out)

        return(0)
