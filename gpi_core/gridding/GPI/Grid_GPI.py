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
    """Gridding module for Post-Cartesian Data - works with 2D and 3D data

    INPUTS:
    data - k-space complex data - if not supplied, Grid uses "1" for all of its data
    coords - k-space coordinates, normalized in units of "1/resolution", i.e. ranging from -0.5 to 0.5
               Last dimension must be 1, 2 or 3 (corresponding to kx, kx/ky, or kx/ky/kz, respectively)
               Coordinates at the very edge of gridded k-space then have values of -/+ 0.5
    weighting - sampling density correction - if not supplied, Grid uses "1"
    params_in - optional dictionary from (e.g.) spiralcoords, to automatically specify the effective matrix

    OUTPUTS:
    gridded data, which is M+E dimensions, where
                  M is 1, 2 or 3, depending on last dimension of coords input (i.e. 1D, 2D, or 3D)
                    The size of these M dimensions is 1.5 times the given effective matrix
                  E is (# input data dims) - (Dims per set widget value)
                    E represents slices, coils, etc., which don't get gridded together.

    WIDGETS:
    Dims per Set - How many dimensions get gridded into the same space (and the space is determined by the last dim of coords)
                   Remaining dimensions are independent, e.g. for slices, coils, etc.
    Eff MTX XY - number of pixels in the final image (XY), nominally (without zero-padding) given by FOV/resolution
      Add 25% to matrix for "true resolution" for (e.g.) spiral
      Output data are gridded to a matrix 50% larger than this to mitigate gridding artifacts
    Eff MTX Z - number of pixels in the final image (Z), nominally (without zero-padding) given by FOV/resolution
      Add 25% to matrix for "true resolution" for (e.g.) stack of cones, spherical distributed spiral, FLORET
      Output data are gridded to a matrix 50% larger than this to mitigate gridding artifacts
    dx, dy, dz - for off-center FOV correction.  Specify number of pixels in each direction to shift (in image space)
                 prior to gridding.

      Note on Input dimensions: If coords is N dimensions, with the last used for the 2D/3D information,
                                  1) weights must have N-1 dimensions, of the same shape as corresponding coords
                                  2) data can have N-1 or more dimensions (of correct shape)
                                  3) If data has extra dimension (the first dimensions), data from each index
                                       in these dimensions are gridded using the same coords and weights

      Examples:  2D Spiral Gridding, 4-channel coil, 22 slices, 32 arms, 4056 points per interleaf
                     data are complex, 4 x 22 x 32 x 4056
                     coords are real,      22 x 32 x 4056 x 2
                     weights are real,     22 x 32 x 4056
                     Dims per Set widget is 2
                     Eff Mtx XY widget is 200
                     output data size is 4 x 22 x 300 x 300

                 3D Distributed Spiral Gridding, 8 coils, 320 arms, 4056 points per interleaf
                     data are complex, 8 x 320 x 4056
                     coords are real,      320 x 4056 x 3
                     weights are real,     320 x 4056
                     Dims per Set widget is 2
                     Eff Mtx XY widget is 160
                     Eff Mtx Z widget is 120
                     output data size is 8 x 180 x 240 x 240
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):

        # Widgets
        self.addWidget('Slider','Dims per Set',min=1,val=2)
        self.addWidget('SpinBox','Eff MTX XY', min=5, val=240)
        self.addWidget('SpinBox','Eff MTX Z',  min=5, val=240)
        self.addWidget('DoubleSpinBox','dx (pixels)', val=0.0)
        self.addWidget('DoubleSpinBox','dy (pixels)', val=0.0)
        self.addWidget('DoubleSpinBox','dz (pixels)', val=0.0)

        # IO Ports
        self.addInPort('data', 'NPYarray', dtype=[np.complex64, np.complex128],
                       obligation=gpi.OPTIONAL)
        self.addInPort('coords', 'NPYarray', dtype=[np.float64, np.float32],
                       obligation=gpi.REQUIRED)
        self.addInPort('weighting', 'NPYarray', dtype=[np.float32, np.float64],
                       obligation=gpi.REQUIRED)
        self.addInPort('params_in', 'DICT', obligation = gpi.OPTIONAL)
        self.addOutPort('out', 'NPYarray', dtype=[np.complex64, np.complex128])

    def validate(self):
        ''' DHW check if input data, coords and weight have the correct dimentions and sizes.
        '''

        data = self.getData('data')
        crds = self.getData('coords')
        wghts = self.getData('weighting')
        inparam = self.getData('params_in')

        if crds.shape[crds.ndim-1] not in [1,2,3]:
          self.log.warn("only 1-3 dimensional gridding implemented")
          return 1
        else:
          self.setAttr('Eff MTX Z', visible=crds.shape[-1]==3)

        self.setAttr('Dims per Set', max = crds.ndim-1)

        if data is not None:
          if data.ndim < crds.ndim - 1:
            self.log.warn("# of dimensions of data to small")
            return 1
          else:
            for i in range(crds.ndim-1):
              if data.shape[-i-1] != crds.shape[-i-2]:
                self.log.warn("sizes of data and cords don't match")
                return 1

        if wghts is not None:
          if wghts.ndim != crds.ndim - 1:
            self.log.warn("# of dimensions of weights must match crds")
            return 1
          else:
            for i in range(crds.ndim-1):
              if crds.shape[i] != wghts.shape[i]:
                self.log.warn("sizes of weights and coords don't match")
                return 1

        # Auto Matrix calculation: extra 25% assumes "true resolution"
        if (inparam is not None):       
          if 'sp_grd_mtx' in inparam:
            mtx_xy = int(inparam['sp_grd_mtx'])
            self.setAttr('Eff MTX XY', val = mtx_xy)
            self.setAttr('dx (pixels)', val=0)
            self.setAttr('dy (pixels)', val=0)
            self.setAttr('dz (pixels)', val=0)
                    
          else:
              self.log.warn("wrong header type")
              return 1



        return 0

    def compute(self):

        import numpy as np
        import gpi_core.gridding.grid as gd

        crds = np.float32(self.getData('coords'))
        wghts = self.getData('weighting')
        data = self.getData('data')
        dps = self.getVal('Dims per Set')
        mtx_xy = (3*self.getVal('Eff MTX XY')/2) # 1.5X OVERSAMPLE
        mtx_z  = (3*self.getVal('Eff MTX Z')/2) # 1.5X OVERSAMPLE
        dx = self.getVal('dx (pixels)')
        dy = self.getVal('dy (pixels)')
        dz = self.getVal('dz (pixels)')

        # Each gridded set will have npts points gridded onto it
        # There are separate coordinates for ncsets of different gridded units (lines, planes, volumes)
        # There are an additional ndsets of data for each ncset of gridded units
        crdshape = crds[...,0].shape
        maxi = crds.ndim - 2
        npts = 1
        for i in range(dps):
          npts *= crdshape[maxi-i]
        ncsets = crds[...,0].size//npts

        # Make data or reshape it
        if data is None:
          datshape = np.array(crds[...,0].shape)
          ndsets = 1
          data = np.ones((ndsets,ncsets,npts), dtype=np.complex64)
          in_dtype = data.dtype  # make the out-type the same as the in-type
        else:
          in_dtype = data.dtype  # make the out-type the same as the in-type
          datshape = np.array(data.shape)
          ndsets = data.size//crds[...,0].size
          # Reshape data to be 3 dimensional
          # force single precision
          data = np.reshape(data.astype(np.complex64),(ndsets,ncsets,npts))

        # Reshape crds to be 3 dimensional - # sets, # pts/set, and dimensionality (1-3)
        crds = np.reshape(crds.astype(np.float32),(ncsets,npts,crds.shape[-1]))

        # Make wghts or reshape it
        if wghts is None:
          wghts = np.ones((ncsets,npts), dtype=np.float32)
        else:
          # Reshape wghts to be 2 dimensional
          wghts = np.reshape(wghts.astype(np.float32),(ncsets,npts))

        # Dimensions for array to grid on
        if crds.shape[crds.ndim-1] == 1:
          outdim = np.array([mtx_xy],dtype=np.int64)
        if crds.shape[crds.ndim-1] == 2:
          outdim = np.array([mtx_xy,mtx_xy],dtype=np.int64)
        if crds.shape[crds.ndim-1] == 3:
          outdim = np.array([mtx_xy,mtx_xy,mtx_z],dtype=np.int64)

        outdim1 = outdim
        if crds.shape[crds.ndim-1] == 3: # For Distributed Spirals
            outdim1 = np.array([mtx_z,mtx_xy,mtx_xy],dtype=np.int64)

        outshape = np.append([ndsets*ncsets], outdim1)
        out = np.zeros(outshape,  dtype = in_dtype)

        # Grid it
        for i in range(ndsets):
          for j in range(ncsets):
            outset = gd.grid(crds[j,...],data[i,j,...],wghts[j,...],outdim,dx,dy,dz)
            out[i*ncsets+j,...] = outset.astype(in_dtype)

        # RESHAPE OUTPUT
        if datshape.size == dps:
          out = out[0,...]
        else:
          outshape = np.append(datshape[0:datshape.size-dps],outdim1)
          out = np.reshape(out,outshape)

        self.setData('out', out.astype(in_dtype))

        return(0)
