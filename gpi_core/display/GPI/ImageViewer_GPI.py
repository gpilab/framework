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

# Author: Jim Pipe / Nick Zwart
# Date: 2013 Sep 01

import gpi
from gpi import QtGui, QtWidgets, QtCore
import numpy as np

# WIDGET

import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
from gpi.defines import GPI_PKG_PATH
import scipy.ndimage as ndimage
import math
from PIL import Image
from matplotlib import cm

def truncate(number, digits):
    try:
        stepper = 10.0 ** digits
        return math.trunc(stepper * number) / stepper
    except:
        formatting = '{:.' + str(digits) + 'f}'
        return formatting.format(number)


class Levels(QtWidgets.QWidget):
    valueChanged = gpi.Signal()

    def __init__(self, parent=None):
        super(Levels, self).__init__(parent)

        self.min_label = QtWidgets.QLabel("Min")
        self.min_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.max_label = QtWidgets.QLabel("Max")
        self.max_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.min_spin = gpi.GPIDoubleSpinBox()
        self.min_spin.setSingleStep(0.1)
        self.min_spin.setKeyboardTracking(False)
        self.max_spin = gpi.GPIDoubleSpinBox()
        self.max_spin.setSingleStep(0.1)
        self.max_spin.setKeyboardTracking(False)

        min_layout = QtWidgets.QHBoxLayout()
        min_layout.addWidget(self.min_label)
        min_layout.addWidget(self.min_spin)

        max_layout = QtWidgets.QHBoxLayout()
        max_layout.addWidget(self.max_label)
        max_layout.addWidget(self.max_spin)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(min_layout)
        layout.addLayout(max_layout)

        self.min_spin.setMinimumWidth(100)
        self.max_spin.setMinimumWidth(100)
        self.set_min(float('-inf'))
        self.set_max(float('inf'))

        self.min_spin.valueChanged.connect(self.valueChanged)
        self.max_spin.valueChanged.connect(self.valueChanged)

        self.setLayout(layout)

    def set_min(self, minl):
        self.min_spin.setMinimum(minl)
        self.max_spin.setMinimum(minl)

    def set_max(self, maxl):
        self.min_spin.setMaximum(maxl)
        self.max_spin.setMaximum(maxl)

        if maxl > 10:
            self.min_spin.setSingleStep(1)
            self.max_spin.setSingleStep(1)

    def set_min_level(self, minl):
        self.min_spin.setValue(minl)

    def set_max_level(self, maxl):
        self.max_spin.setValue(maxl)

    def set_levels(self, minl, maxl):
        self.set_min_level(minl)
        self.set_max_level(maxl)

    def get_min_level(self):
        return self.min_spin.value()

    def get_max_level(self):
        return self.max_spin.value()

    def get_levels(self):
        return self.get_min_level(), self.get_max_level()

    def enable(self):
        self.min_spin.setDisabled(False)
        self.max_spin.setDisabled(False)

    def disable(self):
        self.min_spin.setDisabled(True)
        self.max_spin.setDisabled(True)


class DoubleSpinHorizontalBox(QtWidgets.QWidget):
    valueChanged = gpi.Signal(float)

    def __init__(self, title="", parent=None):
        super(DoubleSpinHorizontalBox, self).__init__(parent)

        self.label = QtWidgets.QLabel(title)
        self.double_spin = gpi.GPIDoubleSpinBox()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.double_spin)

        self.double_spin.setMinimumWidth(100)

        self.double_spin.valueChanged.connect(self.valueChanged)

        self.setLayout(layout)

    # setters
    def set_keyboardtracking(self, val):
        self.double_spin.setKeyboardTracking(val)

    def set_max(self, val):
        self.double_spin.setMaximum(val)

    def set_min(self, val):
        self.double_spin.setMinimum(val)

    def set_val(self, val):
        self.double_spin.setValue(val)

    def set_label(self, val):
        if val != '':
            self.spin_label.setText(val)
            self.spin_label.setVisible(True)
        else:
            self.spin_label.setVisible(False)

    def set_wrapping(self, val):
        self.double_spin.setWrapping(val)

    def set_decimals(self, val):
        self.double_spin.setDecimals(val)

    def set_singlestep(self, val):
        self.double_spin.setSingleStep(val)

    def set_immediate(self, val):
        self._immediate = val

    # getters
    def get_keyboardtracking(self):
        return self.double_spin.keyboardTracking()

    def get_max(self):
        return self.double_spin.maximum()

    def get_min(self):
        return self.double_spin.minimum()

    def get_val(self):
        return self.double_spin.value()

    def get_label(self):
        return self.spin_label.text()

    def get_wrapping(self):
        return self.double_spin.wrapping()

    def get_decimals(self):
        return self.double_spin.decimals()

    def get_singlestep(self):
        return self.double_spin.singleStep()

    def get_immediate(self):
        return self._immediate


class Image_Viewer(gpi.GenericWidgetGroup):
    """Creates an Image Viewer widget that accepts an ndarray and converts into an RGBA image for display

    Parameters
    ----------
    title : str
        Title of the node

    Attributes
    ----------
    pglayout : pyqtgraph.GraphicsLayoutWidget
        The main pyqtgraph layout that

    viewbox : pyqtgraph.ViewBox
        The name of the animal

    image : pyqtgraph.ImageItem
        image item that containts the RGBA data and is added to the viewbox to display

    histogram : gpi.widgets.Histogram
        A histogram to window/level & color map the image

    data : ndarray
        The data used for generating the image

    image_data:
        The RGBA data generated from data and use for image

    p: gpi.NodeAPI
        The parent GPI node calling the ImageViewer class

    data_label: QWidget.QLabel
        Displays the mouse hover position with the `data` value at the position

    stats_label: QWidget.QLabel
        Displays the `data` statistics
    """
    valueChanged = gpi.Signal(bool)

    def __init__(self, title, parent=None):
        super(Image_Viewer, self).__init__(title, parent)

        self.data = None
        self.slice_data = None
        self.image_data = None
        self.sval = 0  # scalar display
        self.zval = 0  # zero ref
        self.gamma = 1  # zero ref
        self.range_min = 0
        self.range_max = 0
        self.fix_range = False
        self.update = False
        self.slice = 1
        self.slice_max = 1
        self.sliceable = 1
        self.slice_dim = 0
        self.interpolate = False
        self.tool = "Mouse"
        self.resize = False
        self.window_leveling = False
        self.wl_viewbox_x = 0
        self.wl_viewbox_y = 0
        self.ROIS = None
        self.free_hand_roi = None
        self.initiated = False
        self.mask_image_data = None

        # initializing pyqtgraph layout to get a viewbox to add image data and histogram
        pg.setConfigOption('imageAxisOrder', 'row-major')
        self.set_background_color()
        self.pglayout = pg.GraphicsLayoutWidget()
        self.pglayout.setMinimumHeight(500)

        # viewbox
        self.viewbox = self.pglayout.addViewBox()
        self.viewbox.invertY()
        self.viewbox.setAspectLocked()
        self._setup_viewbox_menu()
        wheel_handler = self.viewbox.wheelEvent
        self.viewbox.wheelEvent = lambda event: self.scroll_to_slice(event, wheel_handler)
        self.viewbox.scene().sigMouseMoved.connect(self.mouse_move)
        release_handler = self.viewbox.scene().mouseReleaseEvent
        press_handler = self.viewbox.scene().mousePressEvent
        self.viewbox.scene().mouseReleaseEvent = lambda event: self.mouse_release(event, release_handler)
        self.viewbox.scene().mousePressEvent = lambda event: self.mouse_press(event, press_handler)

        # image
        self.image = pg.ImageItem()
        self.viewbox.addItem(self.image)
        self.image_exporter = pg.exporters.ImageExporter(self.viewbox)  # exporter for image

        # histongram & LUT (window/leveling & colormap)
        self.histogram = pg.HistogramLUTItem()
        self.histogram.sigLevelsChanged.connect(self.levels_changed)
        self.histogram.sigLookupTableChanged.connect(lambda e: self.set_update())
        self.pglayout.addItem(self.histogram)
        self._setup_histogram_menu()

        # setup data & stats labels
        self.data_label = QtWidgets.QLabel()
        self.stats_label = QtWidgets.QLabel()
        self.stats_layout = QtWidgets.QVBoxLayout()
        self.stats_layout.addWidget(self.data_label)
        self.stats_layout.addWidget(self.stats_label)
        self.levels_label = QtWidgets.QLabel()
        self.levels_label.setAlignment(QtCore.Qt.AlignRight)

        # setup the image viewer widgets into a grid widget
        wdgLayout = QtWidgets.QGridLayout()
        self.buttons  = self.ROI_buttons()
        wdgLayout.addLayout(self.buttons, 0, 0)
        wdgLayout.addWidget(self.pglayout, 1, 0)
        wdgLayout.addLayout(self.stats_layout, 2, 0)
        wdgLayout.addWidget(self.levels_label, 2, 0)
        self.setLayout(wdgLayout)

    # setters ========================================

    def set_image(self, data):
        """Set up the image item to display in the viewbox

        Parameters
        ----------
        data : RGBA numpy array
        """
        if self.mask_image_data is None: self.image_data = data
        self.image.setImage(data)
        # self.viewbox.autoRange()
        self.image.setLevels((0, 255))
        if self.interpolate: self.interpolate_image(True)
        self.p.setData('out', data)

    def set_parent(self, parent):
        """Set the parent node that initiated this class to get access to it

        Parameters
        ----------
        parent : gpi.NodeAPI
        """
        self.p = parent

    def set_sign(self, on):
        self.sval = 0
        if on: self.sval = 2
        self.set_update()

    def set_zval(self, zval):
        self.zval = zval
        self.set_update()

    def set_gamma(self, gamma):
        self.gamma = gamma
        self.set_update()

    def range_changed(self):
        self.range_min, self.range_max = self.range_widget.get_levels()
        self.histogram.setLevels(self.range_min, self.range_max)

    def levels_changed(self):
        self.range_min, self.range_max = self.histogram.getLevels()
        self.range_widget.set_levels(self.range_min, self.range_max)
        if not self.update and self.initiated and not self.fix_range:
            self.set_fix_range(True)
            self.fix_range_menu.setChecked(True)

        if self.update: return
        self.set_update()

    def set_range_min(self, range_min):
        self.range_min = range_min
        self.histogram.setLevels(self.range_min, self.range_max)

    def set_range_max(self, range_max):
        self.range_max = range_max
        self.histogram.setLevels(self.range_min, self.range_max)

    def set_fix_range(self, on):
        self.fix_range = on
        if on:
            self.range_widget.enable()
            self.histogram.region.setBrush(color=(255, 0, 0, 50))
            self.fix_range_min = self.range_min
            self.fix_range_max = self.range_max
        else:
            self.range_widget.disable()
            self.histogram.region.setBrush(color=(0, 0, 255, 50))

        self.set_update()

    # getters ========================================

    def get_sign(self):
        return self.sval

    def get_zval(self):
        return self.zval

    def get_gamma(self):
        return self.gamma

    def get_range_min(self):
        return self.range_min

    def get_range_max(self):
        return self.range_max

    def get_fix_range(self):
        return self.fix_range

    def get_update(self):
        return None
    
    def get_refresh(self):
        return None

    # data statistics ========================================

    def data_value(self, x, y):
        """Get the data value at x,y
        
        Parameters
        ----------
        x : int (positive)
        y : int (positive)
        """
        try:
            if self.slice_data is None:
                return truncate(self.slice_data[int(x), int(y)], 3)
            else:
                return truncate(self.slice_data[int(x), int(y)], 3)
        except:
            return 0
    

    def update_data_value(self, x, y):
        """Show the data value corresponding to the mouse cursur position on the image displayed"""
        if self.slice_data is None: return
        
        x_b = self.slice_data.shape[0]
        y_b = self.slice_data.shape[1]
        
        # make sure x an y are in the boundries of the data
        if x < 0 or x >= x_b or y < 0 or y >= y_b :
            if self.sliceable:
                self.data_label.setText(f"3D x:{x}/y:{y}/z:{self.slice - 1}  Value: 0")
            else:
                self.data_label.setText(f"2D x:{x}/y:{y}  Value: 0")
            return
        else:
            if self.sliceable:
                self.data_label.setText(f"3D x:{x}/y:{y}/z:{self.slice - 1}  Value: {str(self.data_value(x, y))}")
            else:
                self.data_label.setText(f"2D x:{x}/y:{y}  Value: {str(self.data_value(x, y))}")

    def data_stats(self, data):
        """Get data stats into a formatted string
        
        Parameters
        ----------
        data: numpy array
        """
        if not len(data): return ""
        
        dmin = truncate(data.min(), 3)
        dmax = truncate(data.max(), 3)
        dmean = truncate(data.mean(), 3)
        dstd = truncate(data.std(), 3)
        d1 = list(data.shape)

        stats = "dimensions: "+str(d1)+"\n" \
               "min: "+str(dmin)+", max: "+str(dmax)+"\n" \
               "mean: "+str(dmean)+"\n" \
               "std: "+str(dstd)

        return stats

    def leveling_info(self):
        """Shows the leveling information"""

        zero_ref = "---"
        if self.zval == 1: zero_ref = '0->'
        if self.zval == 2: zero_ref = '-0-'
        if self.zval == 3: zero_ref = '<-0'
        info = f"Gamma: {truncate(self.gamma, 3)}\nZero Ref: {zero_ref}"

        return info

    # update ========================================
    def set_update(self, data=None):
        # get extra dimension parameters and modify data
        if data is None: data = self.data
        if data is None: return
        self.data = data
        
        self.update = True
        if not self.fix_range: self._setup_histogram_levels(data)
        self.update = False

        image_data = None

        cval = self.p.getVal('Complex Display')
        
        if np.iscomplexobj(data) and cval == 4: 
            self.sign.setVisible(False)
        else:
            self.sign.setVisible(True)

        if np.iscomplexobj(data):
            l_data = data
            if cval == 0: # Real
                l_data = np.real(data)
            elif cval == 1: # Imag
                l_data = np.imag(data)
            elif cval == 2: # Mag
                l_data = np.abs(data)
            elif cval == 3: # Phase
                l_data = np.angle(data, deg=True)
            
            self.update = True
            if not self.fix_range: self._setup_histogram_levels(l_data)
            self.update = False
        else:
            self.update = True
            if not self.fix_range: self._setup_histogram_levels(data)
            self.update = False

        dimfunc = self.p.getVal('Extra Dimension')
        dimval = self.p.getVal('Slice/Tile Dimension')
        if self.mask_image_data is not None and (self.mask_image_data[2] != dimfunc or self.mask_image_data[3] != dimval):
            self.mask_image_data = None

        self.slice_dim = dimval
        if data.ndim == 2 and self.ROIS == None: self.ROIS = [[[]]]
        if data.ndim == 3 and dimfunc < 2:
            if self.ROIS == None: self.ROIS = [[[] for i in range(data.shape[2])] for i in range(3)]
            if dimfunc == 0:  # slice data
                self.sliceable = True
                self.slice_max = data.shape[dimval]
                slval = self.p.getVal('Slice')-1

                self.hide_rois(self.slice - 1)
                self.slice = self.p.getVal('Slice')
                self.show_rois(self.slice - 1)

                if self.mask_image_data is not None and self.mask_image_data[4] != slval + 1:
                    self.mask_image_data = None
                if dimval == 0:
                    data = data[slval, ...]
                elif dimval == 1:
                    data = data[:, slval, :]
                else:
                    data = data[..., slval]
            else:  # tile data
                self.sliceable = False
                ncol = self.p.getVal('# Columns')
                nrow = self.p.getVal('# Rows')

                # add some blank tiles
                data = np.rollaxis(data, dimval)
                N, xres, yres = data.shape
                N_new = ncol * nrow
                pad_vals = ((0, N_new - N), (0, 0), (0, 0))
                data = np.pad(data, pad_vals, mode='constant')

                # from http://stackoverflow.com/a/13990648/333308
                data = np.reshape(data, (nrow, ncol, xres, yres))
                data = np.swapaxes(data, 1, 2)
                data = np.reshape(data, (nrow*xres, ncol*yres))

        # Read in parameters, make a little floor:ceiling adjustment
        gamma = self.gamma
        lval = self.p.getAttr('L W F C:', 'val')
        cval = self.p.getVal('Complex Display')

        cmap = self.p.getVal('Color Map')
        sval = self.sval
        zval = self.zval
        fval = self.fix_range
        rmin = self.range_min
        rmax = self.range_max

        self.levels_label.setText(self.leveling_info())

        flor = 0.01*lval['floor']
        ceil = 0.01*lval['ceiling']
        if ceil == flor:
            if ceil == 1.:
                flor = 0.999
            else:
                ceil += 0.001

        # SHOW COMPLEX DATA
        if np.iscomplexobj(data) and cval == 4:
            self.stats_label.setText(self.data_stats(data.T))
            self.slice_data = data.T
            mag = np.abs(data)
            phase = np.angle(data, deg=True)

            # normalize the mag
            data_min = 0.
            if fval:
                data_max = rmax
            else:
                data_max = mag.max()
                self.update = True
                self.set_range_max(data_max)
                self.update = False

            data_range = data_max-data_min
            dmask = np.ones(data.shape)
            new_min = data_range*flor + data_min
            new_max = data_range*ceil + data_min
            mag = np.clip(mag, new_min, new_max)
            data_min = -20000
            if new_max > new_min:
                if (gamma == 1):  # Put in check for gamma=1, the common use case, just to save time
                    mag = (mag - new_min)/(new_max-new_min)
                else:
                    mag = pow((mag - new_min)/(new_max-new_min), gamma)
            else:
                mag = np.ones(mag.shape)

            # ADD BORDERS
            edgpix = self.p.getVal('Edge Pixels')
            blkpix = self.p.getVal('Black Pixels')
            if (edgpix + blkpix) > 0:
                # new image will be h2 x w2
                # frame defines edge pixels to paint with phase table
                h, w = mag.shape
                h2 = h + 2*(edgpix+blkpix)
                w2 = w + 2*(edgpix+blkpix)
                mag2 = np.zeros((h2, w2))
                phase2 = np.zeros((h2, w2))
                frame = np.zeros((h2, w2)) == 1
                frame[0:edgpix, :] = frame[h2-edgpix:h2, :] = True
                frame[:, 0:edgpix] = frame[:, w2-edgpix:w2] = True

                mag2[edgpix+blkpix:edgpix+blkpix+h,
                    edgpix+blkpix:edgpix+blkpix+w] = mag
                mag2[frame] = 1

                phase2[edgpix+blkpix:edgpix+blkpix+h,
                    edgpix+blkpix:edgpix+blkpix+w] = phase
                xloc = np.tile(np.linspace(-1., 1., w2), (h2, 1))
                yloc = np.transpose(np.tile(np.linspace(1., -1., h2), (w2, 1)))
                phase2[frame] = np.degrees(
                    np.arctan2(xloc[frame], yloc[frame]))

                mag = mag2
                phase = phase2

            # now colorize!
            if cmap == 0: # HSV
                phase_cmap = cm.hsv
            elif cmap == 1: # HSL
                try:
                    import seaborn as sns
                except:
                    self.log.warn("Seaborn (required for HSL map) not available! Falling back on HSV.")
                    phase_cmap = cm.hsv
                else: # from http://stackoverflow.com/a/34557535/333308
                    import matplotlib.colors as col
                    hlsmap = col.ListedColormap(sns.color_palette("hls", 256))
                    phase_cmap = hlsmap
            elif cmap == 2: #HUSL
                try:
                    import seaborn as sns
                except:
                    self.p.log.warn("Seaborn (required for HUSL map) not available! Falling back on HSV.")
                    phase_cmap = cm.hsv
                else: # from http://stackoverflow.com/a/34557535/333308
                    import matplotlib.colors as col
                    huslmap = col.ListedColormap(sns.color_palette("husl", 256))
                    phase_cmap = huslmap
            elif cmap == 3: # coolwarm
                phase_cmap = cm.coolwarm

            mag_norm = mag
            phase_norm = (phase + 180) / 360
            # phase shift to match old look better
            if cmap != 3:
                phase_norm = (phase_norm - 1/3) % 1
            colorized = 255 * cm.gray(mag_norm) * phase_cmap(phase_norm)
            red = colorized[...,0]
            green = colorized[...,1]
            blue = colorized[...,2]
            alpha = colorized[...,3]
        
        # DISPLAY SCALAR DATA
        elif dimfunc != 2:

            if np.iscomplexobj(data):
                if cval == 0: # Real
                    data = np.real(data)
                elif cval == 1: # Imag
                    data = np.imag(data)
                elif cval == 2: # Mag
                    data = np.abs(data)
                elif cval == 3: # Phase
                    data = np.angle(data, deg=True)
                
            self.histogram.gradient.show()
            if sval == 1: # Mag
                data = np.abs(data)
            elif sval == 2: # Sign
                self.histogram.gradient.hide()
                sign = np.sign(data)
                data = np.abs(data)

            self.slice_data = data.T
            self.stats_label.setText(self.data_stats(data.T))

            # normalize the data
            if fval:
                data_min = rmin
                data_max = rmax
            else:
                data_min = data.min()
                data_max = data.max()

            self.update = True
            if sval != 2:
                if zval == 1:
                    data_min = 0.
                elif zval == 2:
                    data_max = max(abs(data_min),abs(data_max))
                    data_min = -data_max
                elif zval == 3:
                    data_max = 0.
                data_range = data_max-data_min
                self.set_range_min(data_min)
                self.set_range_max(data_max)
            else:
                data_min = 0.
                data_max = max(abs(data_min),abs(data_max))
                data_range = data_max
                self.set_range_min(-data_range)
                self.set_range_max(data_range)
            self.update = False

            dmask = np.ones(data.shape)
            new_min = data_range*flor + data_min
            new_max = data_range*ceil + data_min
            data = np.minimum(np.maximum(data,new_min*dmask),new_max*dmask)

            if new_max > new_min:
                if (gamma == 1): # Put in check for gamma=1, the common use case, just to save time
                    data = 255.*(data - new_min)/(new_max-new_min)
                else:
                    data = 255.*pow((data - new_min)/(new_max-new_min),gamma)
            else:
                data = 255.*np.ones(data.shape)

            if sval != 2: #Not Signed Data (Pass or Mag)
                lut = self.histogram.getLookupTable(n=256)
                lut = np.insert(lut, 3, 255, axis=1)
                image_data = lut[np.uint8(data)]
                    
   
            else: #Signed data, positive numbers green, negative numbers magenta
                red = np.zeros(data.shape)
                green = np.zeros(data.shape)
                blue = np.zeros(data.shape)
                red[sign<=0] = data[sign<=0]
                blue[sign<=0] = data[sign<=0]
                green[sign>=0] = data[sign>=0]

                red = red.astype(np.uint8)
                green = green.astype(np.uint8)
                blue = blue.astype(np.uint8)
                alpha = np.uint8(data)
        # DISPLAY RGB image
        else:

            if data.shape[-1] > 3:
                red   = data[:,:,0].astype(np.uint8)
                green = data[:,:,1].astype(np.uint8)
                blue  = data[:,:,2].astype(np.uint8)
                if(data.ndim == 3 and data.shape[-1] == 4) :
                    alpha = data[:,:,3].astype(np.uint8)
                else:
                    alpha = 255.*np.ones(blue.shape)
            else:
                self.p.log.warn("input veclen of "+str(data.shape[-1])+" is incompatible")
                return 1

        if image_data is not None: 
            if self.mask_image_data is not None:
                mask = np.zeros(image_data.shape)
                mask[self.mask_image_data[1], self.mask_image_data[0]] = image_data[self.mask_image_data[1], self.mask_image_data[0]]
                image_data = mask
            self.set_image(image_data)
        else:
            # send the RGB values to the output port
            h, w = red.shape[:2]
            imageTru = np.zeros((h, w, 4), dtype=np.uint8)
            imageTru[:, :, 0] = red
            imageTru[:, :, 1] = green
            imageTru[:, :, 2] = blue
            imageTru[:, :, 3] = alpha

            self.set_image(imageTru)
        
        if not self.initiated:
            self.initiated = True
            if not self.fix_range_menu.isChecked(): self.set_fix_range(False)

    def set_refresh(self, data=None):
        self.data = None
        self.slice_data = None
        self.image_data = None
        self.sval = 0  # scalar display
        self.zval = 0  # zero ref
        self.gamma = 1  # zero ref
        self.range_min = 0
        self.range_max = 0
        self.fix_range = False
        self.update = False
        self.slice = 1
        self.slice_max = 1
        self.sliceable = 1
        self.slice_dim = 0
        self.interpolate = False
        self.tool = "Mouse"
        self.resize = False
        self.window_leveling = False
        self.wl_viewbox_x = 0
        self.wl_viewbox_y = 0
        self.ROIS = None
        self.free_hand_roi = None
        self.mask_image_data = None
        self.initiated = False
        self.set_fix_range(False)
        self.set_sign(False)
        self.sign.setChecked(False)

    # setup menus ========================================

    def _setup_viewbox_menu(self):
        """Removes pyqtgraph default menu options from viewbox and adds image & roi specific options"""

        # get view box menu
        menu = self.viewbox.getMenu(None)

        # remove default actions
        actions = menu.actions()
        for action in actions:
            menu.removeAction(action)

        # copy image
        copy = QtWidgets.QAction("Copy", menu)
        copy.triggered.connect(self.copy_image)

        # paste roi
        paste = QtWidgets.QAction("Paste", menu)
        paste.triggered.connect(self.paste_roi)

        # interpolat image
        interpolate = QtWidgets.QAction("Interpolate", menu)
        interpolate.triggered.connect(lambda event: self.interpolate_image(event))
        interpolate.setCheckable(True)

        # sign
        self.sign = QtWidgets.QAction("Sign", menu)
        self.sign.triggered.connect(lambda on: self.set_sign(on))
        self.sign.setCheckable(True)

        # Flip image
        flip_x = QtWidgets.QAction("Flip X", menu)
        flip_x.triggered.connect(lambda on: self.viewbox.invertX(on))
        flip_x.setCheckable(True)

        flip_y = QtWidgets.QAction("Flip Y", menu)
        flip_y.triggered.connect(lambda on: self.viewbox.invertY(not on))
        flip_y.setCheckable(True)

        # recenter view
        recenter = QtWidgets.QAction("Recenter", menu)
        recenter.triggered.connect(lambda: self.viewbox.autoRange())

        # refresh image
        reset = QtWidgets.QAction("Reset", menu)
        reset.triggered.connect(self.reset_image)

        # mask roi menu
        roi_menu = QtWidgets.QMenu(menu)
        roi_menu.setTitle("Mask")
        image = QtWidgets.QAction("Image", roi_menu)
        image.triggered.connect(lambda: self.mask_all_rois())
        binary = QtWidgets.QAction("Binary", roi_menu)
        binary.triggered.connect(lambda: self.mask_all_rois(return_type='binary'))
        one_dim = QtWidgets.QAction("1D Array", roi_menu)
        one_dim.triggered.connect(lambda: self.mask_all_rois(return_type='1D'))
        roi_menu.addAction(image)
        roi_menu.addAction(binary)
        roi_menu.addAction(one_dim)

        # add options
        menu.addAction(copy)
        menu.addAction(paste)
        menu.addAction(interpolate)
        menu.addAction(self.sign)
        menu.addAction(roi_menu.menuAction())
        menu.addAction(flip_x)
        menu.addAction(flip_y)
        menu.addAction(recenter)
        menu.addAction(reset)

    def _setup_histogram_menu(self):
        """Removes pyqtgraph default menu options from histogram and adds image & roi specific options"""

        # get view box menu
        menu = self.histogram.vb.getMenu(None)

        # remove default actions
        actions = menu.actions()
        for action in actions:
            menu.removeAction(action)

        # fix range
        fix_range = QtWidgets.QAction("Fix Range", menu)
        fix_range.triggered.connect(self.set_fix_range)
        fix_range.setCheckable(True)
        self.fix_range_menu = fix_range

        # set window range
        range_menu = QtWidgets.QMenu(menu)
        range_menu.setTitle("Set Range")
        self.range_widget = Levels()
        self.range_widget.valueChanged.connect(self.range_changed)
        set_range = QtWidgets.QWidgetAction(range_menu)
        set_range.setDefaultWidget(self.range_widget)
        range_menu.addAction(set_range)

        # set window gamma
        gamma_menu = QtWidgets.QMenu(menu)
        gamma_menu.setTitle("Set gamma")
        self.gamma_widget = DoubleSpinHorizontalBox("Gamma")
        self.gamma_widget.set_min(0.1)
        self.gamma_widget.set_max(10)
        self.gamma_widget.set_val(1)
        self.gamma_widget.set_singlestep(0.05)
        self.gamma_widget.set_decimals(3)
        self.gamma_widget.valueChanged.connect(self.set_gamma)
        set_gamma = QtWidgets.QWidgetAction(gamma_menu)
        set_gamma.setDefaultWidget(self.gamma_widget)
        gamma_menu.addAction(set_gamma)

        # set zero ref
        zref_menu = QtWidgets.QMenu(menu)
        zref_group = QtWidgets.QActionGroup(zref_menu)
        zref_menu.setTitle("Zero Ref")
        pass_zero = QtWidgets.QAction("---", zref_menu, checkable=True)
        pass_zero.triggered.connect(lambda _: self.set_zval(0))
        above_zero = QtWidgets.QAction("0->", zref_menu, checkable=True)
        above_zero.triggered.connect(lambda _: self.set_zval(1))
        between_zero = QtWidgets.QAction("-0-", zref_menu, checkable=True)
        between_zero.triggered.connect(lambda _: self.set_zval(2))
        below_zero = QtWidgets.QAction("<-0", zref_menu, checkable=True)
        below_zero.triggered.connect(lambda _: self.set_zval(3))
        zref_menu.addAction(pass_zero)
        zref_menu.addAction(above_zero)
        zref_menu.addAction(between_zero)
        zref_menu.addAction(below_zero)
        zref_group.addAction(pass_zero)
        zref_group.addAction(above_zero)
        zref_group.addAction(between_zero)
        zref_group.addAction(below_zero)
        zref_group.setExclusive(True)
        pass_zero.setChecked(True)

        # reset histogram
        reset = QtWidgets.QAction("Reset", menu)
        reset.triggered.connect(self.reset_histogram)

        # add options
        menu.addAction(fix_range)
        menu.addAction(range_menu.menuAction())
        menu.addAction(gamma_menu.menuAction())
        menu.addAction(zref_menu.menuAction())
        menu.addAction(reset)

    def _setup_histogram_levels(self, data):
        self.histogram.autoHistogramRange()
        if np.iscomplexobj(data):
            mag = np.abs(data)
            self.set_range_min(truncate(mag.min(), 3))
            self.set_range_max(truncate(mag.max(), 3))
        else:
            self.set_range_min(truncate(data.min(), 3))
            self.set_range_max(truncate(data.max(), 3))

        self.histogram.vb.disableAutoRange(self.histogram.vb.XYAxes)

    # ROI ========================================

    def ROI_buttons(self):
        """Generate the ROI buttons. Buttons are placed side-by-side"""
        buttons = ['Mouse', 'Point', 'Line', 'Rectangle', 'Ellipse', 'Closed Polygon', 'Free Hand']
        horizontal_layout = QtWidgets.QHBoxLayout()
        
        for text in buttons:
            button = QtWidgets.QPushButton(text, self)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setIcon(QtGui.QIcon(GPI_PKG_PATH + f'/graphics/icons/{text}.png'))
            if text == "Mouse":
                button.setChecked(True)
            else:
                button.setChecked(False)
            button.clicked.connect(self.activate_tool)
            horizontal_layout.addWidget(button)

        return horizontal_layout

    def create_point(self):
        """Create point ROI on image display"""
        point = pg.ROI([self.x, self.y], pen=(4,9), removable=True)
        text = pg.TextItem(str(self.data_value(self.x, self.y)))
        text.setPos(self.x - 8, self.y - 8)
        text.setColor((4, 9))
        point.sigRemoveRequested.connect(lambda event : self.remove_roi(event, text))
        point.sigRegionChanged.connect(lambda event : self.point_drag(event, text))
        self.ROIS[self.slice_dim][self.slice - 1].append((point, text))
        self.viewbox.addItem(point)
        self.viewbox.addItem(text)
    
    def create_line(self):
        """Create line ROI on image display"""
        line = pg.LineSegmentROI([[self.x, self.y], [self.x + 20, self.y]], pen=(1,9), removable=True)
        self.viewbox.addItem(line)
        positions = line.getSceneHandlePositions()
        x1y1 = self.image.mapFromScene(positions[0][1])
        x2y2 = self.image.mapFromScene(positions[1][1])
        x1 = int(round(x1y1.x()))
        y1 = int(round(x1y1.y()))
        x2 = int(round(x2y2.x()))
        y2 = int(round(x2y2.y()))
        a = np.array((x1, y1))
        b = np.array((x2, y2))
        distance = truncate(np.linalg.norm(a-b), 3)
        text = pg.TextItem(str(distance))
        text.setPos(x1 - 4 + (x2-x1)/2, y1 - 6)
        text.setColor((1, 9))
        self.viewbox.addItem(text)
        line.sigRemoveRequested.connect(lambda event : self.remove_roi(event, text))
        line.sigRegionChanged.connect(lambda event : self.line_drag(event, text))
        self.ROIS[self.slice_dim][self.slice - 1].append((line, text))
    
    def create_rect(self):
        """Create rectangle ROI on image display"""
        rect = pg.RectROI([self.x, self.y], [20, 20], centered=True, pen=(0,9), removable=True)
        self.viewbox.addItem(rect)
        stats = self.data_stats(self.mask_roi(rect, self.slice_data, return_type='1D'))
        text = pg.TextItem(stats)
        text.setPos(self.x - 25, self.y - 25)
        text.setColor((0, 9))
        self.viewbox.addItem(text)
        rect.addRotateHandle([1,0], [0.5, 0.5])
        rect.sigRemoveRequested.connect(lambda event : self.remove_roi(event, text))
        rect.sigRegionChanged.connect(lambda event : self.roi_drag(event, text))
        self.ROIS[self.slice_dim][self.slice - 1].append((rect, text))
        self.add_roi_menu(rect, text)

    def create_ellipse(self):
        """Create ellipse ROI on image display"""
        ellipse = pg.EllipseROI([self.x, self.y], [30, 20], pen=(3,9), removable=True)
        self.viewbox.addItem(ellipse)
        stats = self.data_stats(self.mask_roi(ellipse, self.slice_data, return_type='1D', output=False))
        text = pg.TextItem(stats)
        text.setPos(self.x - 25, self.y - 25)
        text.setColor((3, 9))
        self.viewbox.addItem(text)
        ellipse.sigRemoveRequested.connect(lambda event : self.remove_roi(event, text))
        ellipse.sigRegionChanged.connect(lambda event : self.roi_drag(event, text))
        self.ROIS[self.slice_dim][self.slice - 1].append((ellipse, text))
        self.add_roi_menu(ellipse, text)

    def create_polygon(self, closed=True):
        """Create polygon ROI on image display"""
        color = 7
        if closed: color = 4
        polygon = pg.PolyLineROI([[self.x, self.y], [self.x + 35, self.y + 10], [self.x + 10, self.y + 35]],pen=(color,9), closed=closed, removable=True)
        self.viewbox.addItem(polygon)
        stats = self.data_stats(self.mask_roi(polygon, self.slice_data, return_type='1D', output=False))
        text = pg.TextItem(stats)
        text.setPos(self.x - 25, self.y - 25)
        text.setColor((4, 9))
        self.viewbox.addItem(text)
        polygon.sigRemoveRequested.connect(lambda event : self.remove_roi(event, text))
        polygon.sigRegionChanged.connect(lambda event : self.roi_drag(event, text))
        self.ROIS[self.slice_dim][self.slice - 1].append((polygon, text))
        self.add_roi_menu(polygon, text, copy=True)

    def create_free_hand(self):
        """Create free hand ROI on image display"""
        color = 7
        polygon = pg.PolyLineROI([[self.x, self.y]], pen=(color,9), closed=False, removable=True)
        self.free_hand_roi = polygon
        self.free_hand_prev_point = (self.x, self.y)
        self.viewbox.addItem(polygon)

    def close_free_hand(self):
        """Close free hand ROI on image display"""
        h1 = self.free_hand_roi.segments[0].handles[1]['item']
        h2 = self.free_hand_roi.segments[-1].handles[0]['item']
        self.free_hand_roi.addSegment(h1, h2)
        stats = self.data_stats(self.mask_roi(self.free_hand_roi, self.slice_data, return_type='1D', output=False))
        text = pg.TextItem(stats)
        text.setPos(self.x - 25, self.y - 25)
        text.setColor((4, 9))
        self.viewbox.addItem(text)
        self.ROIS[self.slice_dim][self.slice - 1].append((self.free_hand_roi, text))
        self.free_hand_roi.sigRemoveRequested.connect(lambda event : self.remove_roi(event, text))
        self.free_hand_roi.sigRegionChanged.connect(lambda event : self.roi_drag(event, text))
        polygon = self.free_hand_roi
        self.add_roi_menu(polygon, text, copy=True)
        self.free_hand_roi = None

    def hide_rois (self, index):
        try:
            rois = self.ROIS[self.slice_dim][index]
            for roi, text in rois:
                roi.hide()
                text.hide()
        except:
            pass

    def show_rois (self, index):
        try:
            rois = self.ROIS[self.slice_dim][index]
            for roi, text in rois:
                roi.show()
                text.show()
                self.roi_drag(roi, text)
        except:
            pass

    def paste_roi(self):
        positions = eval(QtWidgets.QApplication.clipboard().text())
        positions = list(map(lambda pos: [self.image.mapFromScene(pos[0], pos[1]).x(), self.image.mapFromScene(pos[0], pos[1]).y()], positions))
        polygon = pg.PolyLineROI(positions, pen=(7,9), closed=True, removable=True)
        self.viewbox.addItem(polygon)
        stats = self.data_stats(self.mask_roi(polygon, self.slice_data, return_type='1D'))
        text = pg.TextItem(stats)
        text.setPos(self.x - 25, self.y - 25)
        text.setColor((4, 9))
        self.viewbox.addItem(text)
        polygon.sigRemoveRequested.connect(lambda event : self.remove_roi(event, text))
        polygon.sigRegionChanged.connect(lambda event : self.roi_drag(event, text))
        self.ROIS[self.slice_dim][self.slice - 1].append((polygon, text))
        self.add_roi_menu(polygon, text)

    def propogate_roi(self, roi, text):
        for i in range(len(self.ROIS[self.slice_dim])):
            if self.slice - 1 != i:
                self.ROIS[self.slice_dim][i].append((roi, text))

    def copy_roi(self, roi):
        positions = list(map(lambda point: [point[1].x(), point[1].y()], roi.getSceneHandlePositions()))
        QtWidgets.QApplication.clipboard().setText(str(positions))

    def add_roi_menu(self, roi, text, copy=False):
        """Add mask menu when you right click on ROI
        
        Parameters
        ----------
        roi : pyqtgraph.ROI
        """
        menu = roi.getMenu()

        # copy ROI
        if copy:
            copy = QtWidgets.QAction("Copy ROI", menu)
            copy.triggered.connect(lambda: self.copy_roi(roi))

        # propogate ROI
        propogate = QtWidgets.QAction("Propogate ROI", menu)
        propogate.triggered.connect(lambda: self.propogate_roi(roi, text))

        # Mask ROI
        roi_menu = QtWidgets.QMenu(self)
        roi_menu.setTitle("Mask ROI")
        image = QtWidgets.QAction("Image", roi_menu)
        image.triggered.connect(lambda: self.mask_roi(roi, self.image_data))
        binary = QtWidgets.QAction("Binary", roi_menu)
        binary.triggered.connect(lambda: self.mask_roi(roi, self.slice_data, return_type='binary'))
        one_dim = QtWidgets.QAction("1D Array", roi_menu)
        one_dim.triggered.connect(lambda: self.mask_roi(roi, self.slice_data, return_type='1D'))
        roi_menu.addAction(image)
        roi_menu.addAction(binary)
        roi_menu.addAction(one_dim)

        # add options
        if copy: menu.addAction(copy)
        menu.addAction(propogate)
        menu.addMenu(roi_menu)

    def mask_all_rois(self, return_type="image"):
        """Get the mask of all the rois on the current slice
        
        Parameters
        ----------
        return_type : str {'image', 'binary', '1D', 'coordinates'}, (Default: 'image)
            image: masks the image displayed in the image viewer
            data: masks the data used to generate the image
            1D: masks the data used to generate the image and converts to 1D numpy array
            coordinates: gives the mask coordinates

        Returns
        -------
        return_type
            image: None
            data: ndarray numpy array of masked data used to generate the image
            1D: 1D numpy array of masked data used to generate the image
            coordinates: returns the coordinates used for the mask
        """

        # get rois on slice
        rois = self.ROIS[self.slice_dim][self.slice - 1]
        if len(rois) == 0: return
        rois_coords = np.array(list(map(lambda roi: self.mask_roi(roi[0], self.slice_data, return_type='coordinates'), rois)), dtype='object')
        rois_coords = np.concatenate(rois_coords)

        # setting up the mask
        data = self.slice_data
        if return_type == 'image': data = self.image_data 

        mx = []
        my = []
        for coords in rois_coords:
            mx.append(coords[0])
            my.append(coords[1])

        if return_type == 'coordinates': return list(zip(mx, my))

        mask = np.zeros(data.shape)
        if return_type == 'image': 
            dimfunc = self.p.getVal('Extra Dimension')
            dimval = self.p.getVal('Slice/Tile Dimension')
            slice_v = self.p.getVal('Slice')
            mask[my, mx] = data[my, mx]
            self.mask_image_data = [mx, my, dimfunc, dimval, slice_v]
            self.set_image(mask)
 
        if return_type == 'binary':
            binary = np.ones(data.shape)
            mask[mx, my] = binary[mx, my]

            self.p.setData('binary', mask.T)
            self.valueChanged.emit(True)
            return mask

        if return_type == '1D':
            data_values = []
            for i in range(len(rois_coords)):
                data_values.append(data[rois_coords[i][0]][rois_coords[i][1]])
            data = np.array(data_values)
            self.p.setData('1D', data)
            self.valueChanged.emit(True)
            return data

    def mask_roi(self, roi, data, return_type='image', output=True):
        """Get the mask of the selected roi on the current slice
        
        Parameters
        ----------
        return_type : str {'image', 'binary', '1D', 'coordinates'}, (Default: 'image)
            image: masks the image displayed in the image viewer
            data: masks the data used to generate the image
            1D: masks the data used to generate the image and converts to 1D numpy array
            coordinates: gives the mask coordinates

        Returns
        -------
        return_type
            image: None
            data: ndarray numpy array of masked data used to generate the image
            1D: 1D numpy array of masked data used to generate the image
            coordinates: returns the coordinates used for the mask
        """
        roi.show()
        # setting up the x,y indicies
        cols = data.shape[0]
        rows = data.shape[1]
        grid = np.mgrid[:cols,:rows]
        x_indicies = grid[1,:,:]
        y_indicies = grid[0,:,:]
        x_indicies.shape = cols,rows
        y_indicies.shape = cols,rows

        #  getting the roi region coordinates
        x_coords = roi.getArrayRegion(x_indicies, self.image)
        y_coords = roi.getArrayRegion(y_indicies, self.image)

        mx = []
        my = []
        cols,rows = x_coords.shape
        for x in range(cols):
            for y in range(rows):
                if x_coords[x][y] or y_coords[x][y]:
                    mx.append(int(round(x_coords[x][y])))
                    my.append(int(round(y_coords[x][y])))

        if return_type == 'coordinates': return list(zip(mx, my))

        # setting up the mask
        mask = np.zeros(data.shape)

        if return_type == 'image': 
            dimfunc = self.p.getVal('Extra Dimension')
            dimval = self.p.getVal('Slice/Tile Dimension')
            slice_v = self.p.getVal('Slice')
            mask[my, mx] = data[my, mx]
            self.mask_image_data = [mx, my, dimfunc, dimval, slice_v]
            self.set_image(mask)


        if return_type == 'binary': 
            binary = np.ones(data.shape)
            mask[mx, my] = binary[mx, my]

            if output: 
                self.p.setData('binary', mask.T)
                self.valueChanged.emit(True)
            return mask

        if return_type == '1D':
            data_values = []
            for i in range(len(mx)):
                data_values.append(data[mx[i]][my[i]])
            data = np.array(data_values)
            if output: 
                self.p.setData('1D',data)
                self.valueChanged.emit(True)
            return data

    def remove_roi(self, roi, text=None):
        """Removes ROI from viewbox
        
        Parameters
        ----------
        roi : pyqtgraph.ROI
        
        text: pyqtgraph.TextItem, (text is None by default)
        """

        self.viewbox.removeItem(roi)
        if text: self.viewbox.removeItem(text)
   
    def activate_tool(self, event):
        """Activate to roi tool on ROI button click"""
        for i in range(self.buttons.count()):
            if self.buttons.itemAt(i).widget().isChecked():
                    self.tool = str(self.buttons.itemAt(i).widget().text())
    
    def toggle_tool(self, tool):
        """Toggle the ROI

        Parameters
        ----------
        tool : str {'Mouse', 'Point', 'Line', 'Rectangle', 'Ellipse', 'Closed Polygon', 'Free Hand'}
        """
        for i in range(self.buttons.count()):
            if tool == str(self.buttons.itemAt(i).widget().text()):
                self.buttons.itemAt(i).widget().toggle()
                self.tool = tool
    
    def point_drag(self, roi, text):
        """Update the ROI text when ROI is dragged
        
        Parameters
        ----------
        roi : pyqtgraph.ROI
        text : pyqtgraph.TextItem
        """
        scenePos = self.image.mapFromScene(roi.scenePos())
        x = scenePos.x()
        y = scenePos.y()
        text.setPos(x - 8, y - 8)
        text.setText(str(self.data_value(self.x, self.y)))

    def line_drag(self, roi, text):
        """Update the ROI text when ROI is dragged
        
        Parameters
        ----------
        roi : pyqtgraph.ROI
        text : pyqtgraph.TextItem
        """
        positions = roi.getSceneHandlePositions()
        x1y1 = self.image.mapFromScene(positions[0][1])
        x2y2 = self.image.mapFromScene(positions[1][1])
        x1 = int(round(x1y1.x()))
        y1 = int(round(x1y1.y()))
        x2 = int(round(x2y2.x()))
        y2 = int(round(x2y2.y()))
        a = np.array((x1, y1))
        b = np.array((x2, y2))
        distance = truncate(np.linalg.norm(a-b), 3)
        text.setText(str(distance))
        text.setPos(x1 - 4 + (x2-x1)/2, y1 - 6)

    def roi_drag(self, roi, text):
        """Update the ROI text when ROI is dragged
        
        Parameters
        ----------
        roi : pyqtgraph.ROI
        text : pyqtgraph.TextItem
        """
        scenePos = self.image.mapFromScene(roi.scenePos())
        x = scenePos.x()
        y = scenePos.y()
        # shift = text.boundingRect().getCoords()
        # shift_x = shift[2]
        # shift_y = shift[3]
        # shiftPos = self.image.mapFromScene(shift_x, shift_y)
        text.setPos(x - 25, y - 25)
        stats = self.data_stats(self.mask_roi(roi, self.slice_data, return_type='1D', output=False))
        text.setText(stats)
    

    # Mouse & Keyboard events ========================================

    def mouse_move(self, pos):
        """Get the mouse cursor x,y position on the image and data value at x,y. Help with drawing the free hand ROI"""
        scenePos = self.image.mapFromScene(pos)
        viewboxPos = self.viewbox.mapFromScene(pos)
        self.viewbox_x = viewboxPos.x() 
        self.viewbox_y = viewboxPos.y()
        self.x = scenePos.x()
        self.y = scenePos.y()

        if self.resize: self.mouse_resize()
        if self.window_leveling: self.mouse_window_level()

        if self.free_hand_roi:
            a = np.array(self.free_hand_prev_point)
            b = np.array((self.x, self.y))
            distance = np.linalg.norm(a-b)

            if distance > 3:
                if len(self.free_hand_roi.segments) == 0:
                    h2 = self.free_hand_roi.getHandles()[0]
                else:
                    h2 = self.free_hand_roi.segments[-1].handles[0]['item']
                h3 = self.free_hand_roi.addFreeHandle((self.x, self.y), index=self.free_hand_roi.indexOfHandle(h2))
                self.free_hand_roi.addSegment(h3, h2)
                self.free_hand_prev_point = (self.x, self.y)

        if self.interpolate:
            self.update_data_value(int(self.x/4), int(self.y/4))
        else:
            self.update_data_value(int(self.x), int(self.y))

    def mousePressEvent(self, event):
        """Listen to mouse press events"""
        self.pressed = True
        if self.free_hand_roi:
            self.close_free_hand()

        if event.button() == QtCore.Qt.LeftButton and self.tool != "Mouse":
            if self.tool == "Point":
                self.create_point()
            elif self.tool == "Line":
                self.create_line()
            elif self.tool == "Rectangle":
                self.create_rect()
            elif self.tool == "Ellipse":
                self.create_ellipse()
            elif self.tool == "Closed Polygon":
                self.create_polygon()
            elif self.tool == "Free Hand":
                self.create_free_hand()
            
            self.toggle_tool("Mouse")

        else:
            return super().mousePressEvent(event)

    def keyPressEvent(self, event):
        # copy image
        if event.matches(QtGui.QKeySequence.Copy):
            self.copy_image()
        
        # roi shortcuts
        elif event.key() == QtCore.Qt.Key_M:
            self.toggle_tool("Mouse")
        elif event.key() == QtCore.Qt.Key_P:
            self.toggle_tool("Point")
        elif event.key() == QtCore.Qt.Key_L:
            self.toggle_tool("Line")
        elif event.key() == QtCore.Qt.Key_R:
            self.toggle_tool("Rectangle")
        elif event.key() == QtCore.Qt.Key_E:
            self.toggle_tool("Ellipse")
        elif event.key() == QtCore.Qt.Key_C:
            self.toggle_tool("Closed Polygon")
        elif event.key() == QtCore.Qt.Key_F:
            self.toggle_tool("Free Hand")
        
        else:
            return super().keyPressEvent(event)
    
    def mouse_release(self, event, release_handler):
        self.pressed = False
        self.window_leveling = False
        self.resize = False
        self.pglayout.setMinimumWidth(0)
        self.pglayout.setMaximumWidth(10000)

        return release_handler(event)
    
    def mouse_press(self, event, press_handler):
        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
            # if not self.window_leveling:
            self.window_leveling = True
            self.wl_viewbox_x = self.viewbox_x
            self.wl_viewbox_y = self.viewbox_y
            
        elif QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
            self.resize = True
            self.wl_viewbox_x = self.viewbox_x
            self.wl_viewbox_y = self.viewbox_y
        else:
            return press_handler(event)
    
    def mouse_window_level_helper(self, x, y):
        floor = abs((x%self.viewbox.width()) - self.viewbox.width())/self.viewbox.width()
        ceil = abs((y%self.viewbox.height()) - self.viewbox.height())/self.viewbox.height()

        data = self.data
        cval = self.p.getVal('Complex Display')
        if np.iscomplexobj(self.data):
            if cval == 0: # Real
                data = np.real(self.data)
            elif cval == 1: # Imag
                data = np.imag(self.data)
            elif cval == 2: # Mag
                data = np.abs(self.data)
            elif cval == 3: # Phase
                data = np.angle(self.data, deg=True)

        if np.iscomplexobj(data):
            mag = np.abs(data)
            data_min = mag.min()
            data_max = mag.max()
        else:
            data_min = data.min()
            data_max = data.max()

        
        factor = data_max - data_min
        floor *= factor
        ceil *= factor

        floor += data_min
        ceil += data_min

        return floor*1.7, ceil*1.7

    def mouse_window_level(self):
        vb_floor, vb_ceil = self.mouse_window_level_helper(self.viewbox_x, self.viewbox_y)
        wl_floor, wl_ceil = self.mouse_window_level_helper(self.wl_viewbox_x, self.wl_viewbox_y)
        h_floor, h_ceil = self.histogram.getLevels()
        floor_diff = vb_floor - wl_floor
        ceil_diff = vb_ceil - wl_ceil
        floor = h_floor + floor_diff + ceil_diff
        ceil = h_ceil - floor_diff + ceil_diff

        self.wl_viewbox_x = self.viewbox_x
        self.wl_viewbox_y = self.viewbox_y

        self.histogram.setLevels(floor, ceil)

    def mouse_resize(self):
        floor = self.viewbox_x - self.wl_viewbox_x
        ceil = self.viewbox_y - self.wl_viewbox_y

        self.wl_viewbox_x = self.viewbox_x
        self.wl_viewbox_y = self.viewbox_y

        self.pglayout.setFixedWidth(self.pglayout.width() + floor)
        self.pglayout.setFixedHeight(self.pglayout.height() + ceil)

        self.p.parent().parent().resize(self.pglayout.width() + 40, self.p.parent().parent().height())

    def mouseDoubleClickEvent(self, event):
        pass

    def rightButtonMenu(self, event):
        pass
    
    # Other ========================================
    
    def scroll_to_slice (self, event, wheel_handler):
        """Navigates through the slices if the data is sliceable
        
        Parameters
        ----------
        event : QtWidgets.QGraphicsSceneWheelEvent
        
        wheel_handle:
            pyqtgraph mouse wheel handler which is needed to inject our code without effecting its behaviour
        """

        # check if shift key is pressed and the data is sliceable
        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier and self.sliceable:
            # update slice index & rois visibility based on wheel dirction
            slice_v = self.p.getVal('Slice')
            if event.delta() < 0:
                self.p.setAttr('Slice', val=slice_v - 1)
            else:
                self.p.setAttr('Slice', val=slice_v + 1)
            
        else:
            return wheel_handler(event)

    def resample(self, data, scale):
        """ Resize an image maintaining its proportions
        Args:
            data (np.ndarray): numpy array of the image data of shape (w, h, 3) or (w, h, 4)
            scale (float): scale to resample image to
        Returns:
            image (PIL.Image): Scaled image
        """
        img = Image.fromarray(data)
        width, height = img.size
        return img.resize((width*scale, height*scale), resample=Image.BICUBIC)

    def interpolate_image(self, on):
        if on:
            self.interpolate = True
            img = np.array(self.resample(self.image_data, 4))
            self.image.setImage(img)
        else:
            self.image.setImage(self.image_data)
            self.interpolate = False
        self.viewbox.autoRange()

    def copy_image(self):
        self.image_exporter.params['width'] = self.viewbox.screenGeometry().width()
        self.image_exporter.params['height'] = self.viewbox.screenGeometry().height()
        self.image_exporter.export(copy=True)

    def reset_image(self):
        self.mask_image_data = None
        self.viewbox.autoRange()
        self.set_update()

    def reset_histogram(self):
        if self.fix_range: self.histogram.setLevels(self.fix_range_min, self.fix_range_max)

    def set_background_color(self, color=(20, 30, 40)):
        """Sets the background color of pyqtgraph widgets
        
        Parameters
        ----------
        color : tuple (r, g, b), (the default is (20, 30, 40))
        """
        pg.setConfigOption('background', color)


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
    """2D image viewer for real or complex NPYarrays.

    INPUT:
    2D data, real or complex
    3D uint8 ARGB data (e.g. output of another ImageDisplay node)

    OUTPUT:
    3D data of displayed image, last dimension has length 4 for ARGB byte (uint8) data

    WIDGETS:
    Complex Display - If data are complex, allows you to show Real, Imaginary, Magnitude, Phase, or "Complex" data.
        If C (Complex) is chosen, then pixel brightness reflects value magnitude, while pixel color reflects value phase.
        If input data are real-valued, this widget is hidden

    Color Map - Chooses from a number of colormaps for real-valued data.  Not available if Scalar Display is "Sign"

    Edge Pixels - only visible for complex input data with Complex Display set to "C"
        Setting this to N creates an N-pixel color ring around the image border illustrating the phase-to-color mapping

    Black Pixels - only visible for complex input data with Complex Display set to "C"
        Setting this to N creates an N-pixel black ring around the image border (but inside the Edge Pixels ring) to
        separate the Edge pixel ring from the actual data image

    Viewport - displays the image
      Double clicking on Viewport area brings up a scaling widget to change the image size, and change graphic overlay

    L W F C - (hidden by default - double click on widget area to show sliders)
              Adjust value-to-pixel brightness mapping using Level/Window or Floor/Ceiling

    Scalar Display - visible for real data, or complex data with "Complex Display" set to R, I, M, or P
      Pass uses the real data in the data-to-pixel mapping
      Mag uses the magnitude data in the data-to-pixel mapping (i.e. affects negative values only)
      Sign will display positive values in green, and the absolutele value of negative values in magenta

    Gamma - changes gamma of display function.  Default value of 1 gives linear mapping of data to pixel value
      pixel values refect value of data^gamma

    Zero Ref - visible for real data, or complex data with "Complex Display" set to R, I, M, or P
               also invisible if "Scalar Display" set to Sign
      This is used for the data-to-pixel value mapping
      --- maps the smallest value to black, and the largest value to white
      0-> maps zero to black, and the largest value to white.  All negative numbers are black
      -0- maps zero to middle gray, with the largest magnitude set to black (if negative) or white (if positive)
      <-0 maps zero to white, and the most negative value to black.  All positive numbers are white

    Fix Range
      If Auto-Range On, the data range for pixel value mapping is rescaled whenever new data appears at input
      If Fixed-Range On, the data range is fixed (and can be changed using Range Min and Range Max)

    Range Min - shows minimum data value used for mapping to pixel values
      This value can be changed if (and only if) "Fix Range" is set to "Fixed-Ranged On"

    Range Max - shows maximum data value used for mapping to pixel values
      This value can be changed if (and only if) "Fix Range" is set to "Fixed-Ranged On"
    """

    def execType(self):
        return gpi.GPI_APPLOOP

    def initUI(self):

        # Widgets
        self.addWidget('ExclusivePushButtons','Complex Display',
                       buttons=['R','I','M','P','C'], val=4)
        self.real_cmaps = ['Gray','IceFire','Fire','Hot','HOT2','BGR']
        self.complex_cmaps = ['HSV','HSL','HUSL','CoolWarm']
        self.addWidget('ExclusivePushButtons','Color Map',
                       buttons=self.real_cmaps, val=0, collapsed=True)
        self.addWidget('SpinBox', 'Edge Pixels', min=0)
        self.addWidget('SpinBox', 'Black Pixels', min=0)
        self.addWidget('Image_Viewer', 'Viewport:', parent=self)
        self.addWidget('Slider', 'Slice', min=1, val=1)
        self.addWidget('ExclusivePushButtons', 'Slice/Tile Dimension', buttons=['0', '1', '2'], val=0)
        self.addWidget('ExclusivePushButtons', 'Extra Dimension', buttons=['Slice', 'Tile', 'RGB(A)'], val=0)
        self.addWidget('SpinBox', '# Columns', val=1)
        self.addWidget('SpinBox', '# Rows', val=1)
        self.addWidget('WindowLevel', 'L W F C:', collapsed=True)
        self.addWidget('ExclusivePushButtons','Scalar Display',
                       buttons=['Pass','Mag','Sign'], val=0, visible=False)
        self.addWidget('DoubleSpinBox', 'Gamma',min=0.1,max=10,val=1,singlestep=0.05,decimals=3, visible=False)
        self.addWidget('ExclusivePushButtons','Zero Ref',
                       buttons=['---','0->','-0-','<-0'], val=0, visible=False)
        self.addWidget('PushButton', 'Fix Range', button_title='Auto-Range On', toggle=True, visible=False)
        self.addWidget('DoubleSpinBox', 'Range Min', visible=False)
        self.addWidget('DoubleSpinBox', 'Range Max', visible=False)

        # IO Ports
        self.addInPort('in', 'NPYarray', drange=(2,3))
        self.addOutPort('out', 'NPYarray')
        self.addOutPort('binary', 'NPYarray')
        self.addOutPort('1D', 'NPYarray')
        self.input_data = None

    def validate(self):
        # Complex or Scalar?
        data = self.getData('in')
        dimfunc = self.getVal('Extra Dimension')

        if data.ndim == 3:
            dimval = self.getVal('Slice/Tile Dimension')
            self.setAttr('Extra Dimension', visible=True)
            if data.shape[-1] not in [3, 4]:
                if dimfunc > 1:
                    dimfunc = 0
                self.setAttr('Extra Dimension', buttons=['Slice', 'Tile'], val=dimfunc)
            else:
                if data.dtype == 'uint8':
                    dimfunc = 2
                self.setAttr('Extra Dimension', buttons=['Slice', 'Tile', 'RGB(A)'], val=dimfunc)

            if dimfunc == 0:
                slval = self.getVal('Slice')
                self.setAttr('Slice/Tile Dimension', visible=True)
                if slval > data.shape[dimval]:
                    slval = data.shape[dimval]
                self.setAttr('Slice', visible=True, min=1, max=data.shape[dimval], val=slval)
                self.setAttr('# Rows', visible=False)
                self.setAttr('# Columns', visible=False)
            elif dimfunc == 1:
                self.setAttr('Slice/Tile Dimension', visible=True)
                ncol = self.getVal('# Columns')
                nrow = self.getVal('# Rows')
                N = data.shape[dimval]

                # set the default to something sane, i.e. square-ish
                if (ncol == 1 and nrow == 1
                    or 'Slice/Tile Dimension' in self.widgetEvents()):
                    ncol = np.round(np.sqrt(N))

                # make sure there are at least enough tiles
                if nrow * ncol < N:
                    nrow = np.ceil(N / ncol)

                # don't add extra blank tiles if they're not needed
                # TODO: same thing, but for columns
                while nrow * ncol - N >= ncol:
                    nrow -= 1

                self.setAttr('# Columns', visible=True, val=ncol)
                self.setAttr('# Rows', visible=True, val=nrow)
                self.setAttr('Slice', visible=False)
            else:
                self.setAttr('Slice/Tile Dimension', visible=False)
                self.setAttr('Slice', visible=False)
                self.setAttr('# Rows', visible=False)
                self.setAttr('# Columns', visible=False)

        else:
            if dimfunc > 1:
                dimfunc = 0
                self.setAttr('Extra Dimension', buttons=['Slice', 'Tile'], val=dimfunc)
            self.setAttr('Extra Dimension', visible=False)
            self.setAttr('Slice/Tile Dimension', visible=False)
            self.setAttr('Slice', visible=False)
            self.setAttr('# Rows', visible=False)
            self.setAttr('# Columns', visible=False)

        self.setAttr('L W F C:',visible=(dimfunc != 2))
        self.setAttr('Gamma',visible=(dimfunc != 2))
        self.setAttr('Fix Range',visible=(dimfunc != 2))

        if dimfunc == 2: # RGBA
          self.setAttr('Complex Display',visible=False)
          self.setAttr('Color Map',visible=False)
          self.setAttr('Scalar Display',visible=False)
          self.setAttr('Edge Pixels',visible=False)
          self.setAttr('Black Pixels',visible=False)
          self.setAttr('Zero Ref',visible=False)
          self.setAttr('Range Min',visible=False)
          self.setAttr('Range Max',visible=False)

        else:

          if np.iscomplexobj(data):
            self.setAttr('Complex Display',visible=True)
            scalarvis = self.getVal('Complex Display') != 4
          else:
            self.setAttr('Complex Display',visible=False)
            scalarvis = True

          if scalarvis:
            self.setAttr('Color Map',buttons=self.real_cmaps,
                         collapsed=self.getAttr('Color Map', 'collapsed'))
          else:
            self.setAttr('Color Map',buttons=self.complex_cmaps,
                         collapsed=self.getAttr('Color Map', 'collapsed'))

          self.setAttr('Scalar Display',visible=scalarvis)
          self.setAttr('Edge Pixels',visible=not scalarvis)
          self.setAttr('Black Pixels',visible=not scalarvis)

          if self.getAttr('Viewport:', 'sign') == 2:
            self.setAttr('Zero Ref',visible=False)
          else:
            self.setAttr('Zero Ref',visible=scalarvis)

          self.setAttr('Range Min',visible=scalarvis)
          self.setAttr('Range Max',visible=scalarvis)

          zval = self.getAttr('Viewport:', 'zval')
          if zval == 1:
            self.setAttr('Viewport:',range_min=0)
          elif zval == 3:
            self.setAttr('Viewport:',range_max=0)

        self.setAttr('Zero Ref',visible=False)
        self.setAttr('Range Min',visible=False)
        self.setAttr('Range Max',visible=False)
        self.setAttr('Fix Range',visible=False)
        self.setAttr('Scalar Display',visible=False)
        self.setAttr('Color Map',visible=False)
        self.setAttr('Gamma',visible=False)

        return 0

    def compute(self):

        # make a copy for changes
        data = self.getData('in').copy()
        
        # if self.input_data is None: self.input_data = data
        # if self.input_data is not None and not np.array_equal(self.input_data, data): 
        #     self.input_data = data
        #     self.setAttr('Viewport:', refresh=data)

        self.setAttr('Viewport:', update=data)


        
        return 0
