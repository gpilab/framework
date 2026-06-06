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
# Date: 2013Jun18

import gpi
import numpy as np

class ExternalNode(gpi.NodeAPI):
    """Reformats magnetization profiles defined in Spyn and Bloch nodes for
    plotting in 1D viewer/plotter nodes.

    INPUT: data from Bloch or Spyn node

    OUTPUT: data to plot (typically via Matplotlib)

    WIDGETS:
    M display - select which values to display
                (Mx, My, Mz, Mt=sqrt(mx^2+my^2), |M| = sqrt(mx^2+my^2+mz^2)
                selecting multiple buttons will produce multiple graphs
    Average Across: for each dimension (e.g. T1, T2, etc.), the magnetization can be averaged across that dimension
    X Axis - the independent variable by which to plot on the abscissa
             (cannot be a dimension that has been averaged across)
    (T,T1,T2,FQ,...) Index -
       for every dimension that has length > 1, is not averaged across, and is not used as the X Axis, there is an
       slider to indicate which index along that dimension to use.
    """


    def initUI(self):
        # Widgets
        self.addWidget('NonExclusivePushButtons', 'M display',
                       buttons=['Mx','My','Mz','Mt','|M|'])
        self.addWidget('NonExclusivePushButtons', 'Average Across:',
                       buttons=['T1','T2','FQ','X0','Y0','Z0','Vx','Vy','Vz'], val=0)
        self.addWidget('ExclusivePushButtons', 'X Axis',
                       buttons=['T','T1','T2','FQ','X0','Y0','Z0','Vx','Vy','Vz'], val=0)

        self.addWidget('Slider', 'T  index')
        self.addWidget('Slider', 'T1 index')
        self.addWidget('Slider', 'T2 index')
        self.addWidget('Slider', 'FQ index')
        self.addWidget('Slider', 'X0 index')
        self.addWidget('Slider', 'Y0 index')
        self.addWidget('Slider', 'Z0 index')
        self.addWidget('Slider', 'Vx index')
        self.addWidget('Slider', 'Vy index')
        self.addWidget('Slider', 'Vz index')

        # IO Ports
        self.addInPort('M_in', 'NPYarray',obligation=gpi.REQUIRED)
        self.addOutPort('M_out', 'NPYarray')
        self.addOutPort('Mxy_out', 'NPYarray')
        self.addOutPort('Mz_out', 'NPYarray')

        return 0

    def validate(self):
        '''This function runs before compute() as a GPI_APPLOOP exec-type.
        Here, widgets (bounds, limits, etc...) can be modified to ensure they
        are correctly validated before the widget values are used in the
        compute() routine -where widgets are buffered and any modifications are
        applied after compute() runs.
        '''

        m_in = self.getData('M_in')
        mdim = list(m_in.shape)
        maxt1 = mdim[2]
        maxt2 = mdim[3]
        maxfq = mdim[4]
        maxx0 = mdim[5]
        maxy0 = mdim[6]
        maxz0 = mdim[7]
        maxvx = mdim[8]
        maxvy = mdim[9]
        maxvz = mdim[10]

        avex = self.getVal('Average Across:')
        xaxis = self.getVal('X Axis')

        # Set slider indices for dimensions to be averaged to 1
        # Can't set x axis for a dimension to be averaged across
        #   so if this happens, set x axis to 0
        if avex:
          if (np.array(avex) == 0).any(): # T1
            maxt1 = 1
            if xaxis==1:
              xaxis = 0
              self.setAttr('X Axis',val = 0)
          if (np.array(avex) == 1).any(): # T2
            maxt2 = 1
            if xaxis==2:
              xaxis = 0
              self.setAttr('X Axis',val = 0)
          if (np.array(avex) == 2).any(): # FQ
            maxfq = 1
            if xaxis==3:
              xaxis = 0
              self.setAttr('X Axis',val = 0)
          if (np.array(avex) == 3).any(): # X0
            maxx0 = 1
            if xaxis==4:
              xaxis = 0
              self.setAttr('X Axis',val = 0)
          if (np.array(avex) == 4).any(): # Y0
            maxy0 = 1
            if xaxis==5:
              xaxis = 0
              self.setAttr('X Axis',val = 0)
          if (np.array(avex) == 5).any(): # Z0
            maxz0 = 1
            if xaxis==6:
              xaxis = 0
              self.setAttr('X Axis',val = 0)
          if (np.array(avex) == 6).any(): # Vx
            maxvx = 1
            if xaxis==7:
              xaxis = 0
              self.setAttr('X Axis',val = 0)
          if (np.array(avex) == 7).any(): # Vy
            maxvy = 1
            if xaxis==8:
              xaxis = 0
              self.setAttr('X Axis',val = 0)
          if (np.array(avex) == 8).any(): # Vz
            maxvz = 1
            if xaxis==9:
              xaxis = 0
              self.setAttr('X Axis',val = 0)

        self.setAttr('T  index',max=mdim[1]-2)
        self.setAttr('T1 index',max=maxt1-1)
        self.setAttr('T2 index',max=maxt2-1)
        self.setAttr('FQ index',max=maxfq-1)
        self.setAttr('X0 index',max=maxx0-1)
        self.setAttr('Y0 index',max=maxy0-1)
        self.setAttr('Z0 index',max=maxz0-1)
        self.setAttr('Vx index',max=maxvx-1)
        self.setAttr('Vy index',max=maxvy-1)
        self.setAttr('Vz index',max=maxvx-1)

        # Slider Visibility
        vist1 = vist2 = visfq = True
        visx0 = visy0 = visz0 = True
        visvx = visvy = visvz = True
        if maxt1 == 1 or xaxis == 1:
          vist1 = False
        if maxt2 == 1 or xaxis == 2:
          vist2 = False
        if maxfq == 1 or xaxis == 3:
          visfq = False
        if maxx0 == 1 or xaxis == 4:
          visx0 = False
        if maxy0 == 1 or xaxis == 5:
          visy0 = False
        if maxz0 == 1 or xaxis == 6:
          visz0 = False
        if maxvx == 1 or xaxis == 7:
          visvx = False
        if maxvy == 1 or xaxis == 8:
          visvy = False
        if maxvz == 1 or xaxis == 9:
          visvz = False

        self.setAttr('T  index',visible=xaxis!=0)
        self.setAttr('T1 index',visible=vist1)
        self.setAttr('T2 index',visible=vist2)
        self.setAttr('FQ index',visible=visfq)
        self.setAttr('X0 index',visible=visx0)
        self.setAttr('Y0 index',visible=visy0)
        self.setAttr('Z0 index',visible=visz0)
        self.setAttr('Vx index',visible=visvx)
        self.setAttr('Vy index',visible=visvy)
        self.setAttr('Vz index',visible=visvz)

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''

        # New data
        m_in = self.getData('M_in')

        xaxis = self.getVal('X Axis')

        tmi = int(self.getVal('T  index'))
        t1i = int(self.getVal('T1 index'))
        t2i = int(self.getVal('T2 index'))
        fqi = int(self.getVal('FQ index'))
        x0i = int(self.getVal('X0 index'))
        y0i = int(self.getVal('Y0 index'))
        z0i = int(self.getVal('Z0 index'))
        vxi = int(self.getVal('Vx index'))
        vyi = int(self.getVal('Vy index'))
        vzi = int(self.getVal('Vz index'))

# Average where Desired
        avex = self.getVal('Average Across:')
        m_av = m_in[:3,1:m_in.shape[1],:,:,:,:,:,:,:,:,:]
        for i in range(2,11):
          if (np.array(avex) == i-2).any():
            m_av = np.average(m_av,axis=i,keepdims=True)

# slice through all indices except that corresponding to x-axis values
# Pick out x-axis values
        if xaxis == 0: # Time
          xval = m_in[6,1:m_in.shape[1],0,0,0,0,0,0,0,0,0]
          mnew = m_av[:,:,t1i,t2i,fqi,x0i,y0i,z0i,vxi,vyi,vzi]
        if xaxis == 1: # T1
          xval = m_in[1,0,:,0,0,0,0,0,0,0,0]
          mnew = m_av[:,tmi,:,t2i,fqi,x0i,y0i,z0i,vxi,vyi,vzi]
        if xaxis == 2: # T2
          xval = m_in[2,0,0,:,0,0,0,0,0,0,0]
          mnew = m_av[:,tmi,t1i,:,fqi,x0i,y0i,z0i,vxi,vyi,vzi]
        if xaxis == 3: # FQ
          xval = m_in[6,0,0,0,:,0,0,0,0,0,0]
          mnew = m_av[:,tmi,t1i,t2i,:,x0i,y0i,z0i,vxi,vyi,vzi]
        if xaxis == 4: # X0
          xval = m_in[3,1,0,0,0,:,0,0,0,0,0]
          mnew = m_av[:,tmi,t1i,t2i,fqi,:,y0i,z0i,vxi,vyi,vzi]
        if xaxis == 5: # Y0
          xval = m_in[4,1,0,0,0,0,:,0,0,0,0]
          mnew = m_av[:,tmi,t1i,t2i,fqi,x0i,:,z0i,vxi,vyi,vzi]
        if xaxis == 6: # Z0
          xval = m_in[5,1,0,0,0,0,0,:,0,0,0]
          mnew = m_av[:,tmi,t1i,t2i,fqi,x0i,y0i,:,vxi,vyi,vzi]
        if xaxis == 7: # Vx
          xval = m_in[3,0,0,0,0,0,0,0,:,0,0]
          mnew = m_av[:,tmi,t1i,t2i,fqi,x0i,y0i,z0i,:,vyi,vzi]
        if xaxis == 8: # Vy
          xval = m_in[4,0,0,0,0,0,0,0,0,:,0]
          mnew = m_av[:,tmi,t1i,t2i,fqi,x0i,y0i,z0i,vxi,:,vzi]
        if xaxis == 9: # Vz
          xval = m_in[5,0,0,0,0,0,0,0,0,0,:]
          mnew = m_av[:,tmi,t1i,t2i,fqi,x0i,y0i,z0i,vxi,vyi,:]

# Start with Y=0 X Axis to plot
        x0 = xval[:,np.newaxis]
        xdim = list(xval.shape)[0]
        y0 = np.zeros(xdim)[:,np.newaxis]

# Now add X=0 Y axis to plot
        x0 = np.append(x0,np.linspace(xval[0],xval[0],xdim)[:,np.newaxis],axis=1)
        y0 = np.append(y0,np.linspace(-1.,1.,xdim)[:,np.newaxis],axis=1)

  # No assign Y Axis
        mdisp = self.getVal('M display')
        if mdisp:
          if (np.array(mdisp) == 0).any(): # Mx
            x0 = np.append(x0,xval[:,np.newaxis],axis=1)
            y0 = np.append(y0,mnew[0,:,np.newaxis],axis=1)
          if (np.array(mdisp) == 1).any(): # My
            x0 = np.append(x0,xval[:,np.newaxis],axis=1)
            y0 = np.append(y0,mnew[1,:,np.newaxis],axis=1)
          if (np.array(mdisp) == 2).any(): # Mz
            x0 = np.append(x0,xval[:,np.newaxis],axis=1)
            y0 = np.append(y0,mnew[2,:,np.newaxis],axis=1)
          if (np.array(mdisp) == 3).any(): # Mt
            x0 = np.append(x0,xval[:,np.newaxis],axis=1)
            tval = np.sqrt(mnew[0,:]*mnew[0,:] + mnew[1,:]*mnew[1,:])
            y0 = np.append(y0,tval[:,np.newaxis],axis=1)
          if (np.array(mdisp) == 4).any(): # |M|
            x0 = np.append(x0,xval[:,np.newaxis],axis=1)
            tval = np.sqrt(mnew[0,:]*mnew[0,:] + mnew[1,:]*mnew[1,:] + mnew[2,:]*mnew[2,:])
            y0 = np.append(y0,tval[:,np.newaxis],axis=1)

        m_out = np.append(x0[:,:,np.newaxis],y0[:,:,np.newaxis],axis=2)
        mx_out = mnew[0,:]
        my_out = mnew[1,:]
        mz_out = mnew[2,:]

        self.setData('M_out', m_out)
        self.setData('Mxy_out', mx_out + 1j*my_out)
        self.setData('Mz_out', mz_out)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
