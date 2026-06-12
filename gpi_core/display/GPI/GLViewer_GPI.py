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
# Date 2013 sep 01

# NOTE THIS IS A SPECIAL MODULE, AND WILL LIKELY BE SUBSTANTIALLY REPLACED AT LATER DATE
# --> YOU SHOULD NOT USE THIS MODULE AS A TEMPLATE

import sys
import traceback
import numpy as np

import gpi
import gpi.GLObjects as glo
import gpi.logger
from gpi.defines import getKeyboardModifiers, printMouseEvent
from gpi.numpyqt import qimage2numpy
# start logger for this module
log = gpi.logger.manager.getLogger(__name__)

from gpi import QtCore, QtGui, Qimport, QtWidgets, QtOpenGL, QT_API_NAME

# Qt6: QGLWidget/QGLFormat removed — use QOpenGLWidget (in QtOpenGLWidgets) + QSurfaceFormat
try:
    from qtpy.QtOpenGLWidgets import QOpenGLWidget as _QOpenGLWidgetBase
except ImportError:
    _QOpenGLWidgetBase = QtOpenGL.QOpenGLWidget

try:
    from OpenGL import GL, GLU, GLUT
    import OpenGL.GL
    import OpenGL.GLU
    import OpenGL.GLUT

except ImportError:
    app = QtWidgets.QApplication(sys.argv)
    QtWidgets.QMessageBox.critical(None, "OpenGL grabber",
                               "PyOpenGL must be installed to run this example.")
    raise


class GPIGLWidget(_QOpenGLWidgetBase):
    xRotationChanged = gpi.Signal(int)
    yRotationChanged = gpi.Signal(int)
    zRotationChanged = gpi.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self._vScale = 1.0
        self._xPan = 0.0
        self._yPan = 0.0

        # a list of object descriptions held in dictionaries
        self._GPI_glList = glo.ObjectList()

        # trac number of exceptions thrown in problem code
        self._glError_cnt = 0

        # cache objects in a gl list
        self._glList_cache = None
        self._glList_nonCacheable = []

        # lighting
        self._default_lightPos = [0.0, 0.0, 10.0, 1.0]
        self._lightPos = self._default_lightPos[:]

        # built-in options
        self._blend = 0
        self._test = 0
        self._polyfill = 0
        self._accum_antialiasing = 0

        # self.setMouseTracking(True)

        self.checkFormat()

    def checkFormat(self):
        fmt = self.format()
        msg = "\n\talpha buffer size:" + str(fmt.alphaBufferSize()) + "\n"
        msg += "\tdepth buffer size:" + str(fmt.depthBufferSize()) + "\n"
        msg += "\tswap behavior:" + str(fmt.swapBehavior()) + "\n"
        log.node(msg)

    def setGPIglList(self, lst):
        if isinstance(lst, glo.ObjectList):
            self._GPI_glList = lst

    def getGPIglList(self):
        return self._GPI_glList

    def __del__(self):
        # cannot guarantee that the underlying object hasn't been deleted
        # before this context is made current
        try:
            self.makeCurrent()
        except:
            log.node(traceback.format_exc())
        self.resetGLCache()

    def setViewScale(self, s):
        self._vScale += s
        self.update()

    def setXRotation(self, angle):
        self.normalizeAngle(angle)

        if angle != self.xRot:
            self.xRot = angle
            self.xRotationChanged.emit(angle)
            self.update()

    def setYRotation(self, angle):
        self.normalizeAngle(angle)

        if angle != self.yRot:
            self.yRot = angle
            self.yRotationChanged.emit(angle)
            self.update()

    def setZRotation(self, angle):
        self.normalizeAngle(angle)

        if angle != self.zRot:
            self.zRot = angle
            self.zRotationChanged.emit(angle)
            self.update()

    def initializeGL(self):

        # from basic gear pos
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, self._lightPos)
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_NORMALIZE)

        # set scene to black
        GL.glClearColor(0.0, 0.0, 0.0, 0.0)

        # cache input objects
        self._clipON = False
        # self.instantiateRefs()
        self.cacheGLCommands()

    def paintGL(self):

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, self._lightPos)

        if self._blend:

            GL.glCullFace(GL.GL_BACK)
            GL.glEnable(GL.GL_CULL_FACE)
            GL.glBlendFunc(GL.GL_SRC_ALPHA_SATURATE, GL.GL_ONE)

            # something is not properly initialized for this to run
            # correctly at the beginning.
            try:
                GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            except:
                log.node(traceback.format_exc())
                self._glError_cnt += 1

            GL.glEnable(GL.GL_BLEND)
            GL.glEnable(GL.GL_POLYGON_SMOOTH)
            GL.glDisable(GL.GL_DEPTH_TEST)
        else:
            GL.glDisable(GL.GL_CULL_FACE)

            # something is not properly initialized for this to run
            # correctly at the beginning.
            try:
                GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            except:
                log.node(traceback.format_exc())
                self._glError_cnt += 1

            GL.glDisable(GL.GL_BLEND)
            GL.glDisable(GL.GL_POLYGON_SMOOTH)
            GL.glEnable(GL.GL_DEPTH_TEST)

        if self._polyfill == 2:
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_POINT)
        elif self._polyfill == 1:
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
        else:
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

        if self._accum_antialiasing:
            # accumulation buffer antialiasing not supported in QOpenGLWidget;
            # fall through to standard paintScene
            self.paintScene()
        else:
            self.paintScene()

        if self._test:
            pass
        else:
            pass

        # force all commands to complete
        GL.glFlush()

    def paintScene(self):
        '''Does the actuall object rendering calls.
        '''
        # rotate view
        GL.glPushMatrix()
        GL.glRotatef(self.xRot / 16.0, 1.0, 0.0, 0.0)
        GL.glRotatef(self.yRot / 16.0, 0.0, 1.0, 0.0)
        GL.glRotatef(self.zRot / 16.0, 0.0, 0.0, 1.0)

        # pan
        mtx = np.array(GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX))
        A = mtx[0:3, 0:2]
        x = np.transpose(np.array([[self._xPan, self._yPan]]))
        b = np.dot(A, x)
        GL.glTranslatef(b[0], b[1], b[2])

        # zoom
        GL.glScale(self._vScale, self._vScale, self._vScale)

        # render all non-cacheable first
        if len(self._glList_nonCacheable):
            for desc in self._glList_nonCacheable:
                desc.run()

        # use cached list for mouse interactions
        try:
            GL.glCallList(self._glList_cache)
        except:
            log.node(traceback.format_exc())
            self._glError_cnt += 1

        # rotate view
        GL.glPopMatrix()

    def resizeGL(self, width, height):
        side = min(width, height)
        if side < 0:
            return

        GL.glViewport((width - side) // 2, (height - side) // 2, side, side)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glFrustum(-1.0, +1.0, -1.0, 1.0, 5.0, 60.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glTranslatef(0.0, 0.0, -40.0)

    def resetGLCache(self):
        '''reset both cacheable and non-cacheable items
        '''
        if self._glList_cache:
            GL.glDeleteLists(self._glList_cache, 1)
        self._glList_cache = None
        self._glList_nonCacheable = []

    def instantiateRefs(self):
        '''Run thru all objects calling their instantiateLibs() method.
        '''
        for desc in self._GPI_glList:
            desc.instantiateRefs()
            if type(desc) is glo.ClipPlane:
                print("enable clipping", desc.getPlaneNumTr())
                GL.glEnable(desc.getPlaneNumTr())

    def cacheGLCommands(self):
        '''Cache object commands.
        '''
        if self._glList_cache:
            self.resetGLCache()

        self._glList_cache = GL.glGenLists(1)
        GL.glNewList(self._glList_cache, GL.GL_COMPILE)

        # cache all commands in obj list
        for desc in self._GPI_glList.getCacheableList():
            desc.run()

        # special objects
        for plane, desc in self._GPI_glList.getClipPlanes().items():
            print('render: ' + plane)
            desc.run()

        GL.glEndList()

        # get all non-cacheables
        self._glList_nonCacheable = self._GPI_glList.getNonCacheableList()
        if len(self._glList_nonCacheable):
            for desc in self._glList_nonCacheable:
                desc.setGLWidgetRef(self)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.setViewScale(0.1)
        else:
            self.setViewScale(-0.1)

    def mousePressEvent(self, event):
        self.lastPos = event.pos()

    def mouseMoveEvent(self, event):
        dx = int(event.position().x()) - self.lastPos.x()
        dy = int(event.position().y()) - self.lastPos.y()

        printMouseEvent(event)
        modifiers = getKeyboardModifiers()
        modmidbutton_event = (event.buttons() & QtCore.Qt.RightButton
                              and modifiers & QtCore.Qt.ShiftModifier)

        if event.buttons() & QtCore.Qt.LeftButton:
            self._xPan += dx * 0.05
            self._yPan += -dy * 0.05
            self.update()
        elif modmidbutton_event:
            self.setXRotation(self.xRot + 8 * dy)
            self.setYRotation(self.yRot + 8 * dx)
        elif event.buttons() & QtCore.Qt.MiddleButton:
            self._lightPos[0] += dx * 0.05
            self._lightPos[1] += -dy * 0.05
            self.update()
        elif event.buttons() & QtCore.Qt.RightButton:
            self.setXRotation(self.xRot + 8 * dy)
            self.setZRotation(self.zRot + 8 * dx)

        self.lastPos = event.pos()

    def resetViewingWindow(self):
        '''reset pan, zoom, rotate
        '''
        self._xPan = 0.0
        self._yPan = 0.0
        self._vScale = 1.0
        self.xRot = 0.0
        self.yRot = 0.0
        self.zRot = 0.0
        self._lightPos = self._default_lightPos[:]

    def xRotation(self):
        return self.xRot

    def yRotation(self):
        return self.yRot

    def zRotation(self):
        return self.zRot

    def normalizeAngle(self, angle):
        while (angle < 0):
            angle += 360 * 16

        while (angle > 360 * 16):
            angle -= 360 * 16

    def setBlend(self, val):
        self._blend = val
        self.update()

    def setTest(self, val):
        self._test = val
        self.update()

    def setPolyFill(self, val):
        self._polyfill = val
        self.update()

    def setAntiAliasing(self, val):
        self._accum_antialiasing = val
        self.update()


class OpenGLWindow(gpi.GenericWidgetGroup):

    """Provides an embedded GL window.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        if QtOpenGL is None:
            raise ImportError("QtOpenGL not available in the current Qt "
                              "package ({})".format(QT_API_NAME))
        super().__init__(title, parent)

        # Configure surface format before creating the widget
        fmt = QtGui.QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        fmt.setAlphaBufferSize(8)
        fmt.setSwapBehavior(QtGui.QSurfaceFormat.SwapBehavior.DoubleBuffer)

        self.glWidget = GPIGLWidget()
        self.glWidget.setFormat(fmt)

        self.glWidgetArea = QtWidgets.QScrollArea()
        self.glWidgetArea.setWidget(self.glWidget)
        self.glWidgetArea.setWidgetResizable(True)
        self.glWidgetArea.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.glWidgetArea.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff)
        self.glWidgetArea.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                        QtWidgets.QSizePolicy.Ignored)
        self.glWidgetArea.setMinimumSize(50, 50)

        xSlider = self.createSlider(self.glWidget.xRotationChanged,
                                    self.glWidget.setXRotation)
        ySlider = self.createSlider(self.glWidget.yRotationChanged,
                                    self.glWidget.setYRotation)
        zSlider = self.createSlider(self.glWidget.zRotationChanged,
                                    self.glWidget.setZRotation)

        glBlend = self.createCheckOption('PolySmooth', self.glWidget.setBlend)
        polyFill = self.createCheckOption(
            'Poly-Fill/Line/Point', self.glWidget.setPolyFill, tristate=True)

        # Accumulation buffer antialiasing not supported in QOpenGLWidget (modern GL)
        antialiasing = self.createCheckOption(
            'AntiAliasing', self.glWidget.setAntiAliasing, initstate=0, enabled=False)

        hardwareRender = QtWidgets.QLabel()
        hardwareRender.setFrameStyle(2)
        hardwareRender.setText('Rendering: Hardware')

        centralLayout = QtWidgets.QGridLayout()
        centralLayout.addWidget(self.glWidgetArea, 2, 0, 4, 4)
        centralLayout.setRowStretch(2, 2)
        centralLayout.addWidget(polyFill, 1, 0, 1, 1)
        centralLayout.addWidget(glBlend, 1, 1, 1, 1)
        centralLayout.addWidget(antialiasing, 1, 2, 1, 1)
        centralLayout.addWidget(hardwareRender, 0, 0, 1, 1)

        self.setLayout(centralLayout)

        xSlider.setValue(15 * 16)
        ySlider.setValue(345 * 16)
        zSlider.setValue(0 * 16)

        self.resize(400, 300)

    # setters
    def set_val(self, val):
        """set a list of GL command list interface (dict)."""
        self.glWidget.setGPIglList(val)
        self.glWidget.update()

    def set_resetView(self, val):
        """reset the viewing window"""
        self.glWidget.resetViewingWindow()

    def set_imageARGB(self, val):
        pass

    def set_imageBGRA(self, val):
        pass

    # getters
    def get_val(self):
        """get the held list of GPI-GL objects"""
        return self.glWidget.getGPIglList()

    def get_resetView(self):
        '''This is a one-shot operation, so there is nothing to get'''
        pass

    def get_imageARGB(self):
        '''Render a copy of the GL window and convert to NPY array.
        '''
        fbuff = self.glWidget.grabFramebuffer()
        arr = qimage2numpy(fbuff)
        arr = arr[..., ::-1]
        return arr

    def get_imageBGRA(self):
        '''Render a copy of the GL window and convert to NPY array.  BGRA is
        the fastest since it native.
        '''
        fbuff = self.glWidget.grabFramebuffer()
        arr = qimage2numpy(fbuff)
        return arr

    # support
    def renderIntoPixmap(self):
        size = self.getSize()

        if size.isValid():
            image = self.glWidget.grabFramebuffer()
            pixmap = QtGui.QPixmap.fromImage(image).scaled(size)
            self.setPixmap(pixmap)

    def grabFrameBuffer(self):
        image = self.glWidget.grabFramebuffer()
        self.setPixmap(QtGui.QPixmap.fromImage(image))

    def clearPixmap(self):
        self.setPixmap(QtGui.QPixmap())

    def about(self):
        QtWidgets.QMessageBox.about(self, "About Grabber",
                                "The <b>Grabber</b> example demonstrates two approaches for "
                                "rendering OpenGL into a Qt pixmap.")

    def createActions(self):
        self.renderIntoPixmapAct = QtWidgets.QAction("&Render into Pixmap...",
                                                 self, shortcut="Ctrl+R", triggered=self.renderIntoPixmap)

        self.grabFrameBufferAct = QtWidgets.QAction("&Grab Frame Buffer", self,
                                                shortcut="Ctrl+G", triggered=self.grabFrameBuffer)

        self.clearPixmapAct = QtWidgets.QAction("&Clear Pixmap", self,
                                            shortcut="Ctrl+L", triggered=self.clearPixmap)

        self.exitAct = QtWidgets.QAction("E&xit", self, shortcut="Ctrl+Q",
                                     triggered=self.close)

        self.aboutAct = QtWidgets.QAction("&About", self, triggered=self.about)

        self.aboutQtAct = QtWidgets.QAction("About &Qt", self,
                                        triggered=QtWidgets.QApplication.instance().aboutQt)

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.renderIntoPixmapAct)
        self.fileMenu.addAction(self.grabFrameBufferAct)
        self.fileMenu.addAction(self.clearPixmapAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)

    def createCheckOption(self, title, setterSlot, tristate=False, initstate=0, enabled=True):
        checkbox = QtWidgets.QCheckBox(title)
        checkbox.setTristate(tristate)
        checkbox.setCheckState(initstate)
        checkbox.stateChanged.connect(setterSlot)
        if not enabled:
            checkbox.setEnabled(False)
        return checkbox

    def createSlider(self, changedSignal, setterSlot):
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(0, 360 * 16)
        slider.setSingleStep(16)
        slider.setPageStep(15 * 16)
        slider.setTickInterval(15 * 16)
        slider.setTickPosition(QtWidgets.QSlider.TicksRight)

        slider.valueChanged.connect(setterSlot)
        changedSignal.connect(slider.setValue)

        return slider

    def setPixmap(self, pixmap):
        self.pixmapLabel.setPixmap(pixmap)
        size = pixmap.size()

        if size - QtCore.QSize(1, 0) == self.pixmapLabelArea.maximumViewportSize():
            size -= QtCore.QSize(1, 0)

        self.pixmapLabel.resize(size)

    def getSize(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "Grabber",
                                              "Enter pixmap size:", QtWidgets.QLineEdit.Normal,
                                              "%d x %d" % (self.glWidget.width(), self.glWidget.height()))

        if not ok:
            return QtCore.QSize()

        regExp = QtCore.QRegularExpression(r"([0-9]+) *x *([0-9]+)")
        match = regExp.match(text)
        if match.hasMatch():
            width = int(match.captured(1))
            height = int(match.captured(2))
            if width > 0 and width < 2048 and height > 0 and height < 2048:
                return QtCore.QSize(width, height)

        return self.glWidget.size()


class ExternalNode(gpi.NodeAPI):

    """Prototype 3D GL Viewer
    MOUSE EVENTS:
      Left Button: translate object
      Middle Button: move light source
      Scroll wheel: zoom
      Right Button: rotate (hold down shift key for different axis of rotation)

    INPUT:
    GL Object List

    OUTPUT:
    2D ARGB (stored as 3D array, with last dim of length 4, uint (byte) data for 0-255 per channel)
            This is an image of what is rendered in the Viewport, useful for gluing together images to make movies

    WIDGETS:
    Viewport
      Poly-Fill Line/Point - toggles between showing polygons, lines, or points (depends on how objects are created)
      PolySmooth - for smoothing polygons, implemenation will vary
      AntiAliasing - this option needs to be debugged further
      Pixmap - shows the rendered pixmap.  In this area, the scene is manipulated as follows:
        Left Mouse Button Drag: translate object
        Middle Mouse Button Drag: translate light source
        Middle Mouse Wheel Scroll: Zoom
        Right Mouse Button Drag: Rotate Object about 2 axes.
              Hold down Shift key BEFORE selecting Right mouse button to change 2nd axis of rotation

    Reset - resets rotation, translation, zoom to original values (x axis Horizontal, y axis vertical, z axis through-plane)

    Compute/Nudge - sometimes needed to update renderer

    Set Output - makes output port continually reflect image rendered in Viewport as ARGB data

    KNOWN ISSUES:
    Still needs to be tested on many platforms, bugs likely
    On Linux platform, Z axis location occasionally seems to be improperly interpreted
    """

    def execType(self):
        return gpi.GPI_APPLOOP

    def initUI(self):

        # Widgets
        self.addWidget('OpenGLWindow', 'Viewport')
        self.addWidget('PushButton', 'Reset')
        self.addWidget('PushButton', 'Compute/Nudge')
        self.addWidget('PushButton', 'Set Output', toggle=True)
        #self.addWidget('Slider', 'Background', min=0, max=255, val=0)

        # IO Ports
        self.addInPort(
            'GL Object Descriptions', 'GLOList', obligation=gpi.OPTIONAL)
        self.addOutPort('Rendered RGBA', 'NPYarray')

    def compute(self):

        reset = self.getVal('Reset')
        setoutput = self.getVal('Set Output')

        gpi_glist = glo.ObjectList(self.getData('GL Object Descriptions'))

        if reset:
            self.setAttr('Viewport', resetView=reset)
        self.setAttr('Viewport', val=gpi_glist) # setting the 'val' forces a redraw

        if setoutput:
            img = self.getAttr('Viewport', 'imageARGB')
            # This is a hack to add alpha channel
            alpha_col = 255*np.ones((img.shape[0],img.shape[1],1),dtype = np.uint8)
            img2 = np.concatenate((img,alpha_col),axis=2)
            self.setData('Rendered RGBA', img2)
        else:
            self.setData('Rendered RGBA', None)

        return(0)
