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


# Author: Nick Zwart
# Date: 2013aug10

import copy
import numpy as np

import gpi
import gpi.GLObjects as glo


class ExternalNode(gpi.NodeAPI):
    """A basic module for generating GL object descriptions using GPI format.
    These objects can be accumulated by creating a string of GLObjects nodes, with
    the output of one node fed to the input of the next node.  The final list of GL objects
    can be viewed using the GLViewer

    INPUTS:
    GL Object List - optional input takes the output of another GLObject module, for concatenating all objects in a list
    Crds - optional input of k-space coordinates, as a numpy array, for use with the "trajectory" GL Objects function.
      The last dimension must be 3, corresponding to kx/ky/kz

    OUTPUTS - GL Object List

    WIDGETS:
    GL Objects - type of GL Object to create
      Self Evident, hook up to GLViewer to display.  Clip Plane must be combined with a GL Object to observe
    Color - changes hue of object
    Subdiv - for sphere and cylinders, specifies how many planar surfaces to approximate curve
    Pos X, Pos Y, Pos Z - X, Y, Z coordinates for center of object
    Rot X, Rot Y, Rot Y - specifies rotation of object
    Tube Radius - diameter of cylinders used to show trajectory
    """

    def initUI(self):
        # Widgets
        self.addWidget('Slider', 'Color', min=0, max=60, val=0)
        self.addWidget('DoubleSpinBox', 'Color Span', val=0)
        self.addWidget('Slider', 'Subdiv', min=1, max=100, val=10)
        self.addWidget('DoubleSpinBox', 'tau', val=0.)
        self.addWidget('DoubleSpinBox', 't0', val=0.)
        self.addWidget('DoubleSpinBox', 't1', val=0.)
        self.addWidget('DoubleSpinBox', 't normalize', min=1., val=1.)

        # Axes
        self.addWidget('Slider', 'Tube Radius', min=1, max=100, val=1)

        # IO Ports
        self.addInPort('GL Object List', 'GLOList', obligation=gpi.OPTIONAL)
        self.addInPort('Crds', 'NPYarray', ndim=3, vec=2)
        self.addOutPort('GL Object Descriptions', 'GLOList')

    def validate(self):

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''
        out = glo.ObjectList(self.getData('GL Object List'))

        color_0 = 0.1*self.getVal('Color')
        cspan = 0.1*self.getVal('Color Span')
        subdiv = self.getVal('Subdiv')
        tuberad = 0.01*self.getVal('Tube Radius')
        tnorm = 2.*self.getVal('t normalize') # multiply by 2 to normlize to 0.5
        tau = self.getVal('tau')/tnorm
        t0 = self.getVal('t0')/tnorm
        t1 = self.getVal('t1')/tnorm

        crds_in = self.getData('Crds')

        z0 = np.linspace(t0,t1,crds_in.shape[0],endpoint=False)
        z1 = np.linspace(0.,tau,crds_in.shape[1],endpoint=False)
        zval = z0[:,np.newaxis,np.newaxis]+z1[np.newaxis,:,np.newaxis]

        crds = 15*np.concatenate((crds_in,zval),axis=2) # scale to GL window
 
        # Use the 'multiples' option to keep a list of points instead
        # of full objects.
        for i in range(crds.shape[0]):

          desc = glo.Cylinder()
          desc.setMultiples(crds[i])
          desc.setEndToEnd(True)
          desc.setRadius(tuberad/2.0)

          color = color_0 + cspan*float(i)/float(crds.shape[0])
          while color > 6.:
            color = color - 6.

          if color < 1:
            red = 1.
            green = color
            blue = 0
          elif color < 2:
            red = 2-color
            green = 1.
            blue = 0
          elif color < 3:
            red = 0
            green = 1.
            blue = color-2
          elif color < 4:
            red = 0
            green = 4-color
            blue = 1
          elif color < 5:
            red = color-4
            green = 0
            blue = 1
          elif color <= 6:
            red = 1.
            green = 0
            blue = 6-color

          desc.setRGBA((red,green,blue,1.))
          desc.setSubdiv(subdiv)
          out.append(desc)

        if out.len() == 0: out = None
        self.setData('GL Object Descriptions', out)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
        #return gpi.GPI_THREAD
