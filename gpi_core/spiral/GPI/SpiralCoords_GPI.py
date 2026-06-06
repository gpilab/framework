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


class ExternalNode(gpi.NodeAPI):

    """Module to generate the gradient waveforms for a desired k-space waveform.  Uses the core file bnispiralgen.c
    If using this module to generate k-space coordinates for collected data, it is crucial that the code be identical
    with that used in the methods code (hence we keep bnispiralgen.c as a standalone file)

    INPUT: dictionary from (e.g.) ReadPhilips with all of the parameters used to collect data.  If input data are present,
           parameters cannot be changed.  If not, parameters may be changed freely.

    OUTPUTS:
    crds_out - output coordinates: the last dimension is either 2 (kx/ky) or 3 (kx/ky/kz) for 2D and 3D trajectories.  See
               discussion of "true resolution" below for more details about the scaling.  Dwell time specified by AD dwell time widget.
    grd_out - gradient waveforms used to produce crds_out.  Fixed to dwell time of 6.4 us.

    WIDGETS: most widgets self-explanatory, here are a few clarifications:
    stype - ARCH is standard 2D spiral
            CYL DST is a cylindrical distributed spiral
            SPH DST is a cylindrical distributed spiral
            FLORET is FLORET...
    # of spiral arms - allows floating point entry
                       for ARCH this is rounded to integer
                       for CYL, SPH DST and FLORET, which share arms across ky and kz, this is the effective arms per plane
                       and can be a floating point number (giving greater flexibility in choosing the total number of arms vs.
                       readout duration)
    usamp st (0-1) - the relative value of kr at which undersampling begins (0 at the center, 1 at the edge of collected k-space)
                     the samples are collected at the nyquist limit (1/FOV X-Y) prior to that
    usamp end (0-1) - the relative value of kr at which undersampling ends
                     the samples are collected at the R times the nyquist limit (1/FOV X-Y) prior to that
    max underample - R, i.e. the undersampling relative to (1/FOV X-Y) after kr exceeds usamp end
    ustype - determines the progression of radial undersampling from usamp st to usamp end as linear, quadratic, or hanning
    Max G Freq - limits the maximum frequency of the gradient waveform during the spiral readout.  If set to 0, there is no limit
    T2 Match - allows one to exponentially change the radial undersampling with time to match T2* decay, for optimal, T2*-matched, SNR
    Sloppy Sp. Per - changes the characteristic of the sloppy spiral, if desired (see Miki Lustig's perturbed spiral paper).  0 turns off.
    gtype - amount of gradient to output
        SPIRAL ONLY - the gradient waveform during the readout only
        G -> 0 - Same as above, but with gradient rampdown
        M0 -> 0 - Same as above, but with k-space rewinder
        M1 -> 0 - Same as above, but with gradient first moment compensation
    spinout - controls spiral in, out, etc.
        OUT - generate spiral-out waveform
        IN  - generate spiral-in waveform
        INOUT 180R - generate single waveform with spiral-in followed by spiral-out on a trajectory rotated by 180 degrees
        INOUT SAME - generate single waveform with spiral-in followed by spiral-out on the same trajectory

    ****************************************
    *** The concept of "true resolution" ***
    k-space data are typically normalized, for the gridding process, to values between -0.5 and 0.5
    For spiral data (which measure circular k-space) to have the same resolution as Cartesian (square k-space)
    they must measure a diameter of 2/sqrt(pi) ~ 1.13 larger than conventional k-space limits (so that the area of the circle
    equals the area of the square).  k-space coordinates, therefore, are multiplied by 0.8, so that there range of
    0.8*2/sqrt(pi) = 0.903, or -0.451 to +0.451, fits within the gridded space.  The resulting image, with no further
    zero-padding, will have pixels that are 0.8 times smaller than the requested resolution, with a matrix 25% larger in each
    dimension.  This is a semi-complicated way of making sure that this works routinely, and is referred to by the authors
    as "true resolution".

    A similar logic is used for measuring data in a sphere, but the diameter must be the cubed root of (6/pi), or 1.24, the
    side of an equivalent cube for equal volumes.  k-space coordinates then span 0.8*(6/pi)^(1/3) = 0.993 of the unit width of
    gridded k-space.
    *****************************************
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):

        # Widgets
        self.addWidget('PushButton', 'compute', toggle=True)
        self.addWidget('TextBox', 'Info:')

        self.addWidget('DoubleSpinBox', 'AD dwell time (us)',
                       val=1.0, min=0.1, decimals=6)
        self.addWidget('DoubleSpinBox', 'x delay (us)',
                       val=0.0, min=-100.0, max=100.0)
        self.addWidget('DoubleSpinBox', 'y delay (us)',
                       val=0.0, min=-100.0, max=100.0)
        self.addWidget('DoubleSpinBox', 'z delay (us)',
                       val=0.0, min=-100.0, max=100.0)

        self.addWidget('DoubleSpinBox', 'MaxSlw (mT/m/ms)',
                       val=150.0, min=0.01, decimals=6)
        self.addWidget('DoubleSpinBox', 'MaxGrd (mT/m)',
                       val=40.0, min=0.01, decimals=6)
        self.addWidget('DoubleSpinBox', 'Gam (kHz/mT)',
                       val=42.577, min=0.01, decimals=6)

        self.addWidget('DoubleSpinBox', 'Fov X-Y (cm)',
                       val=24.0, min=0.1, decimals=6)
        self.addWidget('DoubleSpinBox', 'Fov Z (cm)',
                       val=24.0, min=0.1, decimals=6)
        self.addWidget('DoubleSpinBox', 'ImgRes X-Y (cm)',
                       val=0.2, min=0.01, singlestep=0.01, decimals=6)
        self.addWidget('DoubleSpinBox', 'ImgRes Z (cm)', val=0.2,
                       min=0.01, singlestep=0.01, decimals=6)

        self.addWidget('ExclusivePushButtons', 'stype',
                       buttons=['ARCH', 'CYL DST', 'SPH DST', 'FLORET'], val=0)
        self.addWidget('DoubleSpinBox', 'Taper', val=0.0, min=0.0, max = 1.0)
        self.addWidget('DoubleSpinBox', '# of Spiral Arms', val=16.0, min=0.0)

        self.addWidget('SpinBox', '# of Hubs', val=3, min=1, max=3)
        self.addWidget('DoubleSpinBox', 'Alpha0', val=45.0, min=0.0, max=90.0)
        self.addWidget('PushButton', 'FLORET Rebin', toggle=True)

        self.addWidget('DoubleSpinBox', 'usamp st (0 - 1)',
                       val=0.0, min=0.0, max=1.0, singlestep=0.01)
        self.addWidget('DoubleSpinBox', 'usamp end (0 - 1)',
                       val=1.0, min=0.0, max=1.0, singlestep=0.01)
        self.addWidget('DoubleSpinBox', 'max undersample',
                       val=1.0, min=0.0, max=100.0)
        self.addWidget('ExclusivePushButtons', 'ustype',
                       buttons=['LINEAR', 'QUAD', 'HANNING'], val=0)

        self.addWidget('DoubleSpinBox', 'Max G Freq (kHz)', val=0.0, min=0.0)
        self.addWidget('DoubleSpinBox', 'T2 Match (ms)', val=0.0, min=0.0)

        self.addWidget('DoubleSpinBox',
                       'Sloppy Sp. Per (0:off)', val=0.0, min=0.0)

        self.addWidget('ExclusivePushButtons', 'gtype',
                       buttons=['SPIRAL ONLY', 'G -> 0', 'M0 -> 0', 'M1 -> 0', 'Fast Spoil'], val=2)

        self.addWidget('ExclusivePushButtons', 'spinout',
                       buttons=['OUT', 'IN', 'INOUT 180R', 'INOUT SAME', 'INOUT ROT2', 'INOUT SAME2'], val=0)
        self.addWidget('SpinBox', 'Num Calibration Points', val=0, min=0, max=512)

        # IO Ports
        self.addInPort('params_in', 'DICT', obligation=gpi.OPTIONAL)
        self.addInPort('arm_0', 'NPYarray', obligation=gpi.OPTIONAL)
        self.addOutPort('crds_out', 'NPYarray')
        self.addOutPort('grd_out', 'NPYarray')
        self.addOutPort('kmag_trace', 'NPYarray')

    def validate(self):

        inparam = self.getData('params_in')

        if (inparam is not None):

            if 'headerType' in inparam:

                # check if the header is for spiral
                if inparam['headerType'] != 'BNIspiral':
                    self.log.warn("wrong header type")
                    return 1

            else:
                # if there is no header type, then its also the wrong type
                self.log.warn("wrong header type")
                return 1

            self.setAttr('AD dwell time (us)', val=1000. *
                         float(inparam['spDWELL'][0]))

            self.setAttr('MaxSlw (mT/m/ms)',
                         val=float(inparam['spSLEWMAX'][0]))
            self.setAttr('MaxGrd (mT/m)',
                         val=float(inparam['spGMAX'][0]))
            self.setAttr('Gam (kHz/mT)',
                         val=float(inparam['spGAMMA'][0]))

            self.setAttr('Fov X-Y (cm)',
                         val=100. * float(inparam['spFOVXY'][0]))
            self.setAttr('Fov Z (cm)',
                         val=100. * float(inparam['spFOVZ'][0]))
            self.setAttr('ImgRes X-Y (cm)',    val=100. *
                         float(inparam['spRESXY'][0]))
            self.setAttr('ImgRes Z (cm)',
                         val=100. * float(inparam['spRESZ'][0]))

            self.setAttr('stype',
                         val=int(float(inparam['spSTYPE'][0])))
            self.setAttr('# of Spiral Arms',
                         val=float(inparam['spARMS'][0]))

            self.setAttr('usamp st (0 - 1)',
                         val=float(inparam['spUS0'][0]))
            self.setAttr('usamp end (0 - 1)',
                         val=float(inparam['spUS1'][0]))
            self.setAttr('max undersample',
                         val=float(inparam['spUSR'][0]))
            self.setAttr('ustype',
                         val=int(float(inparam['spUSTYPE'][0])))
            self.setAttr('gtype',
                         val=int(float(inparam['spGTYPE'][0])))
            if 'spMGFRQ' in inparam:
                self.setAttr('Max G Freq (kHz)',
                             val=(float(inparam['spMGFRQ'][0])))

            if 'spT2MATCH' in inparam:
                self.setAttr('T2 Match (ms)',
                             val=(float(inparam['spT2MATCH'][0])))

            spinout = int(inparam['spINOUT_ON'][0])
            spinout += int(inparam['spINOUT_OPT'][0])
            self.setAttr('spinout',      val=spinout)

            if spinout > 1: # in-out
                self.setAttr('Num Calibration Points', visible=True)
                if 'spEXTRA_GRAD_PNT' in inparam:
                    self.setAttr('Num Calibration Points', val=int(0.5*float(inparam['spEXTRA_GRAD_PNT'][0])))
            else:
                self.setAttr('Num Calibration Points', visible=False)

            # FLORET params
            if 'spHUBS' in inparam:
                hubs = int(float(inparam['spHUBS'][0]))
            else:
                hubs = self.getVal('# of Hubs')
            if 'spALPHA0' in inparam:
                alpha0 = float(inparam['spALPHA0'][0])
            else:
                alpha0 = self.getVal('Alpha0')
            if 'spFLORETbin' in inparam:
                rebin = float(inparam['spFLORETbin'][0])
            else:
                rebin = self.getVal('FLORET Rebin')
            if self.getVal('stype') == 3:
                self.setAttr('# of Hubs', visible=True, val=hubs)
                self.setAttr('Alpha0', visible=True, val=alpha0)
                self.setAttr('FLORET Rebin', visible=True, val=rebin)
            else:
                self.setAttr('# of Hubs', visible=False)
                self.setAttr('Alpha0', visible=False)
                self.setAttr('FLORET Rebin', visible=False, val=0)

        self.setAttr('Taper', visible=(self.getVal('stype') == 1)) # CDST

        if self.getVal('stype') == 3:
            rebin = self.getVal('FLORET Rebin')
            self.setAttr('# of Hubs', visible=True)
            self.setAttr('Alpha0', visible=True)
            self.setAttr('FLORET Rebin', visible=True, val=rebin)
        else:
            self.setAttr('# of Hubs', visible=False)
            self.setAttr('Alpha0', visible=False)
            self.setAttr('FLORET Rebin', visible=False, val=0)

    def compute(self):

        import numpy as np

        arm_0 = self.getData('arm_0')
        # arm_0 = np.insert(np.diff(arm_0,0),0,0)

        # convert units to ms, kHz, m, mT
        dwell = 0.001 * self.getVal('AD dwell time (us)')
        xdely = 0.001 * self.getVal('x delay (us)')
        ydely = 0.001 * self.getVal('y delay (us)')
        zdely = 0.001 * self.getVal('z delay (us)')

        mslew = self.getVal('MaxSlw (mT/m/ms)')
        mgrad = self.getVal('MaxGrd (mT/m)')
        gamma = self.getVal('Gam (kHz/mT)')

        fovxy = 0.01 * self.getVal('Fov X-Y (cm)')
        fovz = 0.01 * self.getVal('Fov Z (cm)')
        resxy = 0.01 * self.getVal('ImgRes X-Y (cm)')
        resz = 0.01 * self.getVal('ImgRes Z (cm)')

        stype = self.getVal('stype')
        narms = self.getVal('# of Spiral Arms')
        taper = self.getVal('Taper')

        try:
            hubs = self.getVal('# of Hubs')
        except:
            hubs = 3

        try:
            alpha0 = np.pi * self.getVal('Alpha0') / 180.0
        except:
            alpha0 = 0.25 * np.pi

        try:
            rebin = self.getVal('FLORET Rebin')
            if rebin:
                res_sphere = np.power(np.pi / 6, (1./3.))
                nspiral = round(narms * alpha0 * (fovz / (resz * res_sphere)))
                binfact = int(round(nspiral / 34.0))
                nspiral = int(34 * binfact)
                narms = nspiral / (alpha0 * (fovz / (resz * res_sphere)))
                self.setAttr('# of Spiral Arms', val=narms)
        except:
            rebin = 0

        us_0 = self.getVal('usamp st (0 - 1)')
        us_1 = self.getVal('usamp end (0 - 1)')
        us_r = self.getVal('max undersample')
        utype = self.getVal('ustype')

        mgfrq = self.getVal('Max G Freq (kHz)')
        t2mch = self.getVal('T2 Match (ms)')

        slper = self.getVal('Sloppy Sp. Per (0:off)')
        gtype = self.getVal('gtype')
        spinout = self.getVal('spinout')
        if spinout > 1:
            numCalPnts = self.getVal('Num Calibration Points')
        else:
            numCalPnts = 0


        # read num of data points from parameter txt file
        numREADPTS = 0
        inparam = self.getData('params_in')
        if (inparam is not None):
            if 'spREADPTS' in inparam:
                numREADPTS = int(float(inparam['spREADPTS'][0]))

        if self.getVal('compute'):

            # import in thread to save namespace
            import gpi_core.spiral.spiral as sp
            if stype == 0:
                zdely = 0.0

            # determine k-space coordinates based on input of first arm
            # TODO: doesn't handle spinout or FLORET rebinning (RKR)
            if arm_0 is not None:
                npts = arm_0.shape[0]
                crds_out = np.zeros((hubs,narms,npts,3))

                # goldangle = np.pi*(3-np.sqrt(5))
                # goldangle = 137.508*np.pi/180.
                goldangle = 137.508*3.141592653589793/180.
                if stype == 0: # arch
                    for arm in range(np.int(narms)):
                        beta = -arm*2*np.pi/narms
                        crds_out[0,arm,:,0] = np.cos(beta)*arm_0[:,0] - np.sin(beta)*arm_0[:,1]
                        crds_out[0,arm,:,1] = np.cos(beta)*arm_0[:,1] + np.sin(beta)*arm_0[:,0]

                elif stype == 1: # cylindrical distributed spirals
                    for arm in range(np.int(narms)):
                        beta = -arm*goldangle
                        crds_out[0,arm,:,0] = np.cos(beta)*arm_0[:,0] - np.sin(beta)*arm_0[:,1]
                        crds_out[0,arm,:,1] = np.cos(beta)*arm_0[:,1] + np.sin(beta)*arm_0[:,0]
                        crds_out[0,arm,:,2] = -(2*arm/narms - 1)*arm_0[:,2]

                elif stype == 2: # spherical distributed spirals
                    for arm in range(np.int(narms)):
                        beta = -arm*goldangle
                        crds_out[0,arm,:,0] = np.cos(beta)*arm_0[:,0] - np.sin(beta)*arm_0[:,1]
                        crds_out[0,arm,:,1] = np.cos(beta)*arm_0[:,1] + np.sin(beta)*arm_0[:,0]
                        crds_out[0,arm,:,2] = -(2*arm/narms - 1)*arm_0[:,2]

                elif stype == 3: # FLORET
                    for arm in range(np.int(narms)):
                        beta  = -arm*goldangle
                        alpha = -alpha0 + arm/narms*alpha0*2.
                        crds_out[0,arm,:,0] = np.cos(alpha)*(np.cos(beta)*arm_0[:,0] - np.sin(beta)*arm_0[:,1])/np.cos(-alpha0)
                        crds_out[0,arm,:,1] = np.cos(alpha)*(np.cos(beta)*arm_0[:,1] + np.sin(beta)*arm_0[:,0])/np.cos(-alpha0) # OK
                        crds_out[0,arm,:,2] = np.sin(alpha)*arm_0[:,2]/np.sin(-alpha0)

                    if not (xdely == ydely == zdely):
                        self.log.warn("FLORET trajectory calculation based on input of first arm can not account for anisotropic gradient delays!")

                    if hubs > 1:
                        crds_out[1,:,:,0] = crds_out[0,:,:,1] # OK
                        crds_out[1,:,:,1] = -crds_out[0,:,:,2]
                        crds_out[1,:,:,2] = -crds_out[0,:,:,0]
                    if hubs > 2:
                        crds_out[2,:,:,0] = crds_out[0,:,:,2]
                        crds_out[2,:,:,1] = crds_out[0,:,:,1] # OK
                        crds_out[2,:,:,2] = -crds_out[0,:,:,0]

                else:
                    pass

                self.log.warn("True gradient waveform output not (yet) implemented for calculation based on initial spiral arm!")
                grd_out = np.diff(crds_out, axis=-2)
            else:
                grd_out, crds_out = sp.coords(
                    dwell, xdely, ydely, zdely, mslew, mgrad, gamma, fovxy, fovz,
                    resxy, resz, stype, narms, taper, hubs, alpha0, rebin, us_0, us_1, us_r,
                    utype, mgfrq, t2mch, slper, gtype, spinout, numCalPnts)

            # Report Back to User
            nsamp = np.array(crds_out.shape)[2]
            # match data points from parameter file or real data
            if (numREADPTS > 0) and (nsamp > numREADPTS):
                ndim = np.array(crds_out.shape)[-1]
                crds_out = crds_out[..., 0:numREADPTS, 0:ndim]
                nsamp = numREADPTS

            ntrs = np.array(crds_out.shape)[0] * np.array(crds_out.shape)[1]
            # For Philips grad, assume PHGRAST = 0.0064 ms
            tgrad = 0.0064 * np.array(grd_out.shape)[1]
            smp = "Samples: " + str(nsamp) + "\n"
            tau = "Tau (ms): " + str(dwell * nsamp) + "\n"
            tgr = "TGrad (ms): " + str(tgrad) + "\n"
            trs = "Total interleaves: " + str(ntrs)
            info = smp + tau + tgr + trs
            self.setAttr('Info:', val=info)

            # if ARCH set 2d spiral cords out DHW
            if stype == 0:  # ARCH
                crds_out = crds_out[0, ..., 0:2]
                grd_out = grd_out[..., 0:2]
            elif stype != 3:  # FLORET
                crds_out = crds_out[0, ...]

            self.setData('crds_out', crds_out)
            self.setData('grd_out', grd_out)
            self.setData('kmag_trace', np.sqrt(np.sum(crds_out[0,...]**2, axis=-1)))

        return(0)
