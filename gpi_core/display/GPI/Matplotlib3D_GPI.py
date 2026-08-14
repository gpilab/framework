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


# Author: GPI
# Date: 2026 Jul 30
# 3D companion to Matplotlib_GPI.py — adds surface/wireframe/scatter/line3D
# plots with graphical rotation (native Axes3D mouse-drag) plus numeric
# elevation/azimuth control that stays in sync with the mouse.
import json
import logging
import os
import matplotlib

import gpi
from gpi import QtCore, QtGui, QtWidgets

log = logging.getLogger(__name__)

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
# importing Axes3D registers the '3d' projection with matplotlib
from mpl_toolkits.mplot3d import Axes3D

# Dark palette — matches GPI's dark Fusion theme (gpi/theme.py)
_MPL_FIG_FACE = '#353535'
_MPL_AX_FACE  = '#1e1e1e'
_MPL_SPINE    = '#555555'
_MPL_TICK     = '#aaaaaa'
_MPL_TEXT     = '#dcdcdc'
_MPL_GRID     = '#3a3a3a'

_MPL_DEFAULT_THEME = {
    'fig_face': _MPL_FIG_FACE,
    'ax_face':  _MPL_AX_FACE,
    'spine':    _MPL_SPINE,
    'tick':     _MPL_TICK,
    'text':     _MPL_TEXT,
    'grid':     _MPL_GRID,
}

# separate settings file so it doesn't collide with the 2D node's palette
_MPL_COLORS_FILE = os.path.join(os.path.dirname(os.path.realpath(gpi.__file__)), 'matplotlib3d_colors.json')

def _load_mpl_colors():
    try:
        with open(_MPL_COLORS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_mpl_colors(port_colors, theme_colors):
    try:
        os.makedirs(os.path.dirname(_MPL_COLORS_FILE), exist_ok=True)
        with open(_MPL_COLORS_FILE, 'w') as f:
            json.dump({'portColors': list(port_colors),
                       'themeColors': dict(theme_colors)}, f, indent=2)
    except Exception as e:
        log.warning(f'Matplotlib3D: could not save color settings: {e}')

def _style_color_btn(btn, hex_color):
    c = QtGui.QColor(hex_color)
    luma = (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000
    fg = '#000000' if luma > 128 else '#ffffff'
    btn.setStyleSheet(
        f'QPushButton {{ background-color: {hex_color}; color: {fg}; '
        f'border: 1px solid #666; border-radius: 3px; }}'
    )


class MainWin_close(QtWidgets.QMainWindow):
    window_closed = gpi.Signal()
    def __init__(self):
        super().__init__()
        self._isActive = True

    def closeEvent(self, event):
        super().closeEvent(event)
        self.window_closed.emit()
        self._isActive = False

    def isActive(self):
        return self._isActive


class NavbarTools3D(NavigationToolbar):
    # Pan/Zoom rubber-band tools fight with Axes3D's native mouse-drag
    # rotate/zoom, so only expose Home (reset view) and Save here.
    toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
      )

    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)


class SpacingDialog(QtWidgets.QDialog):
    """Subplot margin / spacing editor."""

    _PARAMS = [
        ('left',   'Left margin',    0.0, 1.0),
        ('right',  'Right margin',   0.0, 1.0),
        ('top',    'Top margin',     0.0, 1.0),
        ('bottom', 'Bottom margin',  0.0, 1.0),
    ]

    def __init__(self, fig, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Subplot Spacing')
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowStaysOnTopHint)
        self.fig = fig
        self._spins = {}
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setSpacing(6)
        form.setContentsMargins(8, 8, 8, 8)
        for key, label, lo, hi in self._PARAMS:
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep(0.01)
            spin.setDecimals(3)
            spin.setValue(getattr(self.fig.subplotpars, key))
            spin.valueChanged.connect(lambda val, k=key: self._update(k, val))
            self._spins[key] = spin
            form.addRow(label, spin)
        root.addLayout(form)
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        root.addWidget(sep)
        reset_btn = QtWidgets.QPushButton('Reset to Defaults')
        reset_btn.clicked.connect(self._reset)
        root.addWidget(reset_btn)

    def _update(self, key, val):
        try:
            self.fig.subplots_adjust(**{key: val})
            self.fig.canvas.draw_idle()
        except Exception:
            pass

    def _reset(self):
        defaults = {'left': 0.05, 'right': 0.95, 'top': 0.93, 'bottom': 0.07}
        for k, v in defaults.items():
            self._spins[k].setValue(v)

    def sync_from_figure(self):
        for key, spin in self._spins.items():
            spin.blockSignals(True)
            spin.setValue(getattr(self.fig.subplotpars, key))
            spin.blockSignals(False)


class ColorPaletteDialog(QtWidgets.QDialog):
    """Floating dialog for editing all Matplotlib3D node colors."""

    def __init__(self, plot_widget, parent=None):
        super().__init__(parent)
        self._plot = plot_widget
        self.setWindowTitle('Color Palette')
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self._swatches = {}
        self._build_ui()
        self.refresh_swatches()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 12)

        root.addWidget(self._make_theme_group(
            'Background',
            [('fig_face', 'Figure background'),
             ('ax_face',  'Axes / pane background')]))

        root.addWidget(self._make_theme_group(
            'Text & Borders',
            [('text',  'Title / axis labels'),
             ('tick',  'Tick marks'),
             ('spine', 'Axes edges')]))

        root.addWidget(self._make_theme_group(
            'Grid',
            [('grid', 'Grid lines')]))

        root.addWidget(self._make_series_group())

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        root.addWidget(sep)

        reset_btn = QtWidgets.QPushButton('Reset to Defaults')
        reset_btn.setFixedHeight(28)
        reset_btn.clicked.connect(self._reset_defaults)
        root.addWidget(reset_btn)

    def _make_theme_group(self, title, entries):
        group = QtWidgets.QGroupBox(title)
        form  = QtWidgets.QFormLayout(group)
        form.setSpacing(6)
        form.setContentsMargins(8, 8, 8, 8)
        for key, label in entries:
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(120, 24)
            btn.setToolTip(f'Click to change: {label}')
            btn.clicked.connect(lambda checked, k=key: self._pick_theme(k))
            self._swatches[key] = btn
            form.addRow(label, btn)
        return group

    def _make_series_group(self):
        group  = QtWidgets.QGroupBox('Data Series')
        grid   = QtWidgets.QGridLayout(group)
        grid.setSpacing(5)
        grid.setContentsMargins(8, 8, 8, 8)
        for i in range(8):
            btn = QtWidgets.QPushButton(f'in{i}')
            btn.setFixedSize(80, 26)
            btn.setToolTip(f'Click to change color for input port in{i}')
            btn.clicked.connect(lambda checked, idx=i: self._pick_port(idx))
            self._swatches[f'port_{i}'] = btn
            grid.addWidget(btn, i // 4, i % 4)
        return group

    def _pick_theme(self, key):
        current = QtGui.QColor(self._plot._theme_colors[key])
        color   = QtWidgets.QColorDialog.getColor(current, self, key.replace('_', ' ').title())
        if color.isValid():
            self._plot._theme_colors[key] = color.name()
            _style_color_btn(self._swatches[key], color.name())
            self._plot.on_draw()
            _save_mpl_colors(self._plot._port_colors, self._plot._theme_colors)

    def _pick_port(self, idx):
        current = QtGui.QColor(self._plot._port_colors[idx])
        color   = QtWidgets.QColorDialog.getColor(current, self, f'in{idx} color')
        if color.isValid():
            self._plot._port_colors[idx] = color.name()
            _style_color_btn(self._swatches[f'port_{idx}'], color.name())
            self._plot.on_draw()
            _save_mpl_colors(self._plot._port_colors, self._plot._theme_colors)

    def _reset_defaults(self):
        self._plot._init_parms_colors()
        self.refresh_swatches()
        self._plot.on_draw()
        _save_mpl_colors(self._plot._port_colors, self._plot._theme_colors)

    def refresh_swatches(self):
        for key, color in self._plot._theme_colors.items():
            if key in self._swatches:
                _style_color_btn(self._swatches[key], color)
        for i, color in enumerate(self._plot._port_colors):
            k = f'port_{i}'
            if k in self._swatches:
                _style_color_btn(self._swatches[k], color)


class MatplotDisplay3D(gpi.GenericWidgetGroup):
    """Embeds a matplotlib 3D (Axes3D) figure window.

    Rotation is graphical by default: left-click-drag on the plot rotates
    the view (built into Axes3D), scroll/right-drag zooms.  The Elevation
    and Azimuth spin boxes mirror the current view and can also be used to
    set it numerically; they stay in sync in both directions.
    """
    valueChanged = gpi.Signal()

    _PLOT_TYPES = ['Scatter', 'Line', 'Surface', 'Wireframe']

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self._collapsables = []
        self._subplotPosition = {'left': 0.05, 'right': 0.95, 'top': 0.93, 'bottom': 0.07}

        self._default_port_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
            '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
        ]
        self._port_colors  = list(self._default_port_colors)
        self._theme_colors = dict(_MPL_DEFAULT_THEME)
        self._palette_window = None
        self._adj_window = None

        # debounce draws
        self._updatetimer = QtCore.QTimer()
        self._updatetimer.setSingleShot(True)
        self._updatetimer.timeout.connect(self._on_draw)
        self._updatetimer.setInterval(10)

        # true while we are pushing mouse-driven view angles into the spin
        # boxes, so their valueChanged handlers don't re-trigger a draw
        self._syncing_view = False

        # shifts the port color cycle on each accumulated "hold" draw
        self._hold_color_offset = 0

        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # TITLE / LABELS
        plotlabels = QtWidgets.QHBoxLayout()
        self._plot_title = QtWidgets.QLineEdit()
        self._plot_xlab = QtWidgets.QLineEdit()
        self._plot_ylab = QtWidgets.QLineEdit()
        self._plot_zlab = QtWidgets.QLineEdit()
        self._plot_title.setPlaceholderText('title')
        self._plot_xlab.setPlaceholderText('x label')
        self._plot_ylab.setPlaceholderText('y label')
        self._plot_zlab.setPlaceholderText('z label')
        for w in (self._plot_title, self._plot_xlab, self._plot_ylab, self._plot_zlab):
            w.returnPressed.connect(self.on_draw)
            plotlabels.addWidget(w)
            self._collapsables.append(w)

        # PLOT TYPE / LINE WIDTH
        self._plottype_cb = gpi.widgets.ComboBox('plot type', self)
        self._plottype_cb.set_items(self._PLOT_TYPES)
        self._plottype_cb.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._plottype_cb)

        self._linewidth_spin = gpi.widgets.BasicDoubleSpinBox(self)
        self._linewidth_spin.set_label('line width')
        self._linewidth_spin.set_min(0.1)
        self._linewidth_spin.set_max(20.0)
        self._linewidth_spin.set_decimals(2)
        self._linewidth_spin.set_singlestep(0.1)
        self._linewidth_spin.set_val(1.2)
        self._linewidth_spin.set_immediate(True)
        self._linewidth_spin.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._linewidth_spin)

        plottype_lyt = QtWidgets.QHBoxLayout()
        plottype_lyt.addWidget(self._plottype_cb)
        plottype_lyt.addWidget(self._linewidth_spin)

        # GRID / LEGEND / HOLD / AUTOSCALE
        self._autoscale_btn = gpi.widgets.BasicPushButton(self)
        self._autoscale_btn.set_toggle(True)
        self._autoscale_btn.set_button_title('autoscale')
        self._autoscale_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._autoscale_btn)

        self._grid_btn = gpi.widgets.BasicPushButton(self)
        self._grid_btn.set_toggle(True)
        self._grid_btn.set_button_title('grid')
        self._grid_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._grid_btn)

        self._legend_btn = gpi.widgets.BasicPushButton(self)
        self._legend_btn.set_toggle(True)
        self._legend_btn.set_button_title('legend')
        self._legend_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._legend_btn)

        # HOLD — accumulate plots across draws instead of clearing (kept as
        # its own row, matching Matplotlib_GPI.py; not wired to on_draw so
        # toggling it doesn't itself trigger a redraw).
        self._hold_btn = gpi.widgets.BasicPushButton(self)
        self._hold_btn.set_toggle(True)
        self._hold_btn.set_button_title('hold')
        self._collapsables.append(self._hold_btn)

        self._ortho_btn = gpi.widgets.BasicPushButton(self)
        self._ortho_btn.set_toggle(True)
        self._ortho_btn.set_button_title('orthographic')
        self._ortho_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._ortho_btn)

        toggles_lyt = QtWidgets.QHBoxLayout()
        for b in (self._autoscale_btn, self._grid_btn, self._legend_btn, self._ortho_btn):
            toggles_lyt.addWidget(b)

        # X/Y/Z LIMITS
        lims = QtWidgets.QGridLayout()
        self._lim_min = {}
        self._lim_max = {}
        lims.addWidget(QtWidgets.QLabel(''), 0, 0)
        lims.addWidget(QtWidgets.QLabel('min'), 0, 1, alignment=QtCore.Qt.AlignHCenter)
        lims.addWidget(QtWidgets.QLabel('max'), 0, 2, alignment=QtCore.Qt.AlignHCenter)
        for row, axis in enumerate(('x', 'y', 'z'), start=1):
            lab = QtWidgets.QLabel(axis + ' limits')
            mn = gpi.widgets.BasicDoubleSpinBox(self)
            mx = gpi.widgets.BasicDoubleSpinBox(self)
            for spin in (mn, mx):
                spin.set_immediate(True)
                spin.set_decimals(5)
                spin.valueChanged.connect(self.on_draw)
                self._collapsables.append(spin)
            self._lim_min[axis] = mn
            self._lim_max[axis] = mx
            lims.addWidget(lab, row, 0)
            lims.addWidget(mn, row, 1)
            lims.addWidget(mx, row, 2)
            self._collapsables.append(lab)

        # VIEW (elevation / azimuth) — synced with mouse-drag rotation
        view_lyt = QtWidgets.QGridLayout()
        self._elev_spin = gpi.widgets.BasicDoubleSpinBox(self)
        self._elev_spin.set_label('elevation')
        self._elev_spin.set_min(-180)
        self._elev_spin.set_max(180)
        self._elev_spin.set_val(30)
        self._elev_spin.set_immediate(True)
        self._elev_spin.valueChanged.connect(self._on_view_spin_changed)
        self._azim_spin = gpi.widgets.BasicDoubleSpinBox(self)
        self._azim_spin.set_label('azimuth')
        self._azim_spin.set_min(-180)
        self._azim_spin.set_max(180)
        self._azim_spin.set_val(-60)
        self._azim_spin.set_immediate(True)
        self._azim_spin.valueChanged.connect(self._on_view_spin_changed)
        view_lyt.addWidget(self._elev_spin, 0, 0)
        view_lyt.addWidget(self._azim_spin, 0, 1)
        self._collapsables.append(self._elev_spin)
        self._collapsables.append(self._azim_spin)

        # COLOR PALETTE / SPACING / RESET
        self._palette_btn = gpi.widgets.BasicPushButton(self)
        self._palette_btn.set_button_title('color palette')
        self._palette_btn.valueChanged.connect(self.colorPaletteDialog)
        self._collapsables.append(self._palette_btn)

        self._subplotso_btn = gpi.widgets.BasicPushButton(self)
        self._subplotso_btn.set_button_title('spacing options')
        self._subplotso_btn.valueChanged.connect(self.subplotSpacingOptions)
        self._collapsables.append(self._subplotso_btn)

        opts_lyt = QtWidgets.QHBoxLayout()
        opts_lyt.addWidget(self._palette_btn)
        opts_lyt.addWidget(self._subplotso_btn)

        self._reset_btn = gpi.widgets.BasicPushButton(self)
        self._reset_btn.set_button_title('reset')
        self._reset_btn.valueChanged.connect(self._init_parms_)
        self._collapsables.append(self._reset_btn)

        # HLINES
        def _hline():
            h = QtWidgets.QFrame()
            h.setFrameStyle(QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken)
            self._collapsables.append(h)
            return h

        vbox.addLayout(plotlabels)
        vbox.addWidget(_hline())
        vbox.addLayout(plottype_lyt)
        vbox.addLayout(toggles_lyt)
        vbox.addWidget(_hline())
        vbox.addLayout(lims)
        vbox.addWidget(_hline())
        vbox.addLayout(view_lyt)
        vbox.addWidget(_hline())
        vbox.addLayout(opts_lyt)
        vbox.addWidget(self._hold_btn)
        vbox.insertStretch(-1, 1)
        vbox.addWidget(self._reset_btn)

        self._data   = None
        self._labels = []
        self._plotwindow = self.create_main_frame()

        hbox = QtWidgets.QHBoxLayout()
        hbox.addLayout(vbox)
        hbox.addLayout(self._plotwindow)
        hbox.setStretch(0, 0)
        hbox.setStretch(1, 11)
        self.setLayout(hbox)

        self.set_collapsed(False)
        self._init_parms_()

        saved = _load_mpl_colors()
        if isinstance(saved.get('portColors'), list):
            for i, c in enumerate(saved['portColors'][:8]):
                self._port_colors[i] = c
        if isinstance(saved.get('themeColors'), dict):
            for k, v in saved['themeColors'].items():
                if k in self._theme_colors:
                    self._theme_colors[k] = v

    # --- color palette ---
    def colorPaletteDialog(self):
        if self._palette_window is not None and self._palette_window.isVisible():
            self._palette_window.raise_()
            self._palette_window.activateWindow()
            return
        self._palette_window = ColorPaletteDialog(self, parent=None)
        self._palette_window.show()

    def _init_parms_colors(self):
        self._port_colors  = list(self._default_port_colors)
        self._theme_colors = dict(_MPL_DEFAULT_THEME)

    def subplotSpacingOptions(self):
        if self.fig is None:
            return
        if self._adj_window is not None and self._adj_window.isVisible():
            self._adj_window.sync_from_figure()
            self._adj_window.raise_()
            self._adj_window.activateWindow()
            return
        self._adj_window = SpacingDialog(self.fig, parent=None)
        self._adj_window.show()

    # setters
    def set_val(self, data):
        '''Takes a list of npy arrays, or list of (label, array) tuples.
        '''
        if isinstance(data, list):
            self._data   = []
            self._labels = []
            for item in data:
                if isinstance(item, tuple) and len(item) == 2:
                    self._labels.append(item[0])
                    self._data.append(item[1])
                else:
                    self._labels.append(None)
                    self._data.append(item)
            self.on_draw()

    def set_grid(self, val):
        self._grid_btn.set_val(val)
        self.on_draw()

    def set_autoscale(self, val):
        self._autoscale_btn.set_val(val)
        self.on_draw()

    def set_collapsed(self, val):
        self._isCollapsed = val
        for wdg in self._collapsables:
            if hasattr(wdg, 'setVisible'):
                wdg.setVisible(not val)

    def set_xlim(self, val, quiet=False):
        self._lim_min['x'].set_val(val[0])
        self._lim_max['x'].set_val(val[1])
        if not quiet:
            self.on_draw()

    def set_ylim(self, val, quiet=False):
        self._lim_min['y'].set_val(val[0])
        self._lim_max['y'].set_val(val[1])
        if not quiet:
            self.on_draw()

    def set_zlim(self, val, quiet=False):
        self._lim_min['z'].set_val(val[0])
        self._lim_max['z'].set_val(val[1])
        if not quiet:
            self.on_draw()

    def set_plotOptions(self, val):
        self._subplotSettings = val

    def set_plotPosition(self, val):
        self._subplotPosition = val

    def set_plotlabels(self, s):
        self._plot_title.setText(s['title'])
        self._plot_xlab.setText(s['xlabel'])
        self._plot_ylab.setText(s['ylabel'])
        self._plot_zlab.setText(s['zlabel'])
        self.on_draw()

    def set_legend(self, val):
        self._legend_btn.set_val(val)
        self.on_draw()

    def set_plottype(self, val):
        self._plottype_cb.set_val(val)
        self.on_draw()

    def set_linewidth(self, val):
        self._linewidth_spin.set_val(val)
        self.on_draw()

    def set_view(self, val, quiet=False):
        elev, azim = val
        self._elev_spin.set_val(elev)
        self._azim_spin.set_val(azim)
        if not quiet:
            self.on_draw()

    # getters
    def get_val(self):
        return self._data

    def get_grid(self):
        return self._grid_btn.get_val()

    def get_autoscale(self):
        return self._autoscale_btn.get_val()

    def get_xlim(self):
        return (self._lim_min['x'].get_val(), self._lim_max['x'].get_val())

    def get_ylim(self):
        return (self._lim_min['y'].get_val(), self._lim_max['y'].get_val())

    def get_zlim(self):
        return (self._lim_min['z'].get_val(), self._lim_max['z'].get_val())

    def get_plotPosition(self):
        return self._subplotPosition

    def get_plotlabels(self):
        return {
            'title':  str(self._plot_title.text()),
            'xlabel': str(self._plot_xlab.text()),
            'ylabel': str(self._plot_ylab.text()),
            'zlabel': str(self._plot_zlab.text()),
        }

    def get_legend(self):
        return self._legend_btn.get_val()

    def get_plottype(self):
        return self._plottype_cb.get_val()

    def get_linewidth(self):
        return self._linewidth_spin.get_val()

    def get_view(self):
        return (self._elev_spin.get_val(), self._azim_spin.get_val())

    # main frame
    def create_main_frame(self):
        self.fig = Figure((6.0, 4.8), dpi=100, facecolor=_MPL_FIG_FACE, linewidth=0.0)
        self.axes = None
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.canvas.setFocus()
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self.mpl_toolbar = NavbarTools3D(self.canvas, self)

        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        # keep the elevation/azimuth spin boxes in sync with mouse-drag rotation
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.addWidget(self.mpl_toolbar)
        return vbox

    def _on_mouse_release(self, event):
        if self.axes is None or not hasattr(self.axes, 'elev'):
            return
        self._syncing_view = True
        try:
            self._elev_spin.set_val(round(self.axes.elev, 2))
            self._azim_spin.set_val(round(self.axes.azim, 2))
        finally:
            self._syncing_view = False

    def _on_view_spin_changed(self, _val=None):
        if self._syncing_view:
            return
        self.on_draw()

    def on_key_press(self, event):
        try:
            from matplotlib.backend_bases import key_press_handler
            key_press_handler(event, self.canvas, self.mpl_toolbar)
        except Exception:
            pass

    def _init_parms_(self):
        self._subplotPosition = {'left': 0.05, 'right': 0.95, 'top': 0.93, 'bottom': 0.07}
        self._init_parms_colors()
        self.set_autoscale(True)
        self.set_grid(True)
        self.set_xlim((0.0, 1.0), quiet=True)
        self.set_ylim((0.0, 1.0), quiet=True)
        self.set_zlim((0.0, 1.0), quiet=True)
        self.set_plotlabels({'title': '', 'xlabel': '', 'ylabel': '', 'zlabel': ''})
        self.set_legend(False)
        self._ortho_btn.set_val(False)
        self._hold_btn.set_val(False)
        self._hold_color_offset = 0
        self.set_plottype('Scatter')
        self.set_linewidth(1.2)
        self.set_view((30, -60), quiet=True)
        self.on_draw()

    def on_draw(self):
        if not self._updatetimer.isActive():
            self._updatetimer.start()

    def _style_3d_axes(self, tc):
        ax = self.axes
        ax.set_facecolor(tc['ax_face'])
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            try:
                axis.pane.set_facecolor(tc['ax_face'])
                axis.pane.set_edgecolor(tc['spine'])
            except Exception:
                pass
            try:
                axis.line.set_color(tc['spine'])
            except Exception:
                pass
            try:
                axis._axinfo['grid']['color'] = tc['grid']
            except Exception:
                pass
        for a in ('x', 'y', 'z'):
            try:
                ax.tick_params(axis=a, colors=tc['tick'])
            except Exception:
                pass

    def _on_draw(self):
        if self.axes is None:
            self.axes = self.fig.add_subplot(111, projection='3d')

        tc = self._theme_colors

        if not self._hold_btn.get_val():
            self.axes.cla()
            self._hold_color_offset = 0
        else:
            self._hold_color_offset += 1

        self.fig.set_facecolor(tc['fig_face'])
        self._style_3d_axes(tc)

        # AUTOSCALE / LIMITS
        self.axes.set_autoscale_on(self.get_autoscale())
        if not self.get_autoscale():
            self.axes.set_xlim3d(self.get_xlim())
            self.axes.set_ylim3d(self.get_ylim())
            self.axes.set_zlim3d(self.get_zlim())

        # LABELS
        labels = self.get_plotlabels()
        self.axes.set_title(labels['title'], fontweight='bold', fontsize=16, color=tc['text'])
        self.axes.set_xlabel(labels['xlabel'], fontsize=12, color=tc['text'])
        self.axes.set_ylabel(labels['ylabel'], fontsize=12, color=tc['text'])
        self.axes.set_zlabel(labels['zlabel'], fontsize=12, color=tc['text'])

        # PROJECTION TYPE
        try:
            self.axes.set_proj_type('ortho' if self._ortho_btn.get_val() else 'persp')
        except Exception:
            pass

        # VIEW ANGLE (mouse-drag rotation updates elev/azim directly and
        # bypasses this method, so re-applying the stored values here is safe)
        elev, azim = self.get_view()
        self.axes.view_init(elev=elev, azim=azim)

        # GRID
        self.axes.grid(self.get_grid())

        if self._data is None:
            self.canvas.draw()
            return

        plot_type = self.get_plottype()
        lw = self.get_linewidth()
        any_labeled = False
        for idx, data in enumerate(self._data):
            data = np.asarray(data)
            label = (self._labels[idx] if idx < len(self._labels) else None) or f'in{idx}'
            # shift the color cycle on each accumulated "hold" draw so the
            # newest data doesn't land on top of the same-port color again
            color = self._port_colors[(idx + self._hold_color_offset) % len(self._port_colors)]

            if data.ndim < 2 or data.shape[-1] != 3:
                log.warning(f'Matplotlib3D: unsupported data shape {data.shape} for {label}, '
                            f'last axis must have size 3 (x,y,z), skipping')
                continue

            if data.ndim == 2:
                x, y, z = data[:, 0], data[:, 1], data[:, 2]
                n = max(x.size, 1)
                al = max(1.0 - 1.0 / np.log2(max(n, 2)), 0.6)
                if plot_type == 'Line':
                    self.axes.plot(x, y, z, color=color, lw=lw, alpha=al, label=label)
                else:
                    self.axes.scatter(x, y, z, color=color, s=20, alpha=al, label=label)
                any_labeled = True

            else:
                X, Y, Z = data[..., 0], data[..., 1], data[..., 2]
                if plot_type == 'Wireframe':
                    self.axes.plot_wireframe(X, Y, Z, color=color, linewidth=lw, alpha=0.85, label=label)
                else:
                    self.axes.plot_surface(X, Y, Z, color=color, alpha=0.85, label=label)
                any_labeled = True

        if self.get_legend() and any_labeled:
            try:
                self.axes.legend(facecolor=tc['fig_face'], edgecolor=tc['spine'], labelcolor=tc['text'])
            except Exception:
                pass

        if self.get_autoscale():
            self.set_xlim(self.axes.get_xlim3d(), quiet=True)
            self.set_ylim(self.axes.get_ylim3d(), quiet=True)
            self.set_zlim(self.axes.get_zlim3d(), quiet=True)

        self._style_3d_axes(tc)  # re-apply after cla()/autoscale may reset pane styling
        try:
            self.fig.subplots_adjust(**self._subplotPosition)
        except Exception:
            pass
        self.canvas.draw()


class ExternalNode(gpi.NodeAPI):
    """A Qt embedded 3D plot window — the 3D companion to Matplotlib_GPI.

    Supports scatter/line plots of (N,3) point clouds and surface/wireframe
    plots of (M,N,3) explicit X,Y,Z grids.  The view can be rotated
    graphically with the mouse (left-drag) at any time; the Elevation/Azimuth
    spin boxes track the current view and can also be used to set it
    numerically.

    INPUTS
    The last axis of the input array must have size 3 (x,y,z):
      (N,3)   real-valued data is plotted as a 3D scatter or line
      (M,N,3) real-valued data is plotted as a surface/wireframe
    """

    def initUI(self):
        self.addWidget('MatplotDisplay3D', 'Plot')

        self.addInPort('in0', 'NPYorTorch', kind='numpy', drange=(2, 3), obligation=gpi.OPTIONAL)

    def compute(self):
        data = self.getData('in0')
        in_lst = [('in0', data)] if data is not None else []

        self.setAttr('Plot', val=in_lst)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_APPLOOP
