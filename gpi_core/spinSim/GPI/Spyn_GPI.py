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
# Date: 2013Jun13

import gpi
from gpi import QtWidgets


# WIDGET
class SpynAxys(gpi.GenericWidgetGroup):
    """A combination of SpinBoxes, DoubleSpinBoxes, and PushButtons
    to form a unique widget suitable for the Spin Generator Axes.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self._val = {}
        self._val['length'] = 1
        self._val['start'] = 0.
        self._val['end'] = 0. # the original array length

        self.sb = gpi.BasicSpinBox()  # length
        self.sb.set_label('# Spins:')
        self.sb.set_min(1)
        self.sb.set_val(1)
        self.sb.set_max(gpi.GPI_INT_MAX)

        self.db1 = gpi.BasicDoubleSpinBox()  # start
        self.db1.set_label('Start:')
        self.db1.set_min(gpi.GPI_FLOAT_MIN)
        self.db1.set_max(gpi.GPI_FLOAT_MAX)
        self.db1.set_decimals(3)
        self.db1.set_singlestep(1.)
        self.db1.set_val(0)

        self.db2 = gpi.BasicDoubleSpinBox()  # end
        self.db2.set_label('End:')
        self.db2.set_min(gpi.GPI_FLOAT_MIN)
        self.db2.set_max(gpi.GPI_FLOAT_MAX)
        self.db2.set_decimals(3)
        self.db2.set_singlestep(1.)
        self.db2.set_val(0)

        self.sb.valueChanged.connect(self.lenChange)
        self.db1.valueChanged.connect(self.startChange)
        self.db2.valueChanged.connect(self.endChange)

        vbox = QtWidgets.QHBoxLayout()
        vbox.addWidget(self.sb)
        vbox.addWidget(self.db1)
        vbox.addWidget(self.db2)
        vbox.setStretch(0, 0)
        vbox.setStretch(1, 0)
        vbox.setStretch(2, 0)
        vbox.setContentsMargins(0, 0, 0, 0)  # we don't need margins here
        vbox.setSpacing(0)
        self.setLayout(vbox)

    # setters
    def set_val(self, val):
        """A python-dict containing: size, and width parms. """
        sig = False
        if 'length' in val:
            self._val['length'] = val['length']
            self.setLenQuietly(val['length'])
            sig = True
        if 'start' in val:
            self._val['start'] = val['start']
            self.setStartQuietly(val['start'])
            sig = True
        if 'end' in val:
            self._val['end'] = val['end']
            self.setEndQuietly(val['end'])
            sig = True
        if sig:
            self.valueChanged.emit()


    # getters
    def get_val(self):
        return self._val

    # support
    def lenChange(self, val):
        self._val['length'] = val
        self.setLenQuietly(self._val['length'])
        self.valueChanged.emit()

    def startChange(self, val):
        self._val['start'] = val
        self.setStartQuietly(self._val['start'])
        self.valueChanged.emit()

    def endChange(self, val):
        self._val['end'] = val
        self.setEndQuietly(self._val['end'])
        self.valueChanged.emit()

    def setLenQuietly(self, val):
        self.sb.blockSignals(True)
        self.sb.set_val(val)
        self.sb.blockSignals(False)

    def setStartQuietly(self, val):
        self.db1.blockSignals(True)
        self.db1.set_val(val)
        self.db1.blockSignals(False)

    def setEndQuietly(self, val):
        self.db2.blockSignals(True)
        self.db2.set_val(val)
        self.db2.blockSignals(False)


class ExternalNode(gpi.NodeAPI):
    """Module to generate initial spin profile, for bloch simulations in GPI
    Output data are 11-dimensional, with data stored as follows:
    Dimension 0 corresponds to base information such  M0, T1, T2, velocities, Frequency,
                Diffusion (not yet implemented), and the value of dt
    Dimension 1 corresponds to time.
                The first index of Dimension 1 stores the above info, and
                the 2nd index stores the Spin magnetization, position, time,
                                         gradient, rf, and spoiler info
    These two dimensions are illustrated below:

  D  ###### Dim 0 ->>> #########################
  i  #    0  1  2  3  4  5  6  7  8  9  10 11 12
  m  #
  1  # 0  M0 T1 T2 Vx Vy Vz Fq Dx Dy Dz dt __ __
  |  # 1  Mx My Mz X  Y  Z  T  Gx Gy Gz Rx Ry Sp
  v  # 2  Mx My Mz X  Y  Z  T  Gx Gy Gz Rx Ry Sp
  v  # 3  Mx My Mz X  Y  Z  T  Gx Gy Gz Rx Ry Sp
  v  # 4  Mx My Mz X  Y  Z  T  Gx Gy Gz Rx Ry Sp
  v  ###########################################

    Dimensions 2-10 correspond to the widgets below, from T1, T2, etc. to Vy and Vz

    OUTPUT - spin state, typically fed to Bloch module.  No data present until "Starting Spins"
             widget is set to something other than "OFF"

    WIDGETS:
    Starting Spins - starting state of all spins.  When set to "OFF", no data are generated
    T0 (ms) - starting time.  Valuable for (e.g.) having velocities (which is not yet implemented)
    dt (us) - time between time points which will be recorded by Bloch module and pasted along the first dimension
              smaller numbers produce finer time resolution but larger data sets
              Note the actual numerical simulations occur with time resolution of 1us regardless of this value
    For the remaining widgets, the following is true:
      # Spins - length along that dimension, with values from the specified "Start" value to the specified "End" value
      if # Spins is 1, the value of that property is given by the "Start" parameter
    T1 (ms) - dimension 2 variable.  A value of 0 is infinity (no T1 recovery), otherwise values are in ms
    T2 (ms) - dimension 3 variable.  A value of 0 is infinity (no T2 relaxation), otherwise values are in ms
    Fq (Hz) - dimension 4 variable, off-resonance frequency
    X0/Y0/Z0 - dimension 5-7 variables, locations of spins
    Vx/Vy/Vz - dimension 8-10 variables, velocity of spins (not yet implemented)
    """

    def initUI(self):
        # Widgets
        self.addWidget('ExclusivePushButtons', 'Starting Spins',
                       buttons=['OFF', 'Mz', '0', '-Mz', 'Mx', 'My'],
                       val=0)
        self.addWidget('DoubleSpinBox', 'T0 (ms)', val=0.0)
        self.addWidget('SpinBox', 'dt (us)', val=50, min=1)
        self.addWidget('SpynAxys', 'T1 (ms)')
        self.addWidget('SpynAxys', 'T2 (ms)')
        self.addWidget('SpynAxys', 'Fq (Hz)')
        self.addWidget('SpynAxys', 'X0 (mm)')
        self.addWidget('SpynAxys', 'Y0 (mm)')
        self.addWidget('SpynAxys', 'Z0 (mm)')
        self.addWidget('SpynAxys', 'Vx (cm/s)')
        self.addWidget('SpynAxys', 'Vy (cm/s)')
        self.addWidget('SpynAxys', 'Vz (cm/s)')

        # IO Ports
        self.addOutPort('out', 'NPYarray')

    def validate(self):
        '''This function runs before compute() as a GPI_APPLOOP exec-type.
        Here, widgets (bounds, limits, etc...) can be modified to ensure they
        are correctly validated before the widget values are used in the
        compute() routine -where widgets are buffered and any modifications are
        applied after compute() runs.
        '''

        # validate widget bounds
        return 0

    def compute(self):
       '''This is where the main algorithm should be implemented.
       '''

       import numpy as np

       # GETTING WIDGET INFO
       dim1 = 13 # number of params
         # 0  1  2  3  4  5  6  7  8  9  10 11 12
         # M0 T1 T2 Vx Vy Vz Fq Dx Dy Dz dt __ __
         # Mx My Mz X  Y  Z  T  Gx Gy Gz Rx Ry Sp
       dim2 = 2  # number of time points, 1st time point is constants

       dtms = float(self.getVal('dt (us)')) * 0.001 # convert from us to ms
       t0ms = self.getVal('T0 (ms)')

       mx=my=mz=0.
       if self.getVal('Starting Spins') == 1:
         mz = 1
       if self.getVal('Starting Spins') == 3:
         mz = -1
       if self.getVal('Starting Spins') == 4:
         mx = 1
       if self.getVal('Starting Spins') == 5:
         my = 1

       if self.getVal('Starting Spins') != 0: # OFF State

         # Units are ms, kHz, m, mT

         # Dim 3 is T1
         val = self.getVal('T1 (ms)')
         dim3 = val['length']

         if val['start']<=0:
           t1start=0
         else:
           t1start=val['start']

         if val['end']<=0:
           t1end=0
         else:
           t1end=val['end']

         t1step = (t1end-t1start)/max(1.,float(dim3-1))

         # Dim 4 is T2
         val = self.getVal('T2 (ms)')
         dim4 = val['length']

         if val['start']<=0:
           t2start=0
         else:
           t2start=val['start']

         if val['end']<=0:
           t2end=0
         else:
           t2end=val['end']

         t2step = (t2end-t2start)/max(1.,float(dim4-1))

         # Dim 5 is Fq, convert to kHz
         val = self.getVal('Fq (Hz)')
         dim5 = val['length']
         fqstart=0.001*val['start']
         fqstep= 0.001*(val['end']-val['start'])/max(1.,float(dim5-1))

         # Dim 6 is X0, convert to m
         val = self.getVal('X0 (mm)')
         dim6 = val['length']
         x0start=0.001*val['start']
         x0step= 0.001*(val['end']-val['start'])/max(1.,float(dim6-1))

         # Dim 7 is Y0, convert to m
         val = self.getVal('Y0 (mm)')
         dim7 = val['length']
         y0start=0.001*val['start']
         y0step= 0.001*(val['end']-val['start'])/max(1.,float(dim7-1))

         # Dim 8 is Z0, convert to m
         val = self.getVal('Z0 (mm)')
         dim8 = val['length']
         z0start=0.001*val['start']
         z0step= 0.001*(val['end']-val['start'])/max(1.,float(dim8-1))

         # Dim 9 is Vx, convert to m/ms
         val = self.getVal('Vx (cm/s)')
         dim9 = val['length']
         vxstart=0.00001*val['start']
         vxstep= 0.00001*(val['end']-val['start'])/max(1.,float(dim9-1))

         # Dim 10 is Vy, convert to m/ms
         val = self.getVal('Vy (cm/s)')
         dim10 = val['length']
         vystart=0.00001*val['start']
         vystep= 0.00001*(val['end']-val['start'])/max(1.,float(dim10-1))

         # Dim 11 is Vz, convert to m/ms
         val = self.getVal('Vz (cm/s)')
         dim11 = val['length']
         vzstart=0.00001*val['start']
         vzstep= 0.00001*(val['end']-val['start'])/max(1.,float(dim11-1))

         # Create the data
         out=np.zeros([dim1,dim2,dim3,dim4,dim5,dim6,dim7,dim8,dim9,dim10,dim11])

         # Assign the 1st element of data in dim2, M0 T1 T2 Vx Vy Vz Fq Dx Dy Dz dt GM __
         # These values don't change
         # M0
         out[0,0,:,:,:,:,:,:,:,:,:] = 1.

         # T1
         for i in range(0,dim3):
           if (t1start + t1step*float(i)) > 0.:
             r1val = 1./(t1start + t1step*float(i))
           else:
              r1val = 0;
           out[1,0,i,:,:,:,:,:,:,:,:] = r1val

         # T2
         for i in range(0,dim4):
           if (t2start + t2step*float(i)) > 0.:
             r2val = 1./(t2start + t2step*float(i))
           else:
              r2val = 0;
           out[2,0,:,i,:,:,:,:,:,:,:] = r2val

         #Vx
         for i in range(0,dim9):
           out[3,0,:,:,:,:,:,:,i,:,:] = vxstart + vxstep*float(i)

         #Vy
         for i in range(0,dim10):
           out[4,0,:,:,:,:,:,:,:,i,:] = vystart + vystep*float(i)

         #Vz
         for i in range(0,dim11):
           out[5,0,:,:,:,:,:,:,:,:,i] = vzstart + vzstep*float(i)

         #Fq
         for i in range(0,dim5):
           out[6,0,:,:,i,:,:,:,:,:,:] = fqstart + fqstep*float(i)

         # Dx, Dy, Dz = 0, no action for now

         # dt - convert from us to ms
         out[10,0,:,:,:,:,:,:,:,:,:] = dtms

         # Gamma - fixed for now, kHz/mT
         out[11,0,:,:,:,:,:,:,:,:,:] = 42.577

         # Assign 2nd element of data in dim2, Mx My Mz X  Y  Z  T  Gx Gy Gz Rx Ry Sp
         # This is the first time point

         #Mx My Mz
         out[0,1,:,:,:,:,:,:,:,:,:] = mx
         out[1,1,:,:,:,:,:,:,:,:,:] = my
         out[2,1,:,:,:,:,:,:,:,:,:] = mz

         #X0
         for i in range(0,dim6):
           out[3,1,:,:,:,i,:,:,:,:,:] = x0start + x0step*float(i)

         #Y0
         for i in range(0,dim7):
           out[4,1,:,:,:,:,i,:,:,:,:] = y0start + y0step*float(i)

         #Z0
         for i in range(0,dim8):
           out[5,1,:,:,:,:,:,i,:,:,:] = z0start + z0step*float(i)

         #T0
         out[6,1,:,:,:,:,:,:,:,:,:] = t0ms

         # Reset positions to reflect time relative to zero
         # X0 += Vx*T0
         out[3,1,:,:,:,:,:,:,:,:,:] += out[3,0,:,:,:,:,:,:,:,:,:]*t0ms
         # Y0 += Vy*T0
         out[4,1,:,:,:,:,:,:,:,:,:] += out[4,0,:,:,:,:,:,:,:,:,:]*t0ms
         # Z0 += Vz*T0
         out[5,1,:,:,:,:,:,:,:,:,:] += out[5,0,:,:,:,:,:,:,:,:,:]*t0ms

         #Gx Gy Gz Rx Ry Sp all 0, no action necessary

       else:
         out = None

       # SETTING PORT INFO
       self.setData('out', out)

       return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
