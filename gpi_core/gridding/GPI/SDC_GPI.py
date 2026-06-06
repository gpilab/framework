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
    wates - optional relative weights, used to preferentially use some data over others in areas of overlap
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
        self.addWidget('Slider','Dims per Set',min=1,val=2)
        self.addWidget('SpinBox','Iterations',val=1, min=1)
        self.addWidget('DoubleSpinBox','Effective MTX XY',val=300.0, min=2.0)
        self.addWidget('DoubleSpinBox','Effective MTX Z',val=300.0, min=2.0)
        self.addWidget('DoubleSpinBox','Taper',val=0.0, min=0.0, max = 1.0, singlestep = 0.01)
        self.addWidget('DoubleSpinBox','krad Scale',val=1.0, min=0.2, max = 2.0, singlestep = 0.1)

        # IO Ports
        self.addInPort('crds', 'NPYarray')
        self.addInPort('wates', 'NPYarray', obligation = gpi.OPTIONAL)
        self.addInPort('params_in', 'DICT', obligation = gpi.OPTIONAL)
        self.addOutPort('sdc', 'NPYarray')

    def validate(self):
        crds  = self.getData('crds')
        wates  = self.getData('wates')
        inparam = self.getData('params_in')

        # Check for compatibility
        if crds.shape[-1] not in [1,2,3]:
          self.log.warn("SDC(): Warning, data is not 1-, 2-, or 3-vec, skipping...")
          return 1
        if wates is not None:
          if wates.shape != crds[...,0].shape:
            self.log.warn("Wates Dimension does not match coords")
            return 1

        # Set a couple of conditional attributes
        self.setAttr('Effective MTX Z', visible=crds.shape[-1]==3)
        self.setAttr('Dims per Set', max = crds.ndim-1)

        # Auto Matrix calculation: extra 25% assumes "true resolution"
        # A more robust version will check to see if this is spiral, etc...
        if (inparam is not None):
            if 'headerType' in inparam:
                # old ReadPhilips param output
                if inparam['headerType'] == 'BNIspiral':
                    mtx_xy = (1.25*float(inparam['spFOVXY'][0])/
                              float(inparam['spRESXY'][0]))
                    stype = int(float(inparam['spSTYPE'][0]))
                    if crds.shape[-1] == 3:
                        mtx_z  = (float(inparam['spFOVZ'][0])/
                                  float(inparam['spRESZ'][0]))
                        if stype in [2,3]:  # SDST, FLORET
                            mtx_z *= 1.25
                        self.setAttr('Effective MTX Z', val=mtx_z)

                # new ReadPhilips param output
                elif inparam['headerType'] == 'spparams':
                    stype = inparam['SPIRAL_TYPE']
                    # consider oversample factor DHW
                    if 'OVER_SAMP' in inparam:
                        mtx_xy = int(1.25*inparam['FOV_CM'][0]*inparam['OVER_SAMP'][0] / inparam['RES_CM'][0]+0.5)
                    else:
                        mtx_xy = int(1.25*inparam['FOV_CM'][0] / inparam['RES_CM'][0]+0.5)

                    if crds.shape[-1] == 3:
                        mtx_z = (inparam['FOV_CM'][2] / inparam['RES_CM'][2])
                        if stype in [2,3]:  # SDST, FLORET
                            mtx_z *= 1.25
                        self.setAttr('Effective MTX Z', val=mtx_z)
                else:
                    self.log.warn("wrong header type")
                    return 1
            else:
                # if there is no header type, then its also the wrong type
                self.log.warn("wrong header type")
                return 1

            self.setAttr('Effective MTX XY', val = mtx_xy)

    def compute(self):

        import numpy as np

        dps = self.getVal('Dims per Set')
        mtx_xy = self.getVal('Effective MTX XY')
        mtx_z  = self.getVal('Effective MTX Z')
        numiter = self.getVal('Iterations')
        taper = self.getVal('Taper')
        kradscale = self.getVal('krad Scale')
        crds   = self.getData('crds')
        inwates  = self.getData('wates')

        mtxsz_xy = (2.*mtx_xy)+6
        mtxsz_z  = (2.*mtx_z)+6

        sdshape = crds[...,0].shape
        maxi = crds.ndim - 2
        npts = 1
        for i in range(dps):
          npts *= sdshape[maxi-i]
        nsets = int(crds[...,0].size/npts)

        # Reshape crds to be 3 dimensional - # sets, # pts/set, and dimensionality (1-3)
        crds = np.reshape(crds.astype(np.float64),(nsets,npts,crds.shape[-1]))

        if self.getVal('computenow'):

          if inwates is not None:
            wates = np.copy(inwates.reshape(nsets,npts).astype(np.float64))
          else:
            wates = np.ones((nsets,npts), dtype=np.float64)

          # import in thread to save namespace 
          import gpi_core.gridding.sdc as sd
          for set in range(nsets):
            if crds.shape[-1] == 1:
              cmtxdim = np.array([mtxsz_xy],dtype=np.int64)
              sdcset = sd.oned_sdc(crds[set,:],wates[set,:],cmtxdim,numiter,taper)
            if crds.shape[-1] == 2:
              cmtxdim = np.array([mtxsz_xy,mtxsz_xy],dtype=np.int64)
              sdcset = sd.twod_sdc(crds[set,:],wates[set,:],cmtxdim,numiter,taper)
            if crds.shape[-1] == 3:
              cmtxdim = np.array([mtxsz_xy,mtxsz_xy,mtxsz_z],dtype=np.int64)
              sdcset = sd.threed_sdc(crds[set,:],wates[set,:],cmtxdim,numiter,taper,kradscale)
            if set == 0:
              sdc = np.expand_dims(sdcset,0)
            else:
              sdc = np.append(sdc,np.expand_dims(sdcset,0),axis=0)

          # Reshape sdc weights to match that of incoming coordinates
          self.setData('sdc', np.reshape(sdc,sdshape))

        return(0)

