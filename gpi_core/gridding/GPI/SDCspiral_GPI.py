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


# Author: Jim Pipe
# Date: 2013Aug

import gpi
import numpy as np

class ExternalNode(gpi.NodeAPI):
    """Computes Sampling Density Correction for 2D and 3D waveforms

    INPUTS
    crds - input coordinates, which range from -0.5 to +0.5.
           the last dimension is 2 or 3, corresponding to 2D (kx/ky) or 3D (kx/ky/kz)
    params_in - optional dictionary from (e.g.) spiralcoords, to automatically specify the effective matrix

    OUTPUTS - sampling density, same size as crds (minus the last dimension)

    WIDGETS:
    computenow - turn off to change effective matrix without computing the sampling density
    Dims per Set - how many of the dimensions to compute together as 1 set of coordinates.  Allows for extra
                   dimensions for (e.g.) slices, diffusion weightings, whatever
    Iterations - times to iterate algorithm
    Effective Matrix XY - FOV/resolution in X&Y, which indicates the width of data correlation in k-space
    Effective Matrix Z - FOV/resolution in Z, which indicates the width of data correlation in k-space
    Taper - taper the weights at the edge of k-space; value indicates the fraction of k-space radius to
            (linearly) taper from 1 to 0 (at the very edge): 0 gives no taper, 1 is "full" taper
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):      

        # Widgets
        self.addWidget('PushButton','computenow',toggle=True)
        self.addWidget('SpinBox','Iterations',val=1, min=1)
        self.addWidget('DoubleSpinBox','Effective MTX XY',val=300.0, min=2.0)
        self.addWidget('DoubleSpinBox','Effective MTX Z',val=300.0, min=2.0)
        self.addWidget('DoubleSpinBox','Taper',val=0.0, min=0.0, max = 1.0, singlestep = 0.01)

        # IO Ports
        self.addInPort('crds', 'NPYarray')
        self.addInPort('params_in', 'DICT', obligation = gpi.OPTIONAL)
        self.addOutPort('sdc', 'NPYarray')

    def validate(self):
        crds  = self.getData('crds')
        inparam = self.getData('params_in')

        # Check for compatibility: 2 or 3-vector only right now
        if crds.shape[-1] not in [2,3]:
          self.log.warn("SDC(): Warning, data are not 2-vec or 3-vec, skipping...")
          return 1

        # Set a couple of conditional attributes
        self.setAttr('Effective MTX Z', visible=crds.shape[-1]==3)

        # Auto Matrix calculation: extra 25% assumes "true resolution"
        # A more robust version will check to see if this is spiral, etc...
        if (inparam is not None):
          mtx_xy = 1.25*float(inparam['spFOVXY'][0])/float(inparam['spRESXY'][0])
          self.setAttr('Effective MTX XY', val = mtx_xy)
          if crds.shape[-1] == 3:
            mtx_z  = float(inparam['spFOVZ'][0]) /float(inparam['spRESZ'][0])
            if int(float(inparam['spSTYPE'][0])) in [2,3]: #SDST, FLORET
              mtx_z *= 1.25
            self.setAttr('Effective MTX Z', val = mtx_z)

    def compute(self):

        import numpy as np

        mtx_xy = self.getVal('Effective MTX XY')
        mtx_z  = self.getVal('Effective MTX Z')
        numiter = self.getVal('Iterations')
        taper = self.getVal('Taper')
        crds   = self.getData('crds')
  
        # flip the coords if spiralin
        ktrace = crds[0,:,0]*crds[0,:,0] + crds[0,:,1]*crds[0,:,1]
        spiralin = 0
        if ktrace[-1] < ktrace[0]:
            crds[:,:,:] = crds[:,::-1,:]
            spiralin = 1

        if self.getVal('computenow'):

          # import in thread to save namespace 
          import gpi_core.gridding.sdc as sd
          if crds.shape[-1] == 2:
            sdc = sd.twod_sdcsp(crds,numiter,taper,mtx_xy)
          if crds.shape[-1] == 3:
            sdc = sd.threed_sdcsp(crds,numiter,taper,mtx_xy, mtx_z)

          if spiralin:
            sdc = sdc[:,::-1]   

          self.setData('sdc', sdc)

        return(0)

