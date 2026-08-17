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
# plots with graphical rotation plus numeric elevation/azimuth control that
# stays in sync with the mouse.
#
# Rendered with pyqtgraph.opengl (GPU/OpenGL, via PyOpenGL) when a real,
# working OpenGL context is available: matplotlib's mplot3d/Axes3D has no
# GPU path at all (every mouse-drag rotation re-rasterizes the whole scene
# on the CPU with Agg), which is why the old matplotlib-based 3D view would
# freeze on larger surfaces/point clouds. Some machines (observed on a
# Windows Server deployment target and on a dev VM) hand out a QOpenGLContext
# that reports itself as valid but fails on every real GL call (no actual
# GPU/display driver behind it, e.g. no GPU passthrough in a VM/RDP
# session) — `_probe_opengl_functional()` detects that up front and this
# node transparently falls back to the original CPU/matplotlib Axes3D
# renderer instead of crashing.
import json
import logging
import os
import matplotlib

import gpi
from gpi import QtCore, QtGui, QtWidgets

log = logging.getLogger(__name__)

import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
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


def _hex_to_rgba(hex_color, alpha=1.0):
    c = QtGui.QColor(hex_color)
    return (c.redF(), c.greenF(), c.blueF(), alpha)


def _grid_to_mesh(X, Y, Z):
    """Build MeshData vertexes/faces (2 triangles per cell) for an (M,N)
    explicit X,Y,Z grid, used for the GPU Surface/Wireframe GLMeshItem draws.
    """
    M, N = X.shape
    verts = np.ascontiguousarray(np.stack([X, Y, Z], axis=-1).reshape(-1, 3), dtype=np.float32)
    idx = np.arange(M * N).reshape(M, N)
    i0 = idx[:-1, :-1].ravel()
    i1 = idx[:-1, 1:].ravel()
    i2 = idx[1:, 1:].ravel()
    i3 = idx[1:, :-1].ravel()
    faces = np.concatenate([
        np.stack([i0, i1, i2], axis=1),
        np.stack([i0, i2, i3], axis=1),
    ], axis=0).astype(np.uint32)
    return verts, faces

_GL_FUNCTIONAL = None  # cached result of _probe_opengl_functional()


def _probe_opengl_functional():
    """Detect whether this machine has a real, working OpenGL context.

    A QOpenGLContext can report isValid()==True and a plausible version
    string while every actual GL call still fails (GL_INVALID_OPERATION on
    even glGetString(GL_VENDOR)) — observed on a Windows Server deployment
    target and a dev VM with no real GPU/display driver behind Qt's context
    (e.g. no GPU passthrough in a VM/RDP session). Draw one throwaway frame
    and check whether a basic GL call actually succeeds before committing to
    the GPU (pyqtgraph.opengl) renderer.
    """
    global _GL_FUNCTIONAL
    if _GL_FUNCTIONAL is not None:
        return _GL_FUNCTIONAL

    class _GLProbeWidget(QtWidgets.QOpenGLWidget):
        def __init__(self):
            super().__init__()
            self.ok = False

        def paintGL(self):
            try:
                from OpenGL import GL
                GL.glClear(GL.GL_COLOR_BUFFER_BIT)
                GL.glGetString(GL.GL_VENDOR)
                self.ok = True
            except Exception:
                self.ok = False

    try:
        app = QtWidgets.QApplication.instance()
        probe = _GLProbeWidget()
        probe.resize(2, 2)
        probe.move(-10000, -10000)  # keep the throwaway probe off-screen
        probe.show()
        if app is not None:
            for _ in range(5):
                app.processEvents()
        _GL_FUNCTIONAL = bool(probe.ok)
        probe.close()
        probe.deleteLater()
    except Exception:
        log.warning('Matplotlib3D: OpenGL probe failed, assuming no GPU support', exc_info=True)
        _GL_FUNCTIONAL = False

    if not _GL_FUNCTIONAL:
        log.warning('Matplotlib3D: no functional OpenGL context detected; '
                     'falling back to the CPU (matplotlib) 3D renderer')
    return _GL_FUNCTIONAL

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


class Gl3DViewWidget(gl.GLViewWidget):
    """GLViewWidget that emits a signal once a mouse-drag rotation/zoom
    finishes, so the Elevation/Azimuth spin boxes can be kept in sync (this
    is the GPU-view equivalent of the old Axes3D 'button_release_event' hook).
    """
    viewChanged = gpi.Signal()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.viewChanged.emit()


class NavbarTools3DGL(QtWidgets.QToolBar):
    # Orbit/zoom/pan are native GLViewWidget mouse-drag behavior, so only
    # expose Home (reset view) and Save here, matching the old toolbar.
    def __init__(self, plot_widget, parent):
        super().__init__(parent)
        self._plot = plot_widget
        self.setIconSize(QtCore.QSize(16, 16))
        home_act = self.addAction('Home')
        home_act.setToolTip('Reset original view')
        home_act.triggered.connect(self._plot.reset_view)
        save_act = self.addAction('Save')
        save_act.setToolTip('Save the figure')
        save_act.triggered.connect(self._on_save)

    def _on_save(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Image', '', 'PNG Image (*.png);;All Files (*)')
        if path:
            self._plot.view.grabFramebuffer().save(path)


class SpacingDialogGL(QtWidgets.QDialog):
    """Viewport padding editor (pixels around the GPU 3D view)."""

    _PARAMS = [
        ('left',   'Left padding',    0, 100),
        ('right',  'Right padding',   0, 100),
        ('top',    'Top padding',     0, 100),
        ('bottom', 'Bottom padding',  0, 100),
    ]

    def __init__(self, plot_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Viewport Padding')
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowStaysOnTopHint)
        self._plot = plot_widget
        self._spins = {}
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setSpacing(6)
        form.setContentsMargins(8, 8, 8, 8)
        for key, label, lo, hi in self._PARAMS:
            spin = QtWidgets.QSpinBox()
            spin.setRange(lo, hi)
            spin.setValue(int(self._plot._subplotPosition.get(key, 0)))
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
        self._plot._subplotPosition[key] = val
        self._plot._apply_view_padding()

    def _reset(self):
        defaults = {'left': 0, 'right': 0, 'top': 0, 'bottom': 0}
        for k, v in defaults.items():
            self._spins[k].setValue(v)

    def sync_from_state(self):
        for key, spin in self._spins.items():
            spin.blockSignals(True)
            spin.setValue(int(self._plot._subplotPosition.get(key, 0)))
            spin.blockSignals(False)


class NavbarTools3DMPL(NavigationToolbar):
    # Pan/Zoom rubber-band tools fight with Axes3D's native mouse-drag
    # rotate/zoom, so only expose Home (reset view) and Save here.
    toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
      )

    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)


class SpacingDialogMPL(QtWidgets.QDialog):
    """Subplot margin / spacing editor (CPU/matplotlib fallback renderer)."""

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

    def sync_from_state(self):
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
    """Embeds a GPU-accelerated (pyqtgraph.opengl GLViewWidget) 3D plot window.

    Rotation is graphical by default: left-click-drag on the plot rotates
    the view, scroll/right-drag zooms.  The Elevation and Azimuth spin boxes
    mirror the current view and can also be used to set it numerically;
    they stay in sync in both directions.
    """
    valueChanged = gpi.Signal()

    _PLOT_TYPES = ['Scatter', 'Line', 'Surface', 'Wireframe']

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        # decided once per process: GPU (pyqtgraph.opengl) if a real OpenGL
        # context is available here, otherwise the CPU/matplotlib fallback
        self._gpu_mode = _probe_opengl_functional()

        self._collapsables = []
        self._subplotPosition = ({'left': 0, 'right': 0, 'top': 0, 'bottom': 0} if self._gpu_mode
                                  else {'left': 0.05, 'right': 0.95, 'top': 0.93, 'bottom': 0.07})

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
        if not self._gpu_mode and self.fig is None:
            return
        if self._adj_window is not None and self._adj_window.isVisible():
            self._adj_window.sync_from_state()
            self._adj_window.raise_()
            self._adj_window.activateWindow()
            return
        if self._gpu_mode:
            self._adj_window = SpacingDialogGL(self, parent=None)
        else:
            self._adj_window = SpacingDialogMPL(self.fig, parent=None)
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
        if self._gpu_mode:
            self._apply_view_padding()

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
        if self._gpu_mode:
            return self._create_main_frame_gl()
        return self._create_main_frame_mpl()

    def _create_main_frame_gl(self):
        self.view = Gl3DViewWidget()
        self.view.setParent(self)
        self.view.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.view.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        # keep the elevation/azimuth spin boxes in sync with mouse-drag rotation
        self.view.viewChanged.connect(self._on_mouse_release)

        self._grid_item = gl.GLGridItem()
        self.view.addItem(self._grid_item)
        self._axis_item = gl.GLAxisItem()
        self.view.addItem(self._axis_item)
        self._data_items = []  # GL items for currently plotted data

        self._title_label = QtWidgets.QLabel()
        self._title_label.setAlignment(QtCore.Qt.AlignHCenter)

        self._legend_box = QtWidgets.QWidget()
        self._legend_lyt = QtWidgets.QVBoxLayout(self._legend_box)
        self._legend_lyt.setContentsMargins(6, 6, 6, 6)
        self._legend_lyt.setSpacing(2)
        self._legend_box.hide()

        self.mpl_toolbar = NavbarTools3DGL(self, self)

        view_row = QtWidgets.QHBoxLayout()
        self._view_row = view_row
        view_row.addWidget(self.view, 1)
        view_row.addWidget(self._legend_box, 0)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self._title_label)
        vbox.addLayout(view_row)
        vbox.addWidget(self.mpl_toolbar)
        return vbox

    def _create_main_frame_mpl(self):
        self.fig = Figure((6.0, 4.8), dpi=100, facecolor=_MPL_FIG_FACE, linewidth=0.0)
        self.axes = None
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.canvas.setFocus()
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self.mpl_toolbar = NavbarTools3DMPL(self.canvas, self)

        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        # keep the elevation/azimuth spin boxes in sync with mouse-drag rotation
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.addWidget(self.mpl_toolbar)
        return vbox

    def _apply_view_padding(self):
        p = self._subplotPosition
        self._view_row.setContentsMargins(
            int(p.get('left', 0)), int(p.get('top', 0)),
            int(p.get('right', 0)), int(p.get('bottom', 0)))

    def reset_view(self):
        self.set_view((30, -60), quiet=True)
        self.on_draw()

    def _on_mouse_release(self, *_args):
        if self._gpu_mode:
            elev, azim = self.view.opts['elevation'], self.view.opts['azimuth']
        else:
            if self.axes is None or not hasattr(self.axes, 'elev'):
                return
            elev, azim = self.axes.elev, self.axes.azim
        self._syncing_view = True
        try:
            self._elev_spin.set_val(round(elev, 2))
            self._azim_spin.set_val(round(azim, 2))
        finally:
            self._syncing_view = False

    def _on_view_spin_changed(self, _val=None):
        if self._syncing_view:
            return
        self.on_draw()

    def on_key_press(self, event):
        # only used by the matplotlib (CPU) fallback renderer
        try:
            from matplotlib.backend_bases import key_press_handler
            key_press_handler(event, self.canvas, self.mpl_toolbar)
        except Exception:
            pass

    def _init_parms_(self):
        self._subplotPosition = ({'left': 0, 'right': 0, 'top': 0, 'bottom': 0} if self._gpu_mode
                                  else {'left': 0.05, 'right': 0.95, 'top': 0.93, 'bottom': 0.07})
        if self._gpu_mode:
            self._apply_view_padding()
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
        if self._gpu_mode:
            self._style_3d_axes_gl(tc)
        else:
            self._style_3d_axes_mpl(tc)

    def _style_3d_axes_gl(self, tc):
        self.view.setBackgroundColor(tc['ax_face'])
        self._grid_item.setColor(tc['grid'])
        self._title_label.setStyleSheet(
            f'background-color: {tc["fig_face"]}; color: {tc["text"]}; '
            f'font-weight: bold; font-size: 14px; padding: 4px;')
        self._legend_box.setStyleSheet(
            f'background-color: {tc["fig_face"]}; border: 1px solid {tc["spine"]}; border-radius: 4px;')

    def _style_3d_axes_mpl(self, tc):
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

    def _set_item_visible(self, item, visible):
        in_view = item in self.view.items
        if visible and not in_view:
            self.view.addItem(item)
        elif not visible and in_view:
            self.view.removeItem(item)

    def _clear_data_items(self):
        for item in self._data_items:
            self.view.removeItem(item)
        self._data_items = []

    def _update_legend(self, entries):
        while self._legend_lyt.count():
            w = self._legend_lyt.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        show = self.get_legend() and bool(entries)
        self._legend_box.setVisible(show)
        if not show:
            return
        tc = self._theme_colors
        for label, color_hex in entries:
            row = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            swatch = QtWidgets.QFrame()
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(f'background-color: {color_hex}; border: 1px solid #888;')
            text = QtWidgets.QLabel(label)
            text.setStyleSheet(f'color: {tc["text"]};')
            h.addWidget(swatch)
            h.addWidget(text)
            self._legend_lyt.addWidget(row)

    def _apply_scene_bounds(self):
        # size the grid/axis and the camera distance to the current
        # x/y/z limits so autoscale/manual limits behave like Axes3D's
        xlo, xhi = self.get_xlim()
        ylo, yhi = self.get_ylim()
        zlo, zhi = self.get_zlim()
        vals = (xlo, xhi, ylo, yhi, zlo, zhi)
        if not all(np.isfinite(v) for v in vals):
            # never feed NaN/Inf into the GL scene: a bad upstream value
            # (e.g. an empty/failed read) can crash pyqtgraph mid-paint and
            # permanently corrupt the shared GL context (glBegin/glEnd left
            # open), breaking every frame drawn afterward, not just this one
            log.warning('Matplotlib3D: non-finite plot bounds, falling back to defaults')
            xlo, xhi, ylo, yhi, zlo, zhi = 0.0, 1.0, 0.0, 1.0, 0.0, 1.0
        cx, cy, cz = (xlo + xhi) / 2.0, (ylo + yhi) / 2.0, (zlo + zhi) / 2.0
        extent = max(xhi - xlo, yhi - ylo, zhi - zlo, 1e-6)
        if not np.isfinite(extent) or extent <= 0:
            extent = 1.0

        self._grid_item.resetTransform()
        self._grid_item.setSize(extent * 1.2, extent * 1.2)
        self._grid_item.setSpacing(extent / 10.0, extent / 10.0)
        self._grid_item.translate(cx, cy, zlo)

        self._axis_item.resetTransform()
        self._axis_item.setSize(extent * 0.6, extent * 0.6, extent * 0.6)
        self._axis_item.translate(xlo, ylo, zlo)

        self.view.opts['center'] = pg.Vector(cx, cy, cz)
        # tan-based distance keeps the scene framed the same way whether
        # fov is a normal perspective angle or the near-zero pseudo-ortho
        # angle used for the 'orthographic' toggle below
        fov = self.view.opts['fov']
        self.view.opts['distance'] = max((extent * 0.75) / np.tan(np.radians(fov / 2.0)), 1e-3)

    def _on_draw(self):
        if self._gpu_mode:
            self._on_draw_gl()
        else:
            self._on_draw_mpl()

    def _on_draw_gl(self):
        tc = self._theme_colors
        self._style_3d_axes(tc)
        self._set_item_visible(self._grid_item, self.get_grid())

        if not self._hold_btn.get_val():
            self._clear_data_items()
            self._hold_color_offset = 0
        else:
            self._hold_color_offset += 1

        labels = self.get_plotlabels()
        self._title_label.setText(labels['title'])

        # PROJECTION TYPE — pyqtgraph's GLViewWidget is always a perspective
        # (frustum) camera; 'orthographic' is approximated with a near-zero
        # field of view (a standard pseudo-ortho trick), compensated for in
        # _apply_scene_bounds() so the scene doesn't appear to shrink.
        self.view.opts['fov'] = 1.0 if self._ortho_btn.get_val() else 60.0

        # VIEW ANGLE (mouse-drag rotation updates elevation/azimuth directly
        # and bypasses this method, so re-applying the stored values here is safe)
        elev, azim = self.get_view()
        self.view.opts['elevation'] = elev
        self.view.opts['azimuth'] = azim

        if self._data is None:
            self._update_legend([])
            self._apply_scene_bounds()
            self.view.update()
            return

        plot_type = self.get_plottype()
        lw = self.get_linewidth()
        legend_entries = []
        all_pts = []
        for idx, data in enumerate(self._data):
            data = np.asarray(data)
            label = (self._labels[idx] if idx < len(self._labels) else None) or f'in{idx}'
            # shift the color cycle on each accumulated "hold" draw so the
            # newest data doesn't land on top of the same-port color again
            color_hex = self._port_colors[(idx + self._hold_color_offset) % len(self._port_colors)]

            if data.ndim < 2 or data.shape[-1] != 3:
                log.warning(f'Matplotlib3D: unsupported data shape {data.shape} for {label}, '
                            f'last axis must have size 3 (x,y,z), skipping')
                continue

            if data.size == 0 or not np.isfinite(data).all():
                log.warning(f'Matplotlib3D: empty or non-finite data for {label}, skipping')
                continue

            if data.ndim == 2:
                pts = np.ascontiguousarray(data.reshape(-1, 3), dtype=np.float32)
                n = max(pts.shape[0], 1)
                al = max(1.0 - 1.0 / np.log2(max(n, 2)), 0.6)
                rgba = _hex_to_rgba(color_hex, al)
                if plot_type == 'Line':
                    item = gl.GLLinePlotItem(pos=pts, color=rgba, width=lw,
                                              antialias=True, mode='line_strip')
                else:
                    item = gl.GLScatterPlotItem(pos=pts, color=rgba, size=6, pxMode=True)
                self.view.addItem(item)
                self._data_items.append(item)
                all_pts.append(pts)
                legend_entries.append((label, color_hex))

            else:
                X, Y, Z = data[..., 0], data[..., 1], data[..., 2]
                verts, faces = _grid_to_mesh(X, Y, Z)
                rgba = _hex_to_rgba(color_hex, 0.85)
                draw_edges = plot_type == 'Wireframe'
                md = gl.MeshData(vertexes=verts, faces=faces)
                item = gl.GLMeshItem(meshdata=md, color=rgba, edgeColor=rgba,
                                      shader='shaded', smooth=False, computeNormals=not draw_edges,
                                      drawFaces=not draw_edges, drawEdges=True)
                self.view.addItem(item)
                self._data_items.append(item)
                all_pts.append(verts)
                legend_entries.append((label, color_hex))

        self._update_legend(legend_entries)

        if self.get_autoscale() and all_pts:
            pts_cat = np.concatenate(all_pts, axis=0)
            lo, hi = pts_cat.min(axis=0), pts_cat.max(axis=0)
            self.set_xlim((float(lo[0]), float(hi[0])), quiet=True)
            self.set_ylim((float(lo[1]), float(hi[1])), quiet=True)
            self.set_zlim((float(lo[2]), float(hi[2])), quiet=True)

        self._apply_scene_bounds()
        self.view.update()

    def _on_draw_mpl(self):
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
