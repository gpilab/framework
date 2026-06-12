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


# author: Jim Pipe
# date: 2012sep

import numpy as np
import gpi


class ExternalNode(gpi.NodeAPI):
    """Clamp, Threshold, or Scale values
       Pass does not operate on the data, but sets the min and max widgets to reflect data min and max
       Clamp takes all values above(below) the max(min) and sets them to the max(min)
       Threshold takes all values above(below) the max(min) and sets them to zero
       Scale "Min" OR "Max" multiplies the data by a constant for the desired min/max
       Scale "Min" AND "Max" multiplies the data by a constant and adds an offset for the desired min & max
       For complex numbers, the operations work on the magnitude, while preserving phase
    """

    def initUI(self):

        # Widgets
        self.addWidget('ExclusivePushButtons', 'operation', buttons=[
                       'Pass', 'Clamp', 'Threshold','Scale'], val=0)
        self.addWidget('ExclusivePushButtons', 'MinMax', buttons=[
                       'Min', 'Max', 'Min&Max'], val=0)
        self.addWidget('DoubleSpinBox', 'Min', val = 0, decimals = 5)
        self.addWidget('DoubleSpinBox', 'Max', val = 0, decimals = 5)

        # IO Ports
        self.addInPort('in', 'NPYarray')
        self.addOutPort('out', 'NPYarray')

    def validate(self):

        if self.getVal('operation') == 0:
          self.setAttr('MinMax',visible=False)
          self.setAttr('Min',visible=True)
          self.setAttr('Max',visible=True)
        elif self.getVal('MinMax') == 0:
          self.setAttr('MinMax',visible=True)
          self.setAttr('Min',visible=True)
          self.setAttr('Max',visible=False)
        elif self.getVal('MinMax') == 1:
          self.setAttr('MinMax',visible=True)
          self.setAttr('Min',visible=False)
          self.setAttr('Max',visible=True)
        else:
          self.setAttr('MinMax',visible=True)
          self.setAttr('Min',visible=True)
          self.setAttr('Max',visible=True)

        if self.getVal('Max') < self.getVal('Min'):
          self.setAttr('Max',val = self.getVal('Min'))

        return(0)

    def compute(self):

        import numpy as np

        data = self.getData('in')
        minmax = self.getVal('MinMax')
        pcts = self.getVal('operation')
        minv = self.getVal('Min')
        maxv = self.getVal('Max')

        if np.iscomplexobj(data):
          dmag = np.abs(data)
          darg = np.angle(data)
          if minmax == 0: #Min
            maxv = np.amax(dmag)
          elif minmax == 1: #Max
            minv = np.amin(dmag)

          if pcts == 0: # Pass
            omag = dmag
            self.setAttr('Min',val=np.amin(omag))
            self.setAttr('Max',val=np.amax(omag))
          elif pcts == 1: # Clamp
            omag = np.clip(dmag,minv,maxv)
          elif pcts == 2: # Thresh
            omag = np.where((dmag < minv) | (dmag > maxv), 0.0, dmag)
          elif pcts == 3: # Scale
            if minmax == 0: #Min
              omag = (minv/np.amin(dmag))*dmag
            elif minmax == 1: #Max
              omag = (maxv/np.amax(dmag))*dmag
            elif minmax == 2: #MinMax
              datave = 0.5*(np.amin(dmag)+np.amax(dmag))
              outave = 0.5*(minv+maxv)
              if np.amax(dmag) != np.amin(dmag):
                scale = (maxv-minv)/(np.amax(dmag)-np.amin(dmag))
              else:
                scale = 0
              omag = (scale*(dmag-datave)) + outave

          outdat = omag*(np.cos(darg) + np.sin(darg)*1j)

        else:
          if minmax == 0: #Min
            maxv = np.amax(data)
          elif minmax == 1: #Max
            minv = np.amin(data)

          if pcts == 0: # Pass
            outdat = data
            self.setAttr('Min',val=np.amin(outdat))
            self.setAttr('Max',val=np.amax(outdat))
          elif pcts == 1: # Clamp
            outdat = np.clip(data,minv,maxv)
          elif pcts == 2: # Thresh
            outdat = np.where((data < minv) | (data > maxv), 0, data)
          elif pcts == 3: # Scale
            if minmax == 0: #Min
              outdat = (minv/np.amin(data))*data
            elif minmax == 1: #Max
              outdat = (maxv/np.amax(data))*data
            elif minmax == 2: #MinMax
              datave = 0.5*(np.amin(data)+np.amax(data))
              outave = 0.5*(minv+maxv)
              if np.amax(data) != np.amin(data):
                scale = (maxv-minv)/(np.amax(data)-np.amin(data))
              else:
                scale = 0
              outdat = (scale*(data-datave)) + outave

        self.setData('out', outdat)
        return(0)
