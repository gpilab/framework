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
# Date: 2013 sep 24

import math
import gpi
from gpi.numpyqt import numpy2qimage
from gpi import QtCore, QtWidgets

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)

from scipy import ndimage


class MatplotDisplay2(gpi.GenericWidgetGroup):
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self._data = None
        self.create_main_frame()
        self.on_draw()

    # setters
    def set_val(self, data):
        '''Takes a list of npy arrays.
        '''
        if isinstance(data, list):
            self._data = data
            self.on_draw()
        else:
            return

    # getters
    def get_val(self):
        return self._data

    # support
    def create_main_frame(self):

        self.fig = Figure((5.0, 4.0), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.canvas.setFocus()

        self.mpl_toolbar = NavigationToolbar(self.canvas, self)

        self.canvas.mpl_connect('key_press_event', self.on_key_press)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.canvas)  # the matplotlib canvas
        vbox.addWidget(self.mpl_toolbar)
        self.setLayout(vbox)

    def on_draw(self):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        # self.axes.plot(self.x, self.y, 'ro')
        # self.axes.imshow(self.data, interpolation='nearest')
        # self.axes.plot([1,2,3])

        if self._data is None:
            return

        # plot each set
        # print "--------------------plot the data"
        for data in self._data:

            # check for x, y data
            if data.shape[-1] == 2:
                self.axes.plot(data[..., 0], data[..., 1], alpha=0.8, lw=2.0)
            else:
                self.axes.plot(data, alpha=0.8, lw=2.0)

        self.canvas.draw()

    def on_key_press(self, event):
        # print 'Matplotlib-> you pressed:' + str(event.key)
        # implement the default mpl key press events described at
        # http://matplotlib.org/users/navigation_toolbar.html#navigation-
        # keyboard-shortcuts
        try:
            from matplotlib.backend_bases import key_press_handler
            key_press_handler(event, self.canvas, self.mpl_toolbar)
        except:
            print("key_press_handler import failed. -old matplotlib version.")


# WIDGET
class WindowLevel(gpi.GenericWidgetGroup):

    """Provides an interface to the BasicCWFCSliders."""
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.sl = gpi.BasicCWFCSliders()
        self.sl.valueChanged.connect(self.valueChanged)
        self.pb = gpi.BasicPushButton()
        self.pb.set_button_title('reset')
        # layout
        wdgLayout = QtWidgets.QVBoxLayout()
        wdgLayout.addWidget(self.sl)
        wdgLayout.addWidget(self.pb)
        self.setLayout(wdgLayout)
        # default
        self.set_min(0)
        self.set_max(100)
        self.sl.set_allvisible(True)
        self.reset_sliders()
        self.pb.valueChanged.connect(self.reset_sliders)

    # setters
    def set_val(self, val):
        """Set multiple values with a python-dict with keys:
        level, window, floor and ceiling. -Requires integer
        values for each key.
        """
        self.sl.set_center(val['level'])
        self.sl.set_width(val['window'])
        self.sl.set_floor(val['floor'])
        self.sl.set_ceiling(val['ceiling'])

    def set_min(self, val):
        """Set min for level, window, floor and ceiling (int)."""
        self.sl.set_min(val)

    def set_max(self, val):
        """Set max for level, window, floor and ceiling (int)."""
        self.sl.set_max(val)

    # getters
    def get_val(self):
        val = {}
        val['level'] = self.sl.get_center()
        val['window'] = self.sl.get_width()
        val['floor'] = self.sl.get_floor()
        val['ceiling'] = self.sl.get_ceiling()
        return val

    def get_min(self):
        return self.sl.get_min()

    def get_max(self):
        return self.sl.get_max()

    def reset_sliders(self):
        val = {}
        val['window'] = 100
        val['level'] = 50
        val['floor'] = 0
        val['ceiling'] = 100
        self.set_val(val)


class ExternalNode(gpi.NodeAPI):

    """Display image of 2D array.  Dragging across image with left mouse button produces a graph of signal value along that line.

    INPUT:
    2D array

    WIDGETS:
    Viewport - displays image
      Double clicking on Viewport area brings up a scaling widget to change the image size, and change graphic overlay

    L W F C - (hidden by default - double click on widget area to show sliders)
              Adjust value-to-pixel brightness mapping using Level/Window or Floor/Ceiling
    Cross Section - hidden until line is drawn on image, then a graph of data values along line
    """

    def execType(self):
        return gpi.GPI_APPLOOP

    def initUI(self):

        # Widgets
        self.addWidget('DisplayBox', 'Viewport:')
        self.addWidget('WindowLevel', 'L W F C:', collapsed=True)
        self.addWidget('MatplotDisplay2', 'Cross Section', visible=False)

        # IO Ports
        self.addInPort('in', 'NPYarray', ndim=2, obligation=gpi.REQUIRED)

    def compute(self):

        # make a copy for changes
        data = self.getData('in').copy()

        # convert complex to mag
        if np.iscomplexobj(data):
            data = np.abs(data)

        # get rid of negative numbers
        if data.min() < 0.:
            data -= data.min()

        # normalize the data
        data_min = data.min()
        data_max = data.max()
        data_range = data_max - data_min

        val = self.getAttr('L W F C:', 'val')

        new_min = data_range * val['floor'] / 100.0 + data_min
        new_max = data_range * val['ceiling'] / 100.0 + data_min

        data[data < new_min] = new_min
        data[data > new_max] = new_max

        data = data - math.fabs(new_min)
        data = data / (new_max - math.fabs(new_min)) * 255

        image = numpy2qimage(data.astype(np.uint8))
        if image.isNull():
            self.log.warn("Image Viewer: cannot load image")
        else:
            self.setAttr('Viewport:', val=image)

        line = self.getAttr('Viewport:', 'line')
        if line:
            a = self.getData('in')
            if np.iscomplexobj(a):
                a = np.abs(a)

            # Make a line with "l" points
            x0, y0 = line[0]
            x1, y1 = line[1]
            l = int(np.hypot(x1 - x0, y1 - y0))
            x, y = np.linspace(x0, x1, l), np.linspace(y0, y1, l)

            # Extract the values along the line, using cubic interpolation
            arr = ndimage.map_coordinates(a, np.vstack((x, y)), order=3)

            self.setAttr('Cross Section', val=[arr])
            self.setAttr('Cross Section', visible=True)
        else:
            self.setAttr('Cross Section', visible=False)

        return(0)
