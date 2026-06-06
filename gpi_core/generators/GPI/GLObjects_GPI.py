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
    Multiples - allows one to create more than one instance of object, at pseudo-random locations
    IF GL Objects = Sphere:
      Radius - Radius of Sphere
    IF GL Objects = Cylinder:
      Base, Top, Height - specifies lower and upper diameter of cylinder and its height
    IF GL Objects = Axes:
      Radius - length of axes
      Tube Radius - Diameter of axes cylinders
    IF GL Objects = Text:
      Text - string to display
    IF GL Objects = Trajectory or Random Trajectory:
      Tube Radius - diameter of cylinders used to show trajectory
    IF GL Objects = Clip Plane:
      Plane No. - Specify which of 6 clipping planes are defined
    """

    def initUI(self):
        # Widgets
        self.addWidget('ComboBox', 'GL Objects', items=['Sphere', 'Cylinder', 'Axes', 'Text', 'Trajectory', 'Random Trajectory', 'Trajectory Points', 'Clip Plane'], val='Sphere')

        self.addWidget('Slider', 'Color', min=0, max=60, val=0)
        self.addWidget('Slider', 'Brightness', min=0, max=100, val=100)
        self.addWidget('Slider', 'Subdiv', min=1, max=100, val=10)
        self.addWidget('Slider', 'Pos X', min=-100, max=100, val=0)
        self.addWidget('Slider', 'Pos Y', min=-100, max=100, val=0)
        self.addWidget('Slider', 'Pos Z', min=-100, max=100, val=0)
        self.addWidget('Slider', 'Rot X', min=0, max=360, val=0)
        self.addWidget('Slider', 'Rot Y', min=0, max=360, val=0)
        self.addWidget('Slider', 'Rot Z', min=0, max=360, val=0)
        self.addWidget('Slider', 'Multiples', min=0, max=10000, val=0)
        self.addWidget('StringBox', 'Text', val='Text')

        # Sphere
        self.addWidget('Slider', 'Radius', min=1, max=100, val=10)

        # Cylinder
        self.addWidget('Slider', 'Base', min=1, max=100, val=10)
        self.addWidget('Slider', 'Top', min=1, max=100, val=10)
        self.addWidget('Slider', 'Height', min=1, max=100, val=10)

        # Axes
        self.addWidget('Slider', 'Tube Radius', min=1, max=100, val=1)

        # ClipPlane
        self.addWidget('Slider', 'Plane No.', min=0, max=5, val=0)

        # IO Ports
        self.addInPort('GL Object List', 'GLOList', obligation=gpi.OPTIONAL)
        self.addInPort('Crds', 'NPYarray', ndim=3, vec=3, obligation=gpi.OPTIONAL)
        self.addOutPort('GL Object Descriptions', 'GLOList')

    def validate(self):

        arg = self.getVal('GL Objects')
        if arg == 'Sphere' or arg == 'Axes' or arg == 'Trajectory Points':
            self.setAttr('Radius', visible=True)
        else:
            self.setAttr('Radius', visible=False)

        if arg == 'Cylinder':
            self.setAttr('Base', visible=True)
            self.setAttr('Top', visible=True)
            self.setAttr('Height', visible=True)
        else:
            self.setAttr('Base', visible=False)
            self.setAttr('Top', visible=False)
            self.setAttr('Height', visible=False)

        if arg == 'Axes' or arg == 'Trajectory' or arg == 'Random Trajectory':
            self.setAttr('Tube Radius', visible=True)
        else:
            self.setAttr('Tube Radius', visible=False)

        if arg == 'Text':
            self.setAttr('Text', visible=True)
        else:
            self.setAttr('Text', visible=False)

        if arg == 'Clip Plane':
            self.setAttr('Plane No.', visible=True)
        else:
            self.setAttr('Plane No.', visible=False)

        return 0

    def compute(self):
        '''This is where the main algorithm should be implemented.
        '''
        out = glo.ObjectList(self.getData('GL Object List'))

        arg = self.getVal('GL Objects')

        color = 0.1*self.getVal('Color')
        bright = 0.01*self.getVal('Brightness')
        subdiv = self.getVal('Subdiv')
        posx = 0.1*self.getVal('Pos X')
        posy = 0.1*self.getVal('Pos Y')
        posz = 0.1*self.getVal('Pos Z')
        Rx = 1.0*self.getVal('Rot X')
        Ry = 1.0*self.getVal('Rot Y')
        Rz = 1.0*self.getVal('Rot Z')
        multiples = self.getVal('Multiples')
        text = self.getVal('Text')
        planeNo = self.getVal('Plane No.')


        # Sphere
        radius = 0.1*self.getVal('Radius')

        # Cylinder
        base = 0.05*self.getVal('Base')
        top = 0.05*self.getVal('Top')
        height = 0.2*self.getVal('Height')

        # Axes
        tuberad = 0.01*self.getVal('Tube Radius')

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
 
        RGBA = (bright*red, bright*green, bright*blue, 1.0)

        if arg == 'Sphere':
            desc = glo.Sphere()
            desc.setRadius(radius)
            desc.setRGBA(RGBA)
            desc.setPos((posx, posy, posz))
            desc.setRotXYZ((Rx, Ry, Rz))
            desc.setSubdiv(subdiv)
            if multiples:
                desc.setMultiples(np.random.rand(multiples,3)*10-5)

            out.append(desc)

        if arg == 'Clip Plane':
            desc = glo.ClipPlane()
            desc.setPos((posx, posy, posz))
            desc.setRotXYZ((Rx, Ry, Rz))
            desc.setPlaneNum(planeNo)

            out.append(desc)

        if arg == 'Cylinder':
            desc = {}
            desc = glo.Cylinder()
            desc.setRGBA(RGBA)
            desc.setPos((posx, posy, posz))
            desc.setRotXYZ((Rx, Ry, Rz))
            desc.setSubdiv(subdiv)
            desc.setBase(base)
            desc.setTop(top)
            desc.setHeight(height)
            #desc.setP1P2((0,-5,0), (0,5,0))
            if multiples:
                desc.setMultiples(np.random.rand(multiples,3)*10-5)

            out.append(desc)

        if arg == 'Axes':
            desc = {}
            desc = glo.Axes()
            desc.setRGBA(RGBA)
            desc.setPos((posx, posy, posz))
            desc.setRotXYZ((Rx, Ry, Rz))
            desc.setSubdiv(subdiv)
            desc.setTubeRadius(tuberad)
            desc.setRadius(radius)
            if multiples:
                desc.setMultiples(np.random.rand(multiples,3)*10-5)

            out.append(desc)

        if arg == 'Text':
            desc = {}
            desc = glo.Text()
            desc.setRGBA(RGBA)
            desc.setPos((posx, posy, posz))
            desc.setRotXYZ((Rx, Ry, Rz))
            desc.setSubdiv(subdiv)
            desc.setText(text)
            if multiples:
                desc.setMultiples(np.random.rand(multiples,3)*10-5)

            out.append(desc)

        if arg == 'Trajectory':

            if self.getData('Crds') is not None:
                crds = self.getData('Crds')
                crds = crds * 15  # scale to GL window

                # Use the 'multiples' option to keep a list of points instead
                # of full objects.
                for i in range(crds.shape[0]):
                    desc = glo.Cylinder()
                    desc.setMultiples(crds[i])
                    desc.setEndToEnd(True)
                    desc.setRadius(tuberad/2.0)
                    if color == 0:
                        desc.setRGBA((1,1,1,1))
                    else:
                        isat = (float(i)/float(crds.shape[0]))
                        r2 = isat + (1.-isat)*red
                        g2 = isat + (1.-isat)*green
                        b2 = isat + (1.-isat)*blue
                        desc.setRGBA((r2,g2,b2,1.))
                        #desc.setRGBA(RGBA/float(i+1))
                    desc.setSubdiv(subdiv)
                    out.append(desc)

        if arg == 'Random Trajectory':

            # Given coordinates create a new object for every segment.
            # NOTE: This is slow and memory intensive for large trajectories.

            crds = np.random.rand(10,3)*10-5

            for i in range(crds.shape[0]-1):
                desc = glo.Cylinder()
                desc.setP1P2(crds[i].tolist(), crds[i+1].tolist())
                desc.setRadius(tuberad/2.0)
                desc.setRGBA(RGBA)
                desc.setSubdiv(subdiv)
                out.append(desc)
        
        if arg == 'Trajectory Points':
                        
            if self.getData('Crds') is not None:
                crds = self.getData('Crds')
                crds = crds * 15  # scale to GL window
                            
                # Use the 'multiples' option to keep a list of points instead
                # of full objects.
                for i in range(crds.shape[0]):
                    posx = 360*crds[i,:,0]
                    posy = 360*crds[i,:,1]
                    posz = 360*crds[i,:,2]
                    desc = glo.Sphere()
                    desc.setMultiples(crds[i])
                    desc.setPos((posx, posy, posz))
                    desc.setRadius(.1*radius)
                    if color == 0:
                        desc.setRGBA((1,1,1,1))
                    else:
                        desc.setRGBA(RGBA)
                    desc.setSubdiv(subdiv)
                    out.append(desc)

        if out.len() == 0: out = None
        self.setData('GL Object Descriptions', out)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_PROCESS
        #return gpi.GPI_THREAD
