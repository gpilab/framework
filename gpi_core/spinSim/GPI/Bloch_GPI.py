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
# Date: 2013Jun18

import gpi
import numpy as np

class ExternalNode(gpi.NodeAPI):
    """A Bloch simulator designed to work with the Spyn-node and optional
    RFwaveforms-node input.  Bloch nodes can be cascaded to effectively build
    segments of a pulse sequence.

    The data are passed from the output of either the Spyn Module (the beginning) or
    the output of a Bloch module to the left output (M_in) of the next Bloch module

    INPUTS:
    M_in - spin data
    G_in - input gradient waveform - if 1 dimensional, this is used for all gradients
           if 2 dimensional, with the 2nd dimension 3, this is used for separate Gx, Gy, Gz waveforms 
           Waveform is linearly interpolated to match the duration of the Bloch module
           if not connected, gradients are all considered constant for Duration
    RF_in - input RF waveform - if 1 dimensional, this is used for RF magnitude
           Waveform is linearly interpolated to match the duration of the Bloch module
           if not connected, rf is considered constant for Duration
    Pars_in - accepts parameters to set other widgets (i.e. if external waveform is used

    OUTPUTS - spin data

    WIDGETS:
    Duration: duration of this particular part of the sequence
    Gx, Gy, Gz - amplitude of gradients.  If an external waveform is supplied, 
                 it is multiplied by these respective values
    RF Mag (uT) - amplitude of RF pulse. If an external waveform is supplied, 
                 it is multiplied by this value.  If RF Flip is set, RF Mag is adjusted to
                 give that flip at the center frequency.
    RF Flip (deg) - flip angle of RF pulse at the center frequency. 
                 If RF Mag is set, RF Flip is adjusted accordingly.
    RF Phase (deg) - phase of RF pulse
    Crusher Tc (ms) - this is used to simulate a crusher, although not too realistically.
                 The (Mx,My) component of all spins decay with an additional exp(-t/Tc) during
                 this module.  If Tc=0, Crusher is ignored.
    """

    def initUI(self):
        # Widgets
        self.addWidget('DoubleSpinBox', 'Duration (ms)', min=0.01, val=1.,decimals=3)
        self.addWidget('DoubleSpinBox', 'Gx (mT/m)', val=0.)
        self.addWidget('DoubleSpinBox', 'Gy (mT/m)', val=0.)
        self.addWidget('DoubleSpinBox', 'Gz (mT/m)', val=0.,decimals=3)
        self.addWidget('DoubleSpinBox', 'RF Mag (uT)', val=0.,decimals=2)
        self.addWidget('DoubleSpinBox', 'RF Flip (deg)', val=0.)
        self.addWidget('DoubleSpinBox', 'RF Phase (deg)', val=0.)
        self.addWidget('DoubleSpinBox', 'Crusher Tc (ms)', val=0.)
        self.addWidget('DoubleSpinBox', 'RF Talpha (ms)', val=0.)

        # IO Ports
        self.addInPort('M_in', 'NPYarray',obligation=gpi.REQUIRED)
        self.addInPort('G_in', 'NPYarray',obligation=gpi.OPTIONAL)
        self.addInPort('RF_in', 'NPYarray',ndim=1,obligation=gpi.OPTIONAL)
        self.addInPort('Pars_in', 'DICT',obligation=gpi.OPTIONAL)

        self.addOutPort('M_out', 'NPYarray')

    def validate(self):
        '''This function runs before compute() as a GPI_APPLOOP exec-type.
        Here, widgets (bounds, limits, etc...) can be modified to ensure they
        are correctly validated before the widget values are used in the
        compute() routine -where widgets are buffered and any modifications are
        applied after compute() runs.
        '''

        # New data
        m_in = self.getData('M_in')
        rf_in = self.getData('RF_in')
        g_in = self.getData('G_in')

        # Is g_in the right size?
        if g_in is not None:
          if g_in.ndim==2:
            if g_in.shape[1]!=3:
              self.log.warn("Bloch: g_in must be 1D or 2D with the 2nd dim = 3")
              return 1
          elif g_in.ndim > 2:
            self.log.warn("Bloch: g_in must be 1D or 2D with the 2nd dim = 3")
            return 1

        # read Parameter from RFwaveforms module if changed and available
        if 'Pars_in' in self.portEvents():
            param_dict = self.getData('Pars_in')
            if param_dict is not None:
                if 'Duration (ms)' in param_dict:
                    self.setAttr('Duration (ms)', val=param_dict['Duration (ms)'])
                if 'Gz (mT/m)' in param_dict:
                    self.setAttr('Gz (mT/m)', val=param_dict['Gz (mT/m)'])
                if 'RF Mag (uT)' in param_dict:
                    self.setAttr('RF Mag (uT)', val=param_dict['RF Mag (uT)'])
                if 'RF Flip (deg)' in param_dict:
                    self.setAttr('RF Flip (deg)', val=param_dict['RF Flip (deg)'])

        # Reconcile timing
        dtms = m_in[10,0,0,0,0,0,0,0,0,0,0]
        durval = max(1.,round(self.getVal('Duration (ms)')/dtms,0))*dtms
        self.setAttr('Duration (ms)',val=durval)

        # Find Area of rf pulse for flip at slice center
        if rf_in is not None:
          rf_ave = abs(np.average(rf_in))
        else:
          rf_ave = 1.;

        # Reconcile flip angle and rfmag
        gamma = m_in[11,0,0,0,0,0,0,0,0,0,0] 

        if 'RF Mag (uT)' in self.widgetEvents():
          rf_mag = self.getVal('RF Mag (uT)')
          rf_flip = 360.*gamma*rf_ave*durval*rf_mag/1000.
          self.setAttr('RF Flip (deg)',val=rf_flip)
        else:
          rf_flip = self.getVal('RF Flip (deg)')
          rf_mag = rf_flip/(360.*gamma*rf_ave*durval)*1000.
          self.setAttr('RF Mag (uT)',val=rf_mag)

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''

        # New data
        m_in = self.getData('M_in')
        g_in = self.getData('G_in')
        rf_in = self.getData('RF_in')

#Constants, per pixel
        m0 = m_in[0,0,:,:,:,:,:,:,:,:,:]
        r1 = m_in[1,0,:,:,:,:,:,:,:,:,:]
        r2 = m_in[2,0,:,:,:,:,:,:,:,:,:]
        vx = m_in[3,0,:,:,:,:,:,:,:,:,:]
        vy = m_in[4,0,:,:,:,:,:,:,:,:,:]
        vz = m_in[5,0,:,:,:,:,:,:,:,:,:]
        fq = m_in[6,0,:,:,:,:,:,:,:,:,:]
        dtms = m_in[10,0,0,0,0,0,0,0,0,0,0]
        gamma = m_in[11,0,0,0,0,0,0,0,0,0,0] 

#Starting values for this module are ending values from last module
        mx = m_in[0,-1,:,:,:,:,:,:,:,:,:]
        my = m_in[1,-1,:,:,:,:,:,:,:,:,:]
        mz = m_in[2,-1,:,:,:,:,:,:,:,:,:]
        x0 = m_in[3,-1,:,:,:,:,:,:,:,:,:]
        y0 = m_in[4,-1,:,:,:,:,:,:,:,:,:]
        z0 = m_in[5,-1,:,:,:,:,:,:,:,:,:]
        t0 = m_in[6,-1,:,:,:,:,:,:,:,:,:]

        t_bloch = self.getVal('Duration (ms)')

        # Some Initial Calcs
        odim = int(t_bloch/dtms)
        oshape = list(m_in.shape)
        oshape[1]=odim
        idim = int(1000.*dtms)
        newdat=np.zeros(tuple(oshape))
        n_iter = int(1000.*t_bloch)
        usec = 0.001 # in units of msec
        radspermT = 2.*np.pi*gamma*usec

        # Synthetic Crusher
        tc = self.getVal('Crusher Tc (ms)')
        if tc > 0:
          r2c = r2 + (1./tc)
        else:
          r2c = r2

        # Time constant for rf train
        talpha = self.getVal('RF Talpha (ms)')
        if talpha > 0:
          exp_alpha = np.exp(-usec/talpha)
        else:
          exp_alpha = 1.

        expt1=np.exp(-r1*usec)
        expt2=np.exp(-r2c*usec)
        mz0 = m0*(1.-expt1)
        db0 = fq/gamma

        ######################
        # Create Gx,Gy,Gz array
        ######################
        if g_in is not None:
          gdim = list(g_in.shape)
          x_in  = np.linspace(0.,1.,num=gdim[0])
          x_out = np.linspace(0.,1.,num=n_iter)
          if g_in.ndim==1:
            g_out = np.interp(x_out,x_in,g_in)
            gx = self.getVal('Gx (mT/m)')*g_out
            gy = self.getVal('Gy (mT/m)')*g_out
            gz = self.getVal('Gz (mT/m)')*g_out
          elif g_in.ndim==2 and g_in.shape[1]==3:
            gx = self.getVal('Gx (mT/m)')*np.interp(x_out,x_in,g_in[:,0])
            gy = self.getVal('Gy (mT/m)')*np.interp(x_out,x_in,g_in[:,1])
            gz = self.getVal('Gz (mT/m)')*np.interp(x_out,x_in,g_in[:,2])
        else:
          g_out = np.ones(n_iter)
          gx = self.getVal('Gx (mT/m)')*g_out
          gy = self.getVal('Gy (mT/m)')*g_out
          gz = self.getVal('Gz (mT/m)')*g_out

        ######################
        # Create RFx, RFy arrays
        ######################
        crfph = np.cos(np.radians(self.getVal('RF Phase (deg)')))
        srfph = np.sin(np.radians(self.getVal('RF Phase (deg)')))
        rfm = 0.001 * self.getVal('RF Mag (uT)')
        if rf_in is not None:
          rfdim = list(rf_in.shape)
          x_in  = np.linspace(0.,1.,num=rfdim[0])
          x_out = np.linspace(0.,1.,num=n_iter)

          rf_out = np.interp(x_out,x_in,rf_in)
          rfx = rfm*(crfph*np.real(rf_out)-srfph*np.imag(rf_out))
          rfy = rfm*(crfph*np.imag(rf_out)+srfph*np.real(rf_out))
        else:
          rf_out = np.ones(n_iter)
          rfx = crfph*rfm*rf_out
          rfy = srfph*rfm*rf_out

        ######################
        # Now iterate through time
        ######################
        # record data in newdat for each index in outer loop
        # inner loop interval is 1 usec
        ######################

        for outer in range(0,odim): 
          for inner in range(0,idim): 
            i = outer*idim+inner
            time = float(i+1)*usec
            x = x0 + time*vx
            y = y0 + time*vy
            z = z0 + time*vz

            xph = radspermT*rfx[i] #radians to rotate about x
            yph = radspermT*rfy[i] #radians to rotate about y
            zph = radspermT*(x*gx[i]+y*gy[i]+z*gz[i] + db0) #radians to rotate about z

            mx,my,mz = self.rotate(mx,my,mz,xph,yph,zph)
            mx = mx*expt2
            my = my*expt2
            mz = mz0 + (exp_alpha*expt1)*mz

          newdat[0,outer,:,:,:,:,:,:,:,:,:] = mx
          newdat[1,outer,:,:,:,:,:,:,:,:,:] = my
          newdat[2,outer,:,:,:,:,:,:,:,:,:] = mz
          newdat[3,outer,:,:,:,:,:,:,:,:,:] = x
          newdat[4,outer,:,:,:,:,:,:,:,:,:] = y
          newdat[5,outer,:,:,:,:,:,:,:,:,:] = z
          newdat[6,outer,:,:,:,:,:,:,:,:,:] = t0+time
          newdat[7,outer,:,:,:,:,:,:,:,:,:] = gx[i]
          newdat[8,outer,:,:,:,:,:,:,:,:,:] = gy[i]
          newdat[9,outer,:,:,:,:,:,:,:,:,:] = gz[i]
          newdat[10,outer,:,:,:,:,:,:,:,:,:] = rfx[i]
          newdat[11,outer,:,:,:,:,:,:,:,:,:] = rfy[i]
          newdat[12,outer,:,:,:,:,:,:,:,:,:] = tc

        m_out=np.concatenate((m_in,newdat),axis=1)

        self.setData('M_out', m_out)

        return 0

    ######################
    def rotate(self, rx, ry, rz, px, py, pz):
    ######################
# R = (rx, ry, rz) = (mx, my, mz)
# P = (px, py, pz)
# Rotate R about P, by |P| radians
#
# R1 is the projection of R on P, which does not rotate
# R2 is the residue of R which is perpendicular to P
# R3 and R4 are the vectors of the rotated R2 which are
#           parallel and perpendicular to R2, respectively
#
# R1 = P (P dot R)/(|P|**2)
# R2 = R - R1
# R3 = R2 Cos(|P|)
# R4 = (P x R2) Sin(|P|) / |P|
#
# R' = R1+R3+R4

      psqu = px*px + py*py + pz*pz
      if (psqu > 0).any():
        pmag = np.sqrt(psqu)

        # Need to mask, to avoid div_by_0
        pzero = np.zeros(psqu.shape)

        pdotr = px*rx + py*ry + pz*rz
        r1norm = np.where(psqu,pdotr/psqu,pzero)
        cp = np.cos(pmag)
        spn = np.where(pmag,np.sin(pmag)/pmag,pzero)

        r1x = px*r1norm
        r1y = py*r1norm
        r1z = pz*r1norm

        r2x = rx-r1x
        r2y = ry-r1y
        r2z = rz-r1z

        r3x = r2x*cp
        r3y = r2y*cp
        r3z = r2z*cp

        r4x = (py*r2z - pz*r2y)*spn
        r4y = (pz*r2x - px*r2z)*spn
        r4z = (px*r2y - py*r2x)*spn

        rx = r1x+r3x+r4x
        ry = r1y+r3y+r4y
        rz = r1z+r3z+r4z

      return rx,ry,rz

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
