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

import numpy as np
from matplotlib import cm
import gpi
from gpi import QtGui, QtWidgets


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
    I/O Info: - shows input shape, dtype, and data range

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
      Sign will display positive values in green, and the absolute value of negative values in magenta

    Gamma - changes gamma of display function.  Default value of 1 gives linear mapping of data to pixel value
      pixel values reflect value of data^gamma

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
        return gpi.GPI_THREAD

    def initUI(self):

        # Widgets
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('ExclusivePushButtons', 'Complex Display',
                       buttons=['R', 'I', 'M', 'P', 'C'], val=4)
        self.real_cmaps = ['Gray', 'IceFire', 'Fire', 'Hot', 'HOT2', 'BGR']
        self.complex_cmaps = ['HSV', 'HSL', 'HUSL', 'CoolWarm']
        self.addWidget('ExclusivePushButtons', 'Color Map',
                       buttons=self.real_cmaps, val=0, collapsed=True)
        self.addWidget('SpinBox', 'Edge Pixels', min=0)
        self.addWidget('SpinBox', 'Black Pixels', min=0)
        self.addWidget('DisplayBox', 'Viewport:')
        self.addWidget('Slider', 'Slice', min=1, val=1)
        self.addWidget('ExclusivePushButtons', 'Slice/Tile Dimension', buttons=['0', '1', '2'], val=0)
        self.addWidget('ExclusivePushButtons', 'Extra Dimension', buttons=['Slice', 'Tile', 'RGB(A)'], val=0)
        self.addWidget('SpinBox', '# Columns', val=1)
        self.addWidget('SpinBox', '# Rows', val=1)
        self.addWidget('WindowLevel', 'L W F C:', collapsed=True)
        self.addWidget('ExclusivePushButtons', 'Scalar Display',
                       buttons=['Pass', 'Mag', 'Sign'], val=0)
        self.addWidget('DoubleSpinBox', 'Gamma', min=0.1, max=10, val=1, singlestep=0.05, decimals=3)
        self.addWidget('ExclusivePushButtons', 'Zero Ref',
                       buttons=['---', '0->', '-0-', '<-0'], val=0)
        self.addWidget('PushButton', 'Fix Range', button_title='Auto-Range On', toggle=True)
        self.addWidget('DoubleSpinBox', 'Range Min')
        self.addWidget('DoubleSpinBox', 'Range Max')

        # IO Ports
        self.addInPort('in', 'NPYarray', drange=(2, 3))
        self.addOutPort('out', 'NPYarray')
        self.addOutPort('temp', 'NPYarray')

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

        self.setAttr('L W F C:', visible=(dimfunc != 2))
        self.setAttr('Gamma', visible=(dimfunc != 2))
        self.setAttr('Fix Range', visible=(dimfunc != 2))

        if dimfunc == 2:  # RGBA passthrough
            self.setAttr('Complex Display', visible=False)
            self.setAttr('Color Map', visible=False)
            self.setAttr('Scalar Display', visible=False)
            self.setAttr('Edge Pixels', visible=False)
            self.setAttr('Black Pixels', visible=False)
            self.setAttr('Zero Ref', visible=False)
            self.setAttr('Range Min', visible=False)
            self.setAttr('Range Max', visible=False)

        else:
            if np.iscomplexobj(data):
                self.setAttr('Complex Display', visible=True)
                scalarvis = self.getVal('Complex Display') != 4
            else:
                self.setAttr('Complex Display', visible=False)
                scalarvis = True

            if scalarvis:
                self.setAttr('Color Map', buttons=self.real_cmaps,
                             collapsed=self.getAttr('Color Map', 'collapsed'))
            else:
                self.setAttr('Color Map', buttons=self.complex_cmaps,
                             collapsed=self.getAttr('Color Map', 'collapsed'))

            self.setAttr('Scalar Display', visible=scalarvis)
            self.setAttr('Edge Pixels', visible=not scalarvis)
            self.setAttr('Black Pixels', visible=not scalarvis)

            if self.getVal('Scalar Display') == 2:
                self.setAttr('Zero Ref', visible=False)
            else:
                self.setAttr('Zero Ref', visible=scalarvis)

            self.setAttr('Range Min', visible=scalarvis)
            self.setAttr('Range Max', visible=scalarvis)

            zval = self.getVal('Zero Ref')
            if zval == 1:
                self.setAttr('Range Min', val=0)
            elif zval == 3:
                self.setAttr('Range Max', val=0)

            if self.getVal('Fix Range'):
                self.setAttr('Fix Range', button_title="Fixed Range On")
            else:
                self.setAttr('Fix Range', button_title="Auto-Range On")

        return 0

    def compute(self):

        def _safe_range(arr):
            """NaN/Inf-safe min and max; returns (0, 1) if all non-finite."""
            mn = float(np.nanmin(arr))
            mx = float(np.nanmax(arr))
            if not np.isfinite(mn):
                mn = 0.0
            if not np.isfinite(mx):
                mx = 1.0
            if mn == mx:
                mx = mn + 1.0
            return mn, mx

        # Fetch input — no upfront copy; slice/tile happens first below
        in_data = self.getData('in')
        in_shape = in_data.shape
        in_dtype = in_data.dtype
        data = in_data

        # ---- EXTRA DIMENSION: slice or tile BEFORE processing ----
        dimfunc = self.getVal('Extra Dimension')
        dimval  = self.getVal('Slice/Tile Dimension')

        if data.ndim == 3 and dimfunc < 2:
            if dimfunc == 0:  # slice one frame
                slval = self.getVal('Slice') - 1
                if dimval == 0:
                    data = data[slval, ...]
                elif dimval == 1:
                    data = data[:, slval, :]
                else:
                    data = data[..., slval]
            else:  # tile all frames into a mosaic
                ncol = int(self.getVal('# Columns'))
                nrow = int(self.getVal('# Rows'))
                data = np.rollaxis(data, dimval)
                N, xres, yres = data.shape
                N_new = ncol * nrow
                data = np.pad(data, ((0, N_new - N), (0, 0), (0, 0)), mode='constant')
                data = np.reshape(data, (nrow, ncol, xres, yres))
                data = np.swapaxes(data, 1, 2)
                data = np.reshape(data, (nrow * xres, ncol * yres))

        # ---- READ DISPLAY PARAMETERS ----
        gamma = self.getVal('Gamma')
        lval  = self.getAttr('L W F C:', 'val')
        cval  = self.getVal('Complex Display')

        if 'Complex Display' in self.widgetEvents():
            if cval == 4:
                self.setAttr('Color Map', buttons=self.complex_cmaps,
                             collapsed=self.getAttr('Color Map', 'collapsed'), val=0)
            else:
                self.setAttr('Color Map', buttons=self.real_cmaps,
                             collapsed=self.getAttr('Color Map', 'collapsed'), val=0)

        cmap = self.getVal('Color Map')
        sval = self.getVal('Scalar Display')
        zval = self.getVal('Zero Ref')
        fval = self.getVal('Fix Range')
        rmin = self.getVal('Range Min')
        rmax = self.getVal('Range Max')

        flor = 0.01 * lval['floor']
        ceil = 0.01 * lval['ceiling']
        if ceil == flor:
            flor = 0.999 if ceil == 1. else flor
            ceil = ceil if ceil == 1. else ceil + 0.001

        # ---- COMPLEX (magnitude × phase colormap) ----
        if np.iscomplexobj(data) and cval == 4:
            mag   = np.abs(data)
            phase = np.angle(data, deg=True)

            data_min = 0.
            if fval:
                data_max = rmax
            else:
                data_max = float(np.nanmax(mag))
                if not np.isfinite(data_max):
                    data_max = 1.0
                self.setAttr('Range Max', val=data_max)

            data_range = data_max - data_min
            new_min = data_range * flor + data_min
            new_max = data_range * ceil  + data_min
            mag = np.clip(mag, new_min, new_max)

            if new_max > new_min:
                mag = (mag - new_min) / (new_max - new_min)
                if gamma != 1:
                    mag = np.power(mag, gamma)
            else:
                mag = np.ones(mag.shape)

            # Optional phase-color border ring
            edgpix = self.getVal('Edge Pixels')
            blkpix = self.getVal('Black Pixels')
            if edgpix + blkpix > 0:
                h, w = mag.shape
                h2 = h + 2 * (edgpix + blkpix)
                w2 = w + 2 * (edgpix + blkpix)
                mag2   = np.zeros((h2, w2))
                phase2 = np.zeros((h2, w2))
                frame  = np.zeros((h2, w2), dtype=bool)
                frame[0:edgpix, :]          = True
                frame[h2-edgpix:h2, :]      = True
                frame[:, 0:edgpix]          = True
                frame[:, w2-edgpix:w2]      = True

                pad = edgpix + blkpix
                mag2[pad:pad+h, pad:pad+w]   = mag
                mag2[frame]                  = 1
                phase2[pad:pad+h, pad:pad+w] = phase
                xloc = np.tile(np.linspace(-1., 1., w2), (h2, 1))
                yloc = np.tile(np.linspace(1., -1., h2), (w2, 1)).T
                phase2[frame] = np.degrees(np.arctan2(yloc[frame], xloc[frame]))
                mag, phase = mag2, phase2

            # Pick phase colormap
            if cmap == 0:
                phase_cmap = cm.hsv
            elif cmap == 1:
                try:
                    import seaborn as sns
                    import matplotlib.colors as col
                    phase_cmap = col.ListedColormap(sns.color_palette("hls", 256))
                except ImportError:
                    self.log.warn("Seaborn not available; falling back on HSV.")
                    phase_cmap = cm.hsv
            elif cmap == 2:
                try:
                    import seaborn as sns
                    import matplotlib.colors as col
                    phase_cmap = col.ListedColormap(sns.color_palette("husl", 256))
                except ImportError:
                    self.log.warn("Seaborn not available; falling back on HSV.")
                    phase_cmap = cm.hsv
            else:  # CoolWarm
                phase_cmap = cm.coolwarm

            phase_norm = (phase + 180) / 360
            if cmap != 3:
                phase_norm = (phase_norm - 1 / 3) % 1

            # magnitude modulates brightness; phase drives hue
            colorized = (255 * cm.gray(mag) * phase_cmap(phase_norm)).astype(np.uint8)
            red   = colorized[..., 0]
            green = colorized[..., 1]
            blue  = colorized[..., 2]
            alpha = colorized[..., 3]

        # ---- SCALAR DISPLAY ----
        elif dimfunc != 2:
            if np.iscomplexobj(data):
                if cval == 0:
                    data = np.real(data)
                elif cval == 1:
                    data = np.imag(data)
                elif cval == 2:
                    data = np.abs(data)
                elif cval == 3:
                    data = np.angle(data, deg=True)

            if sval == 1:
                data = np.abs(data)
            elif sval == 2:
                sign = np.sign(data)
                data = np.abs(data)

            if fval:
                data_min, data_max = rmin, rmax
            else:
                data_min, data_max = _safe_range(data)

            if sval != 2:
                if zval == 1:
                    data_min = 0.
                elif zval == 2:
                    data_max = max(abs(data_min), abs(data_max))
                    data_min = -data_max
                elif zval == 3:
                    data_max = 0.
                data_range = data_max - data_min
                self.setAttr('Range Min', val=data_min)
                self.setAttr('Range Max', val=data_max)
            else:
                data_min  = 0.
                data_max  = max(abs(data_min), abs(data_max))
                data_range = data_max
                self.setAttr('Range Min', val=-data_range)
                self.setAttr('Range Max', val=data_range)

            new_min = data_range * flor + data_min
            new_max = data_range * ceil  + data_min
            data = np.clip(data, new_min, new_max)

            if new_max > new_min:
                data = (data - new_min) / (new_max - new_min)
                if gamma != 1:
                    data = np.power(data, gamma)
                data = 255. * data
            else:
                data = 255. * np.ones(data.shape)

            if sval != 2:  # Pass or Mag — apply colormap
                if cmap == 0:  # Grayscale
                    luma  = np.uint8(data)
                    red   = luma
                    green = luma
                    blue  = luma
                    alpha = np.full(luma.shape, 255, dtype=np.uint8)
                else:
                    rd = np.zeros(data.shape)
                    gn = np.zeros(data.shape)
                    be = np.zeros(data.shape)

                    if cmap == 1:  # IceFire
                        hue = 4. * (data / 256.)
                        h0 = hue < 1.
                        h1 = (hue >= 1.) & (hue < 2.)
                        h2 = (hue >= 2.) & (hue < 3.)
                        h3 = (hue >= 3.) & (hue < 4.)
                        be[h0] = hue[h0]
                        gn[h1] = (hue - 1.)[h1]; rd[h1] = (hue - 1.)[h1]; be[h1] = 1.
                        gn[h2] = 1.;              rd[h2] = 1.;              be[h2] = (3. - hue)[h2]
                        rd[h3] = 1.;              gn[h3] = (4. - hue)[h3]

                    elif cmap == 2:  # Fire
                        hue = 4. * (data / 256.)
                        h0 = hue < 1.
                        h1 = (hue >= 1.) & (hue < 2.)
                        h2 = (hue >= 2.) & (hue < 3.)
                        h3 = (hue >= 3.) & (hue < 4.)
                        be[h0] = hue[h0]
                        be[h1] = (2. - hue)[h1]; rd[h1] = (hue - 1.)[h1]
                        rd[h2] = 1.;              gn[h2] = (hue - 2.)[h2]
                        rd[h3] = 1.;              gn[h3] = 1.;              be[h3] = (hue - 3.)[h3]

                    elif cmap == 3:  # Hot
                        hue = 3. * (data / 256.)
                        h0 = hue < 1.
                        h1 = (hue >= 1.) & (hue < 2.)
                        h2 = (hue >= 2.) & (hue < 3.)
                        rd[h0] = hue[h0]
                        rd[h1] = 1.; gn[h1] = (hue - 1.)[h1]
                        rd[h2] = 1.; gn[h2] = 1.; be[h2] = (hue - 2.)[h2]

                    elif cmap == 4:  # HOT2 (ASIST)
                        r0 = data < 20.
                        r1 = (data >= 20.)  & (data <= 100.)
                        r3 = (data >= 128.) & (data <= 191.)
                        r4 = data > 191.
                        rd[r0] = data[r0] * (4.   / 255.)
                        rd[r1] = (80. - (data[r1] - 20.)) / 255.
                        rd[r3] = (data[r3] - 128.) * (4. / 255.)
                        rd[r4] = 1.

                        g1 = (data >= 45.)  & (data <= 130.)
                        g2 = (data > 130.)  & (data < 192.)
                        g3 = data >= 192.
                        gn[g1] = (data[g1] - 45.) * (3. / 255.)
                        gn[g2] = 1.
                        gn[g3] = (252. - (data[g3] - 192.) * 4.) / 255.

                        b1 = (data >= 1.)  & (data < 86.)
                        b2 = (data >= 86.) & (data <= 137.)
                        be[b1] = (data[b1] - 1.) * (3. / 255.)
                        be[b2] = (255. - (data[b2] - 86.) * 5.) / 255.

                    elif cmap == 5:  # BGR
                        hue = 4. * (data / 256.)
                        h0 = hue < 1.
                        h1 = (hue >= 1.) & (hue < 2.)
                        h2 = (hue >= 2.) & (hue < 3.)
                        h3 = (hue >= 3.) & (hue < 4.)
                        be[h0] = hue[h0]
                        gn[h1] = (hue - 1.)[h1]; be[h1] = 1.
                        gn[h2] = 1.; rd[h2] = (hue - 2.)[h2]; be[h2] = (3. - hue)[h2]
                        rd[h3] = 1.; gn[h3] = (4. - hue)[h3]

                    red   = np.uint8(255. * rd)
                    green = np.uint8(255. * gn)
                    blue  = np.uint8(255. * be)
                    alpha = np.full(red.shape, 255, dtype=np.uint8)

            else:  # Sign: positive → green, negative → magenta (red + blue)
                rd = np.zeros(data.shape)
                gn = np.zeros(data.shape)
                be = np.zeros(data.shape)
                rd[sign <= 0] = data[sign <= 0]
                be[sign <= 0] = data[sign <= 0]
                gn[sign >= 0] = data[sign >= 0]
                red   = rd.astype(np.uint8)
                green = gn.astype(np.uint8)
                blue  = be.astype(np.uint8)
                alpha = np.full(red.shape, 255, dtype=np.uint8)

        # ---- RGB(A) PASSTHROUGH ----
        else:
            if data.shape[-1] >= 3:
                red   = data[:, :, 0].astype(np.uint8)
                green = data[:, :, 1].astype(np.uint8)
                blue  = data[:, :, 2].astype(np.uint8)
                alpha = (data[:, :, 3].astype(np.uint8)
                         if data.shape[-1] == 4
                         else np.full(red.shape, 255, dtype=np.uint8))
            else:
                self.log.warn(f"ImageDisplay: incompatible input veclen {data.shape[-1]}")
                return 1

        # ---- ASSEMBLE OUTPUT IMAGE ----
        # QImage.Format_RGB32 memory layout per pixel (little-endian): [B, G, R, 0xFF]
        # so channel 0 → Blue display, channel 1 → Green, channel 2 → Red
        h, w = red.shape[:2]
        image = np.zeros((h, w, 4), dtype=np.uint8)
        image[:, :, 0] = blue
        image[:, :, 1] = green
        image[:, :, 2] = red
        image[:, :, 3] = alpha

        qimage = QtGui.QImage(image.data, w, h, QtGui.QImage.Format_RGB32)
        if qimage.isNull():
            self.log.warn("ImageDisplay: failed to construct QImage")

        # ---- I/O INFO ----
        try:
            if np.iscomplexobj(in_data):
                mag_data = np.abs(in_data)
                lo, hi = _safe_range(mag_data)
                range_label = f'|mag| range: [{lo:.4g}, {hi:.4g}]'
            else:
                lo, hi = _safe_range(in_data.astype(float))
                range_label = f'range: [{lo:.4g}, {hi:.4g}]'
        except Exception:
            range_label = 'range: n/a'

        self.setAttr('I/O Info:', val=(
            f'shape: {in_shape}   dtype: {in_dtype}\n'
            f'display: {(h, w)}   {range_label}'
        ))

        self.setAttr('Viewport:', val=qimage)
        self.setData('out', image)

        return 0
