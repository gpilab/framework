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
# Date: 2020Oct

import gpi

class ExternalNode(gpi.NodeAPI):

    """Module to generate the gradient waveforms for a desired k-space
    waveform. Uses the core files spiralgencf_gen.c and spiralgencf_fill.cpp
    
    INPUTS:
    GIRF_in - (optional) gradient impulse response function for gradient preconditioning

    OUTPUTS:
    crds_out - output coordinates: the last dimension is 2 (kx/ky).
    grd_out - gradient waveforms used to produce crds_out.  Dwell time is SPGRAST

    WIDGETS: most widgets self-explanatory, here are a few clarifications:
    min undersample - R, i.e. the undersampling relative to (1/FOV) before
        kr reaches usamp st
    max undersample - R, i.e. the undersampling relative to (1/FOV) after
        kr exceeds usamp end
    usamp st (0-1) - the relative value of kr at which undersampling begins (0
        at the center, 1 at the edge of collected k-space) the samples are
        collected at the nyquist limit (1/FOV) prior to that
    usamp end (0-1) - the relative value of kr at which undersampling ends
        the samples are collected at the R times the nyquist limit (1/FOV)
        prior to that
    Max G Freq - limits the maximum frequency of the gradient waveform during
        the spiral readout. If set to 0, there is no limit (default minimum is 0.5 kHz)
    Start Window - time for rounding enforced when starting
    Corner Window - an angle determining the rounding enforced when
        transitioning between (freq, slew,grad) limits
    spinout - controls spiral in, out, etc.
        OUT - generate spiral-out waveform
        IN  - generate spiral-in waveform
        OUT180 - generate spiral-out waveform and negate the waveform

    ****************************************
    *** The concept of "true resolution" ***
    k-space data are typically normalized, for the gridding process, to values
    between -0.5 and 0.5 For spiral data (which measure circular k-space) to
    have the same resolution as Cartesian (square k-space) they must measure a
    diameter of 2/sqrt(pi) ~ 1.13 larger than conventional k-space limits (so
    that the area of the circle equals the area of the square).  k-space
    coordinates, therefore, are multiplied by 0.8, so that their range of
    0.8*2/sqrt(pi) = 0.903, or -0.451 to +0.451, fits within the gridded space.
    The resulting image, with no further zero-padding, will have pixels that
    are 0.8 times smaller than the requested resolution, with a matrix 25%
    larger in each dimension.  This is a semi-complicated way of making sure
    that this works routinely, and is referred to by the authors as "true
    resolution".
    *****************************************
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):

        import numpy as np

        # Widgets
        self.addWidget('PushButton', 'compute', toggle=True)
        self.addWidget('TextBox', 'Info:')

        self.addWidget('DoubleSpinBox', 'FOV (cm)',
                       val=24.0, min=0.1, decimals=6)
        self.addWidget('DoubleSpinBox', 'Res (mm)',
                       val=0.8, min=0.1, singlestep=0.1, decimals=5)
        self.addWidget('SpinBox', '# of Spiral Arms', val=16, min=1)

        self.addWidget('ExclusivePushButtons', 'spinout',
                       buttons=['OUT', 'IN', 'OUT180'],val=0)

        self.addWidget('DoubleSpinBox', 'AD dwell time (us)',
                       val=1.0, min=0.1, decimals=6)
        self.addWidget('DoubleSpinBox', 'MaxSlw (mT/m/ms)',
                       val=150.0, min=0.01, decimals=6)
        self.addWidget('DoubleSpinBox', 'MaxGrd (mT/m)',
                       val=40.0, min=0.01, decimals=6)

        self.addWidget('DoubleSpinBox', 'min undersample',
                       val=1.0, min=0.0, max=100.0)
        self.addWidget('DoubleSpinBox', 'max undersample',
                       val=1.0, min=0.0, max=100.0)
        self.addWidget('DoubleSpinBox', 'usamp st (0 - 1)',
                       val=0.0, min=0.0, max=1.0, singlestep=0.01)
        self.addWidget('DoubleSpinBox', 'usamp end (0 - 1)',
                       val=1.0, min=0.0, max=1.0, singlestep=0.01)

        self.addWidget('PushButton', 'Precompensate', toggle=True, val=1)
        self.addWidget('PushButton', 'Precondition', toggle=True, val=1)

        self.addWidget('DoubleSpinBox', 'Max G Freq (kHz)', val=1.0, min=0.5, max=20.)
        self.addWidget('DoubleSpinBox', 'Start Window (us)', val=200.0, min=0.0)
        self.addWidget('DoubleSpinBox', 'End Window (us)', val=100.0, min=0.0)
        self.addWidget('DoubleSpinBox', 'Corner Window (cycles)', val=0.5, min=0.0)

        self.addWidget('DoubleSpinBox', 'TrueRes Factor', val=1.0,
                       min=0.0, max=1.0)

        self.addWidget('DoubleSpinBox', 'x delay (us)',
                       val=0.0, min=-100.0, max=100.0, visible = False)
        self.addWidget('DoubleSpinBox', 'y delay (us)',
                       val=0.0, min=-100.0, max=100.0, visible = False)

        self.addWidget('DoubleSpinBox', 'Gam (kHz/mT)',
                       val=42.577, min=0.01, decimals=6, visible = False) # hide this until we need it

        # IO Ports
        self.addInPort('GIRF_in', 'NPYarray',dtype=[np.float32,np.float64],ndim=1,obligation=gpi.OPTIONAL)
        self.addOutPort('crds_out', 'NPYarray')
        self.addOutPort('grd_out', 'NPYarray')
        self.addOutPort('gtf_out', 'NPYarray')

    def compute(self):

        import numpy as np

        # convert units to ms, kHz, m, mT
        dwell = 0.001 * self.getVal('AD dwell time (us)')
        xdely = 0.001 * self.getVal('x delay (us)')
        ydely = 0.001 * self.getVal('y delay (us)')

        mslew = self.getVal('MaxSlw (mT/m/ms)')
        mgrad = self.getVal('MaxGrd (mT/m)')
        gamma = self.getVal('Gam (kHz/mT)')

        fov = 0.01 * self.getVal('FOV (cm)')

        narms = float(self.getVal('# of Spiral Arms'))

        trures_fac = self.getVal('TrueRes Factor')
        trures_acq = trures_fac * np.sqrt(np.pi)/2 + 1 - trures_fac

        res = 0.001 * self.getVal('Res (mm)')

        us_0 = self.getVal('usamp st (0 - 1)')
        us_1 = self.getVal('usamp end (0 - 1)')
        us_r0 = self.getVal('min undersample')
        us_r = self.getVal('max undersample')

        precomp = self.getVal('Precompensate')
        precond = self.getVal('Precondition')

        mgfrq = self.getVal('Max G Freq (kHz)')
        start_win = 0.001*self.getVal('Start Window (us)') # change to ms
        end_win = 0.001*self.getVal('End Window (us)') # change to ms
        corner_win = 2.*np.pi*self.getVal('Corner Window (cycles)') # change to radians

        spinout = self.getVal('spinout')

        if self.getVal('compute'):

            girf = self.getData('GIRF_in')
            if girf is not None:
              # The first point should not be 0
              while girf[0] == 0:
                girf = girf[1:]
              # normalize to have unit area, so DC part of MTF is 1
              girf = np.float64(girf)/np.sum(np.float64(girf))
            else:
              # Make it a delta function
              girf = np.float64(np.array([1.,0.]))

            gtf_res = 0.05 # spectral resolution in kHz
            spgrast = 0.005 # gradient raster in ms
            # gtf_len*spgrast = 1/gtf_res
            # force gtf_len to be even
            gtf_len = 2*int(0.5/(gtf_res*spgrast))

            gtf = np.absolute(np.fft.fft(np.pad(girf,(0,gtf_len-girf.shape[0]))))

            # import in thread to save namespace
            # spiralgencf corresponds to spiralgencf_PyMOD.cpp
            import gpi_core.spiral.spiralgencf as sp

            print("end win",end_win)
            grd_out, crds_out = sp.coords(
                girf,gtf,dwell, xdely, ydely, mslew, mgrad, gamma,
                fov, res, narms,
                us_0, us_1, us_r0, us_r,
                mgfrq, precomp, precond, start_win, end_win, corner_win, spinout,
                trures_acq)

            # Report Back to User
            nsamp = np.array(crds_out.shape)[-2]

            spgrast = 0.005 # Gradient raster time in ms

            smp = "Samples: " + str(nsamp) + "\n"
            tau = "Tau (ms): " + str(dwell * nsamp) + "\n"
            tgrad = spgrast * np.array(grd_out.shape)[1]
            tgr = "TGrad (ms): " + str(tgrad) + "\n"
            info = smp + tau + tgr
            self.setAttr('Info:', val=info)

            grd_out = grd_out[..., 0:2]

            self.setData('crds_out', crds_out)
            self.setData('grd_out', grd_out)
            self.setData('gtf_out', gtf)

        return(0)
