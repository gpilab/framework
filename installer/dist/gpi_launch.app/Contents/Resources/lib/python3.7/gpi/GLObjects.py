#    Copyright (C) 2014  Dignity Health
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
#    AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
#    SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
#    PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
#    USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
#    LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
#    MAKES NO WARRANTY AND HAS NO LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.

# Manuals:
# PyOpenGL 3.0.2 Object Ref:
#   http://pyopengl.sourceforge.net/documentation/manual-3.0/index.xhtml
# OGL Programming Guide:
#   http://www.glprogramming.com/red/index.html
# GLUT Guide:
#   http://www.opengl.org/documentation/specs/glut/spec3/node1.html
#
# Specific Help:
#   Cyl between two pts:
#       http://www.thjsmith.com/40/cylinder-between-two-points-opengl-c
#   FSAA:
#       http://www.cs.uiuc.edu/class/sp05/cs419/accum/antialias.c
#       http://www.glprogramming.com/red/chapter06.html#name2
#
# Possible Extension Packages:
#   http://www.slicer.org
#   http://www.paraview.org/paraview/project/features.html

''' This module facilitates the manipulation of GL objects by maintaining a
list of GL calls to be supplied to a GL renderer.  These objects are pure
python and can therefore be easily serialized for passing between Nodes. '''


import copy
import traceback
import numpy as np  # for vector calcs
import numpy.linalg

from gpi import QtWidgets, QtGui, QtCore
from .logger import manager
# start logger for this module
log = manager.getLogger(__name__)

try:
    try:
        import OpenGL, OpenGL.GL, OpenGL.GLU, OpenGL.GLUT
        from OpenGL import GL, GLU
    
    # fallback for OpenGl Module import source
    except ImportError:
        # https://stackoverflow.com/questions/63475461/unable-to-import-opengl-gl-in-python-on-macos
        print('Patching OpenGL import for Big Sur (OSX)')
        from ctypes import util
        orig_util_find_library = util.find_library
        
        # retrieving the OpenGl Modules from its directory instead of cache
        def new_util_find_library (name):
            res = orig_util_find_library (name)
            if res: return res
            return '/System/Library/Frameworks/' + name + '.framework/' + name

        util.find_library = new_util_find_library
        
        import OpenGL, OpenGL.GL, OpenGL.GLU, OpenGL.GLUT
        from OpenGL import GL, GLU

except ImportError:
    log.warn('OpenGL was not found, GL objects and windows will not be supported in this session.')
    raise



class ObjectList(object):
    def __init__(self, oList=None):

        self._olist = []
        self._olist_noncacheable = []

        # keep track of clipping planes only one instance of each
        # can exist at a time so replace them.
        self._clipplanes = {}

        if oList is not None:
            self._olist = copy.deepcopy(oList.getCacheableList())
            self._olist_noncacheable = copy.deepcopy(oList.getNonCacheableList())
            self._clipplanes = copy.deepcopy(oList.getClipPlanes())

    def append(self, obj):

        # all special object hooks
        if isinstance(obj, ClipPlane):
            self._clipplanes[obj.getPlaneLabel()] = obj
            return

        if not obj.cacheable():
            self._olist_noncacheable.append(obj)
            return

        # all normal objects get appended
        self._olist.append(obj)

    def getCacheableList(self):
        return self._olist

    def getNonCacheableList(self):
        return self._olist_noncacheable

    def getClipPlanes(self):
        return self._clipplanes

    def len(self):
        return len(self._clipplanes) + len(self._olist) + len(self._olist_noncacheable)


class GPIGLObject(object):

    def __init__(self):
        # the name of THIS object (for referencing)
        self._label = self.__class__
        self._cacheable = True
        self._glwdg = None

        # material
        self._face = 'GL_FRONT'  # GL_FRONT_AND_BACK
        self._pname = 'GL_AMBIENT_AND_DIFFUSE'
        self._RGBA = (1.0, 1.0, 1.0, 1.0)  # default color is WHITE

        # shading
        self._shademodel = 'GL_SMOOTH'

        # subdivisions
        self._subdiv = 8

        # position (x, y, z)
        self._position = None

        # rotations individual matrices (x, y, z)
        self._rotxyz = None

        # rotations angle-vector (ang, x, y, z)
        self._rotav = None

        # scale (x, y, z)
        self._scale = None

        # multiple shape instances
        self._multiples = None

    def GL(self, attr):
        return getattr(GL, attr)

    def GLU(self, attr):
        return getattr(GLU, attr)

    def GLUT(self, attr):
        return getattr(GLUT, attr)

    def QtGui(self, attr):
        return getattr(QtGui, attr)

    def QtWidgets(self, attr):
        return getattr(QtWidgets, attr)

    def QtCor(self, attr):
        return getattr(QtCor, attr)

    def setGLWidgetRef(self, ref):
        self._glwdg = ref

    def cacheable(self):
        return self._cacheable

    def setMultiples(self, pos):
        '''Takes a list of positions specific to subclass shape.
        Either a list or a numpy array
        '''
        self._multiples = np.array(pos)

    def setSubdiv(self, sub):
        self._subdiv = sub

    def getSubdiv(self):
        return self._subdiv

    def setScale(self, scl):
        self._scale = scl

    def getScale(self):
        return self._scale

    def setPos(self, pos):
        self._position = pos

    def getPos(self):
        return self._position

    def setRotAV(self, rot):
        self._rotav = rot

    def getRotAV(self):
        return self._rotav

    def setRotXYZ(self, rot):
        self._rotxyz = rot

    def getRotXYZ(self):
        return self._rotxyz

    def setRGBA(self, RGBA):
        self._RGBA = RGBA

    def getRGBA(self):
        return self._RGBA

    def applyLighting(self):
        if self._RGBA:
            GL.glMaterialfv(self.GL(self._face), self.GL(self._pname), self._RGBA)
            GL.glShadeModel(self.GL(self._shademodel))

    def applyTransforms(self):
        GL.glPushMatrix()

        if self._position is not None:
            GL.glTranslatef(self._position[0], self._position[1], self._position[2])

        if self._rotav is not None:
            GL.glRotatef(self._rotav[0], self._rotav[1], self._rotav[2], self._rotav[3])

        if self._rotxyz is not None:  # independent axis rotation
            GL.glRotatef(self._rotxyz[0], 1.0, 0.0, 0.0)
            GL.glRotatef(self._rotxyz[1], 0.0, 1.0, 0.0)
            GL.glRotatef(self._rotxyz[2], 0.0, 0.0, 1.0)

        if self._scale is not None:
            GL.glScale(self._scale[0], self._scale[1], self._scale[2])

        try:
            self.applyShape()
        except:
            log.node(str(self.__class__)+':'+traceback.format_exc())

        GL.glPopMatrix()

    def applyShape(self):
        # subclass to implement specific quadrics etc...
        pass

    def run(self):
        if self._multiples is not None:
            self.applyLighting()
            for i in range(self._multiples.shape[0]):
                self._position = self._multiples[i].tolist()
                self.applyTransforms()
        else:
            self.applyLighting()
            self.applyTransforms()


class Text(GPIGLObject):

    def __init__(self):
        super(Text, self).__init__()

        self._cacheable = False
        self._text = 'Text'

        # Qt font
        self._font = 'Times New Roman'
        self._ptsize = 20

    def setFont(self, f):
        self._font = f

    def setSize(self, s):
        self._ptsize = s

    def setText(self, t):
        self._text = t

    def applyShape(self):
        '''Grab external QT rendering command.
        '''
        GL.glColor4d(*self._RGBA)
        f = QtGui.QFont(str(self._font), self._ptsize)
        p = self._position
        if self._glwdg is None:
            log.critical('Reference to GLWidget is not set! Aborting render.')
        else:
            self._glwdg.renderText(p[0], p[1], p[2], self._text, f)


class Sphere(GPIGLObject):

    def __init__(self):
        super(Sphere, self).__init__()

        # normals
        self._normals = 'GL_SMOOTH'
        self._texture = 'GL_TRUE'

        self._radius = 1.0

    def setNormals(self, n):
        self._normals = n

    def setTexture(self, t):
        self._texture = t

    def setRadius(self, r):
        self._radius = r

    def applyShape(self):
        Q=GLU.gluNewQuadric()
        GLU.gluQuadricNormals(Q, self.GL(self._normals))
        GLU.gluQuadricTexture(Q, self.GL(self._texture))
        GLU.gluSphere(Q, self._radius, self._subdiv, self._subdiv/2)
        GLU.gluDeleteQuadric( Q )

class Cylinder(GPIGLObject):

    def __init__(self):
        super(Cylinder, self).__init__()

        # normals
        self._normals = 'GL_SMOOTH'
        self._texture = 'GL_TRUE'

        self._base = 1.0
        self._top = 1.0
        self._height = 1.0
        self._z = np.array([0,0,1.0])
        self._conv = 180.0 / np.pi

        self._endToEnd = False

        self._Quadric = None
        self._f1 = None
        self._f2 = None
        self._f3 = None

    def setEndToEnd(self, val):
        self._endToEnd = val

    def setP1P2(self, p1, p2):
        p1 = np.array(p1)
        self._position = np.array(p2)

        p = p1 - self._position
        t = np.cross(self._z, p)
        self._height = np.linalg.norm(p)

        ang = self._conv * np.arccos(p[2]/self._height)
        self._rotav = (ang, t[0], t[1], t[2])

    def setBase(self, base):
        self._base = base

    def getBase(self):
        return self._base

    def setTop(self, top):
        self._top = top

    def getTop(self):
        return self._top

    def setHeight(self, h):
        self._height = h

    def getHeight(self):
        return self._height

    def setNormals(self, n):
        self._normals = n

    def setTexture(self, t):
        self._texture = t

    def setRadius(self, r):
        self._top = r
        self._base = r

    def applyShape(self):
        self._Quadric=GLU.gluNewQuadric()
        GLU.gluQuadricNormals(self._Quadric, self.GL(self._normals))
        GLU.gluQuadricTexture(self._Quadric, self.GL(self._texture))
        GLU.gluCylinder(self._Quadric, self._base, self._top, self._height, self._subdiv, 1)
        GLU.gluDeleteQuadric(self._Quadric)
        self._Quadric = None

    def cleanupCache(self):
        GLU.gluDeleteQuadric(self._Quadric)
        self._Quadric = None

    def run(self):
        # TODO: this can be made alot faster by placing these Quadric calls here, however, this needs to be compatible with the Axes object.
        # -make a better baseclass for these cases.

        #self._Quadric=GLU.gluNewQuadric()
        #self._f1 = lambda: GLU.gluQuadricNormals(self._Quadric, self.GL(self._normals))
        #self._f2 = lambda: GLU.gluQuadricTexture(self._Quadric, self.GL(self._texture))


        self.applyLighting()
        #self._f1()
        #self._f2()

        if self._multiples is not None:
            if self._endToEnd:
                for i in range(self._multiples.shape[0]-1):
                    self.setP1P2(self._multiples[i], self._multiples[i+1])
                    self.applyTransforms()
            else:
                for pos in self._multiples:
                    self._position = pos
                    self.applyTransforms()
        else:
            self.applyTransforms()

        # remove quadrics and such
        #self.cleanupCache()


class ClipPlane(GPIGLObject):

    def __init__(self):
        super(ClipPlane, self).__init__()

        # six planes max
        self._planeNo = 0

        # normal
        self._norm = 'x'

    def setNorm(self, n):
        self._norm = n

    def setPlaneNum(self, no):
        if (no < 6) and (no >= 0):
            self._planeNo = int(no)

    def getPlaneLabel(self):
        return 'GL_CLIP_PLANE'+str(self._planeNo)

    def applyShape(self):
        p = self.GL(self.getPlaneLabel())
        GL.glEnable(p)
        if self._norm == 'x':
            GL.glClipPlane(p, (1,0,0,0))
        if self._norm == 'y':
            GL.glClipPlane(p, (0,1,0,0))
        if self._norm == 'z':
            GL.glClipPlane(p, (0,0,1,0))

class Axes(GPIGLObject):

    def __init__(self):
        super(Axes, self).__init__()

        self._RGBA = None
        self._cacheable = False

        self._x = Cylinder()
        self._y = Cylinder()
        self._z = Cylinder()

        self._xl = Text()
        self._yl = Text()
        self._zl = Text()

        self._x.setRGBA((1.0, 0.0, 0.0, 1.0))  # RED
        self._y.setRGBA((0.0, 1.0, 0.0, 1.0))  # GREEN
        self._z.setRGBA((0.0, 0.0, 1.0, 1.0))  # BLUE

        self._xl.setRGBA((1.0, 0.0, 0.0, 1.0))  # RED
        self._yl.setRGBA((0.0, 1.0, 0.0, 1.0))  # GREEN
        self._zl.setRGBA((0.0, 0.0, 1.0, 1.0))  # BLUE

        self._x.setP1P2((-1,0,0), (1,0,0))
        self._y.setP1P2((0,-1,0), (0,1,0))
        self._z.setP1P2((0,0,1), (0,0,-1))  # NRZ flipped for Linux

        self._a = 0.1
        self._xl.setPos((self._x.getHeight()/4 +self._a, 0, 0))
        self._yl.setPos((0, self._y.getHeight()/4 +self._a, 0))
        self._zl.setPos((0, 0, self._z.getHeight()/4 +self._a))

        self._xl.setText('x')
        self._yl.setText('y')
        self._zl.setText('z')

    def setGLWidgetRef(self, ref):
        self._xl.setGLWidgetRef(ref)
        self._yl.setGLWidgetRef(ref)
        self._zl.setGLWidgetRef(ref)

    def setRGBA(self, c):
        pass

    def setSubdiv(self, s):
        self._x.setSubdiv(s)
        self._y.setSubdiv(s)
        self._z.setSubdiv(s)

    def setRadius(self, r):
        self._x.setP1P2((-r,0,0), (r,0,0))
        self._y.setP1P2((0,-r,0), (0,r,0))
        self._z.setP1P2((0,0,r), (0,0,-r))  # NRZ flipped for Linux

        self._xl.setPos((self._x.getHeight()/4 +self._a, 0, 0))
        self._yl.setPos((0, self._y.getHeight()/4 +self._a, 0))
        self._zl.setPos((0, 0, self._z.getHeight()/4 +self._a))

    def setTubeRadius(self, r):
        self._x.setTop(r)
        self._x.setBase(r)
        self._y.setTop(r)
        self._y.setBase(r)
        self._z.setTop(r)
        self._z.setBase(r)

        self._xl.setSize(200.0*r)
        self._yl.setSize(200.0*r)
        self._zl.setSize(200.0*r)

    def applyShape(self):
        self._x.applyLighting()
        self._x.applyTransforms()
        self._y.applyLighting()
        self._y.applyTransforms()
        self._z.applyLighting()
        self._z.applyTransforms()

        self._xl.applyLighting()
        self._xl.applyTransforms()
        self._yl.applyLighting()
        self._yl.applyTransforms()
        self._zl.applyLighting()
        self._zl.applyTransforms()

