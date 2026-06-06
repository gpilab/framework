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
# Date: 2013 Oct

import gpi
from gpi import QtGui
import numpy as np

class ExternalNode(gpi.NodeAPI):
    """2D image Compare Module

    INPUTS (must be the same size):
    3D uint8 ARGB data (e.g. from ImageDisplay)
    3D uint8 ARGB data (e.g. from ImageDisplay)

    OUTPUT:
    3D data of displayed image, last dimension has length 4 for ARGB byte (uint8) data

    WIDGETS:
    Transition: chooses how to transition between images of left and right ports
    LeftRight: Toggles between left or right images
    edge: slider to demarcate the line, or fading, between two images
    """

    def execType(self):
        return gpi.GPI_APPLOOP

    def initUI(self):

        # Widgets
        self.addWidget('DisplayBox', 'Viewport:')
        self.addWidget('ExclusivePushButtons','Transition',
                       buttons=['Toggle','Fade','Hor','Vert','Color'], val=0)
        self.addWidget('PushButton', 'LeftRight', button_title='Left Port', toggle=True)
        self.addWidget('Slider', 'edge',val=0)

        # IO Ports
        self.addInPort('inleft', 'NPYarray', ndim=3, obligation=gpi.REQUIRED)
        self.addInPort('inright', 'NPYarray', ndim=3, obligation=gpi.REQUIRED)
        self.addOutPort('out', 'NPYarray')

    def validate(self):

        # Complex or Scalar?
        inleft = self.getData('inleft')
        inright = self.getData('inright')

        if (inleft.shape[-1] != 4):
            self.log.warn("left port data must have a last dimension of 4")
            return 1
        if (inright.shape[-1] != 4):
            self.log.warn("right port data must have a last dimension of 4")
            return 1
        if (inleft.shape != inright.shape):
            self.log.warn("data must be the same size")
            return 1

        if self.getVal('Transition') == 0: # Toggle
          self.setAttr('edge',visible=False)
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title="Right Port")
          else:
            self.setAttr('LeftRight',button_title="Left Port")
        elif self.getVal('Transition') == 1: # Fade
          self.setAttr('edge',visible=True,max=100)
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title="Right Port at edge=0")
          else:
            self.setAttr('LeftRight',button_title="Left Port at edge=0")
        elif self.getVal('Transition') == 2: # Horizontal
          self.setAttr('edge',visible=True,max=inleft.shape[0])
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title="Right Port on top")
          else:
            self.setAttr('LeftRight',button_title="Left Port on top")
        elif self.getVal('Transition') == 3: # Vertical
          self.setAttr('edge',visible=True,max=inleft.shape[1])
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title="Right Port on left")
          else:
            self.setAttr('LeftRight',button_title="Left Port on left")
        elif self.getVal('Transition') == 4: # Color
          self.setAttr('edge',visible=True,max=5)
          if self.getVal('LeftRight'):
            self.setAttr('LeftRight',button_title="Left Port RYGCBM")
          else:
            self.setAttr('LeftRight',button_title="Right Port RYGCBM")

        return 0

    def compute(self):

        edgeval = self.getVal('edge')

        # make a copy for changes
        if self.getVal('LeftRight'):
          outright = self.getData('inleft')
          outleft  = self.getData('inright')
        else:
          outleft = self.getData('inleft')
          outright = self.getData('inright')

        if self.getVal('Transition') == 0: # Toggle
          out = outleft
        elif self.getVal('Transition') == 1: # Fade
          cr = 0.01*float(self.getVal('edge'))
          cl = 1.-cr
          out = cl*outleft.astype(np.float) + cr*outright.astype(np.float)
        elif self.getVal('Transition') == 2: # Horizontal
          out = np.append(outleft[:edgeval,:,:],outright[edgeval:,:,:],axis=0)
        elif self.getVal('Transition') == 3: # Vertical
          out = np.append(outleft[:,:edgeval,:],outright[:,edgeval:,:],axis=1)
        elif self.getVal('Transition') == 4: # Color
          out = np.copy(outleft)
          if self.getVal('edge') <= 1 or self.getVal('edge') == 5:
            out[:,:,2] = outright[:,:,2] # Red
          if self.getVal('edge') >= 1 and self.getVal('edge') <= 3:
            out[:,:,1] = outright[:,:,1] # Green
          if self.getVal('edge') >= 3:
            out[:,:,0] = outright[:,:,0] # Blue


        image1 = out.astype(np.uint8)

        h, w = out.shape[:2]
        format_ = QtGui.QImage.Format_RGB32

        image = QtGui.QImage(image1.data, w, h, format_)
        image.ndarray = image1
        if image.isNull():
            self.log.warn("Image Viewer: cannot load image")

        self.setAttr('Viewport:', val=image)
        self.setData('out',image1)

        return 0
