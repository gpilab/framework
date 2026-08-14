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
# Date: 2013 Oct 30
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
try:
    from matplotlib.backends.backend_qt import SubplotToolQt
except ImportError:
    SubplotToolQt = None

# Dark palette — matches GPI's dark Fusion theme (gpi/theme.py)
_MPL_FIG_FACE = '#353535'
_MPL_AX_FACE  = '#1e1e1e'
_MPL_SPINE    = '#555555'
_MPL_TICK     = '#aaaaaa'
_MPL_TEXT     = '#dcdcdc'
_MPL_GRID     = '#3a3a3a'

# Default theme dict — single source of truth for all color reset paths
_MPL_DEFAULT_THEME = {
    'fig_face': _MPL_FIG_FACE,
    'ax_face':  _MPL_AX_FACE,
    'spine':    _MPL_SPINE,
    'tick':     _MPL_TICK,
    'text':     _MPL_TEXT,
    'grid':     _MPL_GRID,
    'refline':  _MPL_SPINE,
}

_MPL_COLORS_FILE = os.path.join(os.path.dirname(os.path.realpath(gpi.__file__)), 'matplotlib_colors.json')

def _load_mpl_colors():
    """Return saved color dict, or {} if the file doesn't exist yet."""
    try:
        with open(_MPL_COLORS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_mpl_colors(port_colors, theme_colors):
    """Persist color palette to ~/gpi/matplotlib_colors.json."""
    try:
        os.makedirs(os.path.dirname(_MPL_COLORS_FILE), exist_ok=True)
        with open(_MPL_COLORS_FILE, 'w') as f:
            json.dump({'portColors': list(port_colors),
                       'themeColors': dict(theme_colors)}, f, indent=2)
    except Exception as e:
        log.warning(f'Matplotlib: could not save color settings: {e}')

def _style_color_btn(btn, hex_color):
    """Style a QPushButton as a color swatch with auto foreground contrast."""
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

class NavbarTools(NavigationToolbar):
    # list of toolitems to add to the toolbar, format is:
    # (
    #   text, # the text of the button (often not visible to users)
    #   tooltip_text, # the tooltip shown on hover (where possible)
    #   image_file, # name of the image for the button (without the extension)
    #   name_of_method, # name of the method in NavigationToolbar2 to call
    # )
    toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to  previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        (None, None, None, None),
        #('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
      )

    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)

###############################################################################
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Pierre Raybau
# Licensed under the terms of the MIT License
# see the mpl licenses directory for a copy of the license

"""Module that provides a GUI-based editor for matplotlib's figure options"""

#from __future__ import print_function
import os.path as osp

try:
    import matplotlib.backends.qt_editor.formlayout as formlayout
except ImportError:
    formlayout = None
    log.debug("matplotlib qt_editor.formlayout not available — figure options editor disabled")

from matplotlib import markers

def get_icon(name):
    basedir = osp.join(matplotlib.get_data_path(), 'images')
    return QtGui.QIcon(osp.join(basedir, name))

LINESTYLES = {
              '-': 'Solid',
              '--': 'Dashed',
              '-.': 'DashDot',
              ':': 'Dotted',
              'steps': 'Steps',
              'none': 'None',
              }

MARKERS = markers.MarkerStyle.markers

COLORS = {'b': '#0000ff', 'g': '#00ff00', 'r': '#ff0000', 'c': '#00ffff',
          'm': '#ff00ff', 'y': '#ffff00', 'k': '#000000', 'w': '#ffffff'}

def col2hex(color):
    """Convert matplotlib color to hex"""
    return COLORS.get(color, color)

def figure_edit(axes, parent=None):
    """Edit matplotlib figure options"""
    sep = (None, None) # separator

    has_curve = len(axes.get_lines()) > 0

    # Get / General
    #xmin, xmax = axes.get_xlim()
    #ymin, ymax = axes.get_ylim()
    #general = [('Title', axes.get_title()),
    #           sep,
    #           (None, "<b>X-Axis</b>"),
    #           ('Min', xmin), ('Max', xmax),
    #           ('Label', axes.get_xlabel()),
    #           ('Scale', [axes.get_xscale(), 'linear', 'log']),
    #           sep,
    #           (None, "<b>Y-Axis</b>"),
    #           ('Min', ymin), ('Max', ymax),
    #           ('Label', axes.get_ylabel()),
    #           ('Scale', [axes.get_yscale(), 'linear', 'log'])
    #           ]

    if not has_curve:
        return

    if has_curve:
        # Get / Curves
        linedict = {}
        for line in axes.get_lines():
            label = line.get_label()
            if label == '_nolegend_':
                continue
            linedict[label] = line
        curves = []
        linestyles = LINESTYLES.items()
        markers = MARKERS.items()
        curvelabels = sorted(linedict.keys())
        for label in curvelabels:
            line = linedict[label]
            curvedata = [
                         ('Label', label),
                         sep,
                         (None, '<b>Line</b>'),
                         ('Style', [line.get_linestyle()] + list(linestyles)),
                         ('Width', line.get_linewidth()),
                         ('Color', col2hex(line.get_color())),
                         sep,
                         (None, '<b>Marker</b>'),
                         ('Style', [line.get_marker()] + list(markers)),
                         ('Size', line.get_markersize()),
                         ('Facecolor', col2hex(line.get_markerfacecolor())),
                         ('Edgecolor', col2hex(line.get_markeredgecolor())),
                         ]
            curves.append([curvedata, label, ""])

    #datalist = [(general, "Axes", "")]
    #if has_curve:
    #datalist.append((curves, "Curves", ""))
    datalist = [(curves, "Curves", "")]

    def apply_callback(data):
        """This function will be called to apply changes"""
        #if has_curve:
        #    general, curves = data
        #else:
        #    general, = data

        curves = data[0]

        # Set / General
        #title, xmin, xmax, xlabel, xscale, ymin, ymax, ylabel, yscale = general
        #axes.set_xscale(xscale)
        #axes.set_yscale(yscale)
        #axes.set_title(title)
        #axes.set_xlim(xmin, xmax)
        #axes.set_xlabel(xlabel)
        #axes.set_ylim(ymin, ymax)
        #axes.set_ylabel(ylabel)

        if has_curve:
            # Set / Curves
            for index, curve in enumerate(curves):
                line = linedict[curvelabels[index]]
                label, linestyle, linewidth, color, \
                    marker, markersize, markerfacecolor, markeredgecolor = curve
                line.set_label(label)
                line.set_linestyle(linestyle)
                line.set_linewidth(linewidth)
                line.set_color(color)
                if marker != 'none':
                    line.set_marker(marker)
                    line.set_markersize(markersize)
                    line.set_markerfacecolor(markerfacecolor)
                    line.set_markeredgecolor(markeredgecolor)

        # Redraw
        figure = axes.get_figure()
        figure.canvas.draw()

    if formlayout is not None:
        data = formlayout.fedit(datalist, title="Figure options", parent=parent, icon=get_icon('qt4_editor_options.svg'), apply=apply_callback)

        if data is not None:
            apply_callback(data)
###############################################################################


class SpacingDialog(QtWidgets.QDialog):
    """Subplot margin / spacing editor — replaces the broken SubplotToolQt."""

    _PARAMS = [
        ('left',   'Left margin',    0.0, 1.0),
        ('right',  'Right margin',   0.0, 1.0),
        ('top',    'Top margin',     0.0, 1.0),
        ('bottom', 'Bottom margin',  0.0, 1.0),
        ('wspace', 'Column spacing', 0.0, 2.0),
        ('hspace', 'Row spacing',    0.0, 2.0),
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
        defaults = {'left': 0.111, 'right': 0.913, 'top': 0.912,
                    'bottom': 0.119, 'wspace': 0.2, 'hspace': 0.2}
        for k, v in defaults.items():
            self._spins[k].setValue(v)

    def sync_from_figure(self):
        for key, spin in self._spins.items():
            spin.blockSignals(True)
            spin.setValue(getattr(self.fig.subplotpars, key))
            spin.blockSignals(False)


class LineOptionsDialog(QtWidgets.QDialog):
    """Per-line color / style / width editor — replaces the removed formlayout."""

    _STYLES = [('-', 'Solid'), ('--', 'Dashed'), ('-.', 'Dash-Dot'),
               (':', 'Dotted'), ('none', 'None')]

    def __init__(self, axes, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Line Options')
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowStaysOnTopHint)
        self.axes = axes
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        lines = [l for l in self.axes.get_lines()
                 if l.get_label() != '_nolegend_']
        if not lines:
            root.addWidget(QtWidgets.QLabel('No labelled lines to edit.'))
            root.addWidget(QtWidgets.QPushButton('Close', clicked=self.accept))
            return

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(container)
        vbox.setSpacing(6)

        for line in lines:
            group = QtWidgets.QGroupBox(line.get_label())
            form  = QtWidgets.QFormLayout(group)
            form.setSpacing(4)

            col_btn = QtWidgets.QPushButton()
            col_btn.setFixedSize(100, 22)
            _style_color_btn(col_btn, line.get_color())
            col_btn.clicked.connect(lambda ch, l=line, b=col_btn: self._pick(l, b))
            form.addRow('Color', col_btn)

            lw = QtWidgets.QDoubleSpinBox()
            lw.setRange(0.1, 20.0)
            lw.setSingleStep(0.5)
            lw.setValue(line.get_linewidth())
            lw.valueChanged.connect(lambda v, l=line: self._apply(l, 'linewidth', v))
            form.addRow('Width', lw)

            ls = QtWidgets.QComboBox()
            for key, lbl in self._STYLES:
                ls.addItem(lbl, key)
            cur = line.get_linestyle()
            ls.setCurrentIndex(next((i for i, (k, _) in enumerate(self._STYLES) if k == cur), 0))
            ls.currentIndexChanged.connect(lambda i, l=line, c=ls: self._apply(l, 'linestyle', c.itemData(i)))
            form.addRow('Style', ls)

            al = QtWidgets.QDoubleSpinBox()
            al.setRange(0.0, 1.0)
            al.setSingleStep(0.05)
            al.setDecimals(2)
            al.setValue(line.get_alpha() if line.get_alpha() is not None else 1.0)
            al.valueChanged.connect(lambda v, l=line: self._apply(l, 'alpha', v))
            form.addRow('Opacity', al)

            vbox.addWidget(group)

        vbox.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll)
        close_btn = QtWidgets.QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)
        self.resize(300, 420)

    def _pick(self, line, btn):
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(line.get_color()), self, 'Line Color')
        if color.isValid():
            line.set_color(color.name())
            _style_color_btn(btn, color.name())
            self.axes.get_figure().canvas.draw_idle()

    def _apply(self, line, attr, val):
        getattr(line, f'set_{attr}')(val)
        self.axes.get_figure().canvas.draw_idle()


class ColorPaletteDialog(QtWidgets.QDialog):
    """Floating dialog for editing all Matplotlib node colors."""

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

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(12, 12, 12, 12)

        root.addWidget(self._make_theme_group(
            'Background',
            [('fig_face', 'Figure background'),
             ('ax_face',  'Axes background')]))

        root.addWidget(self._make_theme_group(
            'Text & Borders',
            [('text',  'Title / axis labels'),
             ('tick',  'Tick marks'),
             ('spine', 'Axes border')]))

        root.addWidget(self._make_theme_group(
            'Grid & Reference Lines',
            [('grid',    'Grid'),
             ('refline', 'x=0 / y=0 lines')]))

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

    # ------------------------------------------------------------------
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
        """Sync all swatch buttons to the current colors in the plot widget."""
        for key, color in self._plot._theme_colors.items():
            if key in self._swatches:
                _style_color_btn(self._swatches[key], color)
        for i, color in enumerate(self._plot._port_colors):
            k = f'port_{i}'
            if k in self._swatches:
                _style_color_btn(self._swatches[k], color)


class MatplotDisplay(gpi.GenericWidgetGroup):

    """Embeds the matplotlib figure window.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        # gpi interface
        self._collapsables = []
        self._subplotSettings = {}
        #self._subplotPosition = {'right': 0.9, 'bottom': 0.12, 'top': 0.9, 'wspace': 0.2, 'hspace': 0.2, 'left': 0.125}
        self._subplotPosition = {'right': 0.913, 'bottom': 0.119, 'top': 0.912, 'wspace': 0.2, 'hspace': 0.2, 'left': 0.111}
        #self._subplot_keepers = ['yscale', 'xscale'] # linear, log
        self._subplot_keepers = []
        self._lineSettings = []
        self._line_keepers = ['linewidth', 'linestyle', 'label', 'marker', 'markeredgecolor', 'markerfacecolor', 'markersize', 'color', 'alpha']

        # matplotlib tab10 default color cycle
        self._default_port_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
            '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
        ]
        self._port_colors  = list(self._default_port_colors)
        self._theme_colors = dict(_MPL_DEFAULT_THEME)
        self._palette_window = None

        # since drawing is slow, don't do it as often, use the timer as a
        # debouncer
        self._updatetimer = QtCore.QTimer()
        self._updatetimer.setSingleShot(True)
        self._updatetimer.timeout.connect(self._on_draw)
        self._updatetimer.setInterval(10)

        # plot specific UI side panel
        #  -sets options for plot window so this needs to be run first
        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)  # no spaces around this item
        vbox.setSpacing(0)

        # AUTOSCALE
        self._autoscale_btn = gpi.widgets.BasicPushButton(self)
        self._autoscale_btn.set_toggle(True)
        self._autoscale_btn.set_button_title('autoscale')
        self._autoscale_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._autoscale_btn)

        # GRID
        self._grid_btn = gpi.widgets.BasicPushButton(self)
        self._grid_btn.set_toggle(True)
        self._grid_btn.set_button_title('grid')
        self._grid_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._grid_btn)

        # X/Y LIMITS
        lims = QtWidgets.QGridLayout()
        self._xl = gpi.widgets.BasicDoubleSpinBox(self)
        self._xh = gpi.widgets.BasicDoubleSpinBox(self)
        self._yl = gpi.widgets.BasicDoubleSpinBox(self)
        self._yh = gpi.widgets.BasicDoubleSpinBox(self)
        self._xl.valueChanged.connect(self.on_draw)
        self._xh.valueChanged.connect(self.on_draw)
        self._yl.valueChanged.connect(self.on_draw)
        self._yh.valueChanged.connect(self.on_draw)
        self._xl.set_immediate(True)
        self._xh.set_immediate(True)
        self._yl.set_immediate(True)
        self._yh.set_immediate(True)
        self._xl.set_label('max')
        self._xh.set_label('min')
        self._xl.set_decimals(7)
        self._xh.set_decimals(7)
        self._yl.set_decimals(7)
        self._yh.set_decimals(7)
        self._xlab = QtWidgets.QLabel('x limits')
        self._ylab = QtWidgets.QLabel('y limits')
        #self._maxlab = QtWidgets.QLabel('max')
        #self._minlab = QtWidgets.QLabel('min')
        #lims.addWidget(self._maxlab,1,0,1,1)
        #lims.addWidget(self._minlab,2,0,1,1)
        lims.addWidget(self._xlab,0,1,1,1,alignment=QtCore.Qt.AlignHCenter)
        lims.addWidget(self._xh,1,1,1,1,alignment=QtCore.Qt.AlignHCenter)
        lims.addWidget(self._xl,2,1,1,1,alignment=QtCore.Qt.AlignHCenter)
        lims.addWidget(self._ylab,0,2,1,1,alignment=QtCore.Qt.AlignHCenter)
        lims.addWidget(self._yh,1,2,1,1,alignment=QtCore.Qt.AlignHCenter)
        lims.addWidget(self._yl,2,2,1,1,alignment=QtCore.Qt.AlignHCenter)
        self._collapsables.append(self._xlab)
        self._collapsables.append(self._ylab)
        self._collapsables.append(self._xl)
        self._collapsables.append(self._xh)
        self._collapsables.append(self._yl)
        self._collapsables.append(self._yh)
        #self._collapsables.append(self._minlab)
        #self._collapsables.append(self._maxlab)

        # TICK MARKS
        ticks = QtWidgets.QGridLayout()
        self._x_numticks = gpi.widgets.BasicSpinBox(self)
        self._x_numticks.valueChanged.connect(self.on_draw)
        self._y_numticks = gpi.widgets.BasicSpinBox(self)
        self._y_numticks.valueChanged.connect(self.on_draw)
        self._x_ticks = QtWidgets.QLineEdit()
        self._y_ticks = QtWidgets.QLineEdit()
        self._x_ticks.textChanged.connect(lambda txt: self.check_validticks(self._x_ticks))
        self._y_ticks.textChanged.connect(lambda txt: self.check_validticks(self._y_ticks))
        self._x_ticks.setPlaceholderText('comma separated list of x labels')
        self._y_ticks.setPlaceholderText('comma separated list of y labels')
        self._x_ticks.returnPressed.connect(self.on_draw)
        self._y_ticks.returnPressed.connect(self.on_draw)
        self._x_numticks.set_immediate(True)
        self._y_numticks.set_immediate(True)
        self._x_numticks.set_min(2)
        self._y_numticks.set_min(2)
        self._x_numticks.set_max(100)
        self._y_numticks.set_max(100)
        self._x_numticks.set_val(5)
        self._y_numticks.set_val(5)
        self._x_numticks.set_label('x ticks')
        self._y_numticks.set_label('y ticks')
        ticks.addWidget(self._x_numticks, 0,0,1,1)
        ticks.addWidget(self._y_numticks, 1,0,1,1)
        ticks.addWidget(self._x_ticks, 0,1,1,1)
        ticks.addWidget(self._y_ticks, 1,1,1,1)
        self._collapsables.append(self._x_numticks)
        self._collapsables.append(self._y_numticks)
        self._collapsables.append(self._x_ticks)
        self._collapsables.append(self._y_ticks)

        # TITLE, XLABEL, YLABEL
        plotlabels = QtWidgets.QHBoxLayout()
        self._plot_title = QtWidgets.QLineEdit()
        self._plot_xlab = QtWidgets.QLineEdit()
        self._plot_ylab = QtWidgets.QLineEdit()
        self._plot_title.setPlaceholderText('title')
        self._plot_xlab.setPlaceholderText('x label')
        self._plot_ylab.setPlaceholderText('y label')
        self._plot_title.returnPressed.connect(self.on_draw)
        self._plot_xlab.returnPressed.connect(self.on_draw)
        self._plot_ylab.returnPressed.connect(self.on_draw)
        plotlabels.addWidget(self._plot_title)
        plotlabels.addWidget(self._plot_xlab)
        plotlabels.addWidget(self._plot_ylab)
        self._collapsables.append(self._plot_title)
        self._collapsables.append(self._plot_xlab)
        self._collapsables.append(self._plot_ylab)

        # XSCALE, YSCALE
        self._xscale_btn = gpi.widgets.BasicPushButton(self)
        self._xscale_btn.set_toggle(True)
        self._xscale_btn.set_button_title('log(x)')
        self._xscale_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._xscale_btn)
        self._yscale_btn = gpi.widgets.BasicPushButton(self)
        self._yscale_btn.set_toggle(True)
        self._yscale_btn.set_button_title('log(y)')
        self._yscale_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._yscale_btn)

        scale_options_layout = QtWidgets.QHBoxLayout()
        scale_options_layout.addWidget(self._xscale_btn)
        scale_options_layout.addWidget(self._yscale_btn)

        # LEGEND
        self._legend_btn = gpi.widgets.BasicPushButton(self)
        self._legend_btn.set_toggle(True)
        self._legend_btn.set_button_title('legend')
        self._legend_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._legend_btn)

        # HOLD
        self._hold_btn = gpi.widgets.BasicPushButton(self)
        self._hold_btn.set_toggle(True)
        self._hold_btn.set_button_title('hold')
        #self._hold_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._hold_btn)

        # MOVE AXES TO ORIGIN
        # self._origin_axes_btn = gpi.widgets.BasicPushButton(self)
        # self._origin_axes_btn.set_toggle(True)
        # self._origin_axes_btn.set_button_title("axes at (0,0)")
        # self._collapsables.append(self._origin_axes_btn)

        # RESET
        self._reset_btn = gpi.widgets.BasicPushButton(self)
        self._reset_btn.set_toggle(False)
        self._reset_btn.set_button_title('reset')
        self._reset_btn.valueChanged.connect(self._init_parms_)
        self._collapsables.append(self._reset_btn)

        # X=0, Y=0
        self._xeq0_btn = gpi.widgets.BasicPushButton(self)
        self._xeq0_btn.set_toggle(True)
        self._xeq0_btn.set_button_title('x=0')
        self._xeq0_btn.set_val(True)
        self._xeq0_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._xeq0_btn)
        self._yeq0_btn = gpi.widgets.BasicPushButton(self)
        self._yeq0_btn.set_toggle(True)
        self._yeq0_btn.set_button_title('y=0')
        self._yeq0_btn.set_val(True)
        self._yeq0_btn.valueChanged.connect(self.on_draw)
        self._collapsables.append(self._yeq0_btn)

        # LINE OPTIONS
        self._lino_btn = gpi.widgets.BasicPushButton(self)
        self._lino_btn.set_toggle(False)
        self._lino_btn.set_button_title('line options')
        self._lino_btn.valueChanged.connect(self.lineOptionsDialog)
        self._collapsables.append(self._lino_btn)

        # SUBPLOT SPACING OPTIONS
        self._subplotso_btn = gpi.widgets.BasicPushButton(self)
        self._subplotso_btn.set_toggle(False)
        self._subplotso_btn.set_button_title('spacing options')
        self._subplotso_btn.valueChanged.connect(self.subplotSpacingOptions)
        self._collapsables.append(self._subplotso_btn)
        self.adj_window = None

        # COLOR PALETTE button — opens the floating palette dialog
        self._palette_btn = gpi.widgets.BasicPushButton(self)
        self._palette_btn.set_toggle(False)
        self._palette_btn.set_button_title('color palette')
        self._palette_btn.valueChanged.connect(self.colorPaletteDialog)
        self._collapsables.append(self._palette_btn)

        plot_options_layout = QtWidgets.QHBoxLayout()
        plot_options_layout.addWidget(self._subplotso_btn)
        plot_options_layout.addWidget(self._lino_btn)
        plot_options_layout.addWidget(self._palette_btn)

        grid_legend_lyt = QtWidgets.QHBoxLayout()
        grid_legend_lyt.addWidget(self._legend_btn)
        grid_legend_lyt.addWidget(self._grid_btn)

        autoscale_scale_lyt = QtWidgets.QHBoxLayout()
        autoscale_scale_lyt.addWidget(self._autoscale_btn)
        autoscale_scale_lyt.addWidget(self._xscale_btn)
        autoscale_scale_lyt.addWidget(self._yscale_btn)
        autoscale_scale_lyt.addWidget(self._xeq0_btn)
        autoscale_scale_lyt.addWidget(self._yeq0_btn)

        # HLINES
        self._hline1 = QtWidgets.QFrame()
        self._hline1.setFrameStyle(QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken)
        self._hline1.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self._collapsables.append(self._hline1)

        self._hline2 = QtWidgets.QFrame()
        self._hline2.setFrameStyle(QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken)
        self._hline2.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self._collapsables.append(self._hline2)

        self._hline3 = QtWidgets.QFrame()
        self._hline3.setFrameStyle(QtWidgets.QFrame.HLine | QtWidgets.QFrame.Sunken)
        self._hline3.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self._collapsables.append(self._hline3)

        spc = 10
        self._spacer1 = QtWidgets.QSpacerItem(1,spc,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._spacer2 = QtWidgets.QSpacerItem(1,spc,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._spacer3 = QtWidgets.QSpacerItem(1,spc,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._spacer4 = QtWidgets.QSpacerItem(1,spc,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._spacer5 = QtWidgets.QSpacerItem(1,spc,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._spacer6 = QtWidgets.QSpacerItem(1,spc,QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._collapsables.append(self._spacer1)
        self._collapsables.append(self._spacer2)
        self._collapsables.append(self._spacer3)
        self._collapsables.append(self._spacer4)
        self._collapsables.append(self._spacer5)
        self._collapsables.append(self._spacer6)

        # panel layout
        vbox.addLayout(plotlabels)

        vbox.addSpacerItem(self._spacer1)
        vbox.addWidget(self._hline1)
        vbox.addSpacerItem(self._spacer2)

        vbox.addLayout(lims)
        #vbox.addLayout(scale_options_layout)
        #vbox.addWidget(self._autoscale_btn)
        vbox.addLayout(autoscale_scale_lyt)

        vbox.addSpacerItem(self._spacer3)
        vbox.addWidget(self._hline2)
        vbox.addSpacerItem(self._spacer4)

        vbox.addLayout(ticks)
        #vbox.addWidget(self._legend_btn)
        vbox.addLayout(grid_legend_lyt)
        vbox.addLayout(plot_options_layout)
        #vbox.addWidget(self._lino_btn)
        #vbox.addWidget(self._subplotso_btn)

        vbox.addSpacerItem(self._spacer5)
        vbox.addWidget(self._hline3)
        vbox.addSpacerItem(self._spacer6)

        vbox.addWidget(self._hold_btn)
        # vbox.addWidget(self._origin_axes_btn)

        vbox.insertStretch(-1,1)
        vbox.addWidget(self._reset_btn)

        # plot window
        self._data   = None
        self._labels = []
        self._plotwindow = self.create_main_frame()

        # put side panel and plot window together
        hbox = QtWidgets.QHBoxLayout()
        hbox.addLayout(vbox)
        hbox.addLayout(self._plotwindow)
        hbox.setStretch(0,0)
        hbox.setStretch(1,11)
        self.setLayout(hbox)

        #self._on_draw() # draw once to get initial settings
        #self.copySubplotSettings()

        # Don't hide side-panel options by default
        self.set_collapsed(False)
        self.set_grid(True)
        self.set_autoscale(True)

        # DEFAULTS
        self._init_parms_()

        # Load globally-saved color settings — must be AFTER _init_parms_()
        # because _init_parms_ calls _init_parms_colors() which resets to defaults.
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
        """Open (or raise) the floating Color Palette window."""
        if self._palette_window is not None and self._palette_window.isVisible():
            self._palette_window.raise_()
            self._palette_window.activateWindow()
            return
        self._palette_window = ColorPaletteDialog(self, parent=None)
        self._palette_window.show()

    def _init_parms_colors(self):
        """Reset colors to defaults (called by dialog Reset and _init_parms_)."""
        self._port_colors  = list(self._default_port_colors)
        self._theme_colors = dict(_MPL_DEFAULT_THEME)

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
        """bool | Only collapse the display options, not the Plot window.
        """
        self._isCollapsed = val
        for wdg in self._collapsables:
            if hasattr(wdg, 'setVisible'):
                wdg.setVisible(not val)

    def set_xlim(self, val, quiet=False):
        '''tuple of floats (min, max)
        '''
        self._xh.set_val(val[0])
        self._xl.set_val(val[1])
        if not quiet:
            self.on_draw()

    def set_ylim(self, val, quiet=False):
        '''tuple of floats (min, max)
        '''
        self._yh.set_val(val[0])
        self._yl.set_val(val[1])
        if not quiet:
            self.on_draw()

    def set_plotOptions(self, val):
        self._subplotSettings = val

    def set_lineOptions(self, val):
        self._lineSettings = val

    def set_plotPosition(self, val):
        self._subplotPosition = val

    def set_ticks(self, s):
        self._x_numticks.set_val(s['xticknum'])
        self._y_numticks.set_val(s['yticknum'])
        self._x_ticks.setText(s['xticks'])
        self._y_ticks.setText(s['yticks'])

    def set_plotlabels(self, s):
        self._plot_title.setText(s['title'])
        self._plot_xlab.setText(s['xlabel'])
        self._plot_ylab.setText(s['ylabel'])
        self.on_draw()

    def set_legend(self, val):
        self._legend_btn.set_val(val)
        self.on_draw()

    def set_xline(self, val):
        self._yeq0_btn.set_val(val)
        self.on_draw()

    def set_yline(self, val):
        self._xeq0_btn.set_val(val)
        self.on_draw()

    def set_scale(self, val):
        self._xscale_btn.set_val(val['xscale'])
        self._yscale_btn.set_val(val['yscale'])
        self.on_draw()

    # getters
    def get_val(self):
        return self._data

    def get_grid(self):
        return self._grid_btn.get_val()

    def get_autoscale(self):
        return self._autoscale_btn.get_val()

    def get_xlim(self):
        return (self._xh.get_val(), self._xl.get_val())

    def get_ylim(self):
        return (self._yh.get_val(), self._yl.get_val())

    def get_plotOptions(self):
        return self._subplotSettings

    def get_lineOptions(self):
        return self._lineSettings

    def get_plotPosition(self):
        return self._subplotPosition

    def get_ticks(self):
        s = {}
        s['xticknum'] = self._x_numticks.get_val()
        s['yticknum'] = self._y_numticks.get_val()
        s['xticks'] = str(self._x_ticks.text())
        s['yticks'] = str(self._y_ticks.text())
        return s

    def get_plotlabels(self):
        s = {}
        s['title'] = str(self._plot_title.text())
        s['xlabel'] = str(self._plot_xlab.text())
        s['ylabel'] = str(self._plot_ylab.text())
        return s

    def get_legend(self):
        return self._legend_btn.get_val()

    def get_xline(self):
        return self._yeq0_btn.get_val()

    def get_yline(self):
        return self._xeq0_btn.get_val()

    def get_scale(self):
        s = {}
        s['xscale'] = self._xscale_btn.get_val()
        s['yscale'] = self._yscale_btn.get_val()
        return s

    # support
    def check_validticks(self, tickwdg):
        s = tickwdg.text()
        comma_cnt = s.count(',')
        if (comma_cnt > 0) or (len(s) == 0):
            color = '#ffffff' # white
            tickwdg.setStyleSheet('QLineEdit { background-color: %s }' % color)
            return

        #color = '#fff79a' # yellow
        color = '#f6989d' # red
        tickwdg.setStyleSheet('QLineEdit { background-color: %s }' % color)
        return

    def create_main_frame(self):
        self.fig = Figure((6.0, 4.8), dpi=100, facecolor=_MPL_FIG_FACE, linewidth=0.0)
        self.axes = None
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.canvas.setFocus()

        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        #self.mpl_toolbar = NavigationToolbar(self.canvas, self)
        self.mpl_toolbar = NavbarTools(self.canvas, self)
        self.mpl_toolbar.actionTriggered.connect(self.copySubplotSettings)

        self.canvas.mpl_connect('key_press_event', self.on_key_press)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.canvas)  # the matplotlib canvas
        vbox.addWidget(self.mpl_toolbar)
        return vbox
        #self.setLayout(vbox)

    def lineOptionsDialog(self):
        if self.axes is None:
            log.debug("Matplotlib: no axes available, skipping line editor")
            return
        dlg = LineOptionsDialog(self.axes, parent=None)
        dlg.finished.connect(lambda _: (self.copySubplotSettings(), self.on_draw()))
        dlg.show()

    def subplotSpacingOptions(self):
        if self.fig is None:
            return
        if self.adj_window is not None and self.adj_window.isVisible():
            self.adj_window.sync_from_figure()
            self.adj_window.raise_()
            self.adj_window.activateWindow()
            return
        self.adj_window = SpacingDialog(self.fig, parent=None)
        self.adj_window.finished.connect(self.copySubplotSettings)
        self.adj_window.show()

    def copySubplotSettings(self):
        '''Get a copy of the settings found in the 'Figure Options' editor.
        '''
        if self.axes is None:
            return

        # subplot settings
        for k in self._subplot_keepers:
            self._subplotSettings[k] = getattr(self.axes, 'get_'+k)()

        # line settings
        self._lineSettings = []
        for l in self.axes.get_lines():
            s = {}
            for k in self._line_keepers:
                s[k] = getattr(l, 'get_'+k)()
            self._lineSettings.append(s)

        # subplot position
        self._subplotPosition = {}
        self._subplotPosition['left'] = self.fig.subplotpars.left
        self._subplotPosition['right'] = self.fig.subplotpars.right
        self._subplotPosition['top'] = self.fig.subplotpars.top
        self._subplotPosition['bottom'] = self.fig.subplotpars.bottom
        self._subplotPosition['wspace'] = self.fig.subplotpars.wspace
        self._subplotPosition['hspace'] = self.fig.subplotpars.hspace

    def applySubplotSettings(self):
        '''Everytime the plot is drawn it looses its 'Figure Options' so just
        make sure they are applied again.
        '''
        # subplot settings
        for k in self._subplot_keepers:
            if k in self._subplotSettings:
                getattr(self.axes, 'set_'+k)(self._subplotSettings[k])

        #subplot position
        self.fig.subplots_adjust(**self._subplotPosition)

    def _init_parms_(self):
        '''Default parameter settings
        '''
        self._subplotSettings = {}
        self._subplotPosition = {'right': 0.913, 'bottom': 0.119, 'top': 0.912, 'wspace': 0.2, 'hspace': 0.2, 'left': 0.111}
        self._lineSettings = []
        self._init_parms_colors()
        self.set_autoscale(True)
        self.set_grid(True)
        s = {}
        s['xticknum'] = 5
        s['yticknum'] = 5
        s['xticks'] = ''
        s['yticks'] = ''
        self.set_ticks(s)
        s = {}
        s['title'] = ''
        s['xlabel'] = ''
        s['ylabel'] = ''
        self.set_plotlabels(s)
        self.set_legend(False)
        s = {}
        s['xscale'] = False # linear
        s['yscale'] = False
        self.set_scale(s)
        self.on_draw()

    def on_draw(self):
        if not self._updatetimer.isActive():
            self._updatetimer.start()

    def _on_draw(self):

        # Create axes once; use cla() on redraw so the axes object (and the
        # navigation toolbar's view history) persists across draws.
        if self.axes is None:
            self.axes = self.fig.add_subplot(111)

        tc = self._theme_colors  # shorthand

        if not self._hold_btn.get_val():
            self.axes.cla()

        # --- Theme colors ---
        self.fig.set_facecolor(tc['fig_face'])
        self.axes.set_facecolor(tc['ax_face'])
        for spine in self.axes.spines.values():
            spine.set_color(tc['spine'])
        self.axes.tick_params(colors=tc['tick'], which='both')

        # AUTOSCALE and LIMITS
        self.axes.set_autoscale_on(self.get_autoscale())
        if not self.get_autoscale():
            self.axes.set_xlim(self.get_xlim())
            self.axes.set_ylim(self.get_ylim())

        # TITLE, XLABEL and YLABEL
        self.axes.set_title(
            self.get_plotlabels()['title'],
            fontweight='bold', fontsize=16, color=tc['text'])
        self.axes.set_xlabel(
            self.get_plotlabels()['xlabel'], fontsize=14, color=tc['text'])
        self.axes.set_ylabel(
            self.get_plotlabels()['ylabel'], fontsize=14, color=tc['text'])

        # XSCALE / YSCALE
        xscale_log = self.get_scale()['xscale']
        yscale_log = self.get_scale()['yscale']
        self.axes.set_xscale('log' if xscale_log else 'linear')
        self.axes.set_yscale('log' if yscale_log else 'linear')

        # GRID
        if self.get_grid():
            self.axes.grid(True, color=tc['grid'], linewidth=0.5)
        else:
            self.axes.grid(False)

        if self._data is None:
            self.canvas.draw()
            return

        # PLOT each data set with per-port label
        for idx, data in enumerate(self._data):
            label = (self._labels[idx] if idx < len(self._labels) else None) or f'in{idx}'
            ln = max(data.shape) if data.shape else 1
            lw = max(5.0 - np.log10(max(ln, 1)), 1.0)
            al = max(1.0 - 1.0 / np.log2(max(ln, 2)), 0.75)

            color = self._port_colors[idx % len(self._port_colors)]
            if data.shape[-1] == 2:
                self.axes.plot(data[..., 0], data[..., 1], alpha=al, lw=lw, label=label, color=color)
            else:
                self.axes.plot(data, alpha=al, lw=lw, label=label, color=color)

        # X=0, Y=0 reference lines
        if self.get_xline():
            self.axes.axhline(y=0, color=tc['refline'], lw=0.8, zorder=-1)
        if self.get_yline():
            self.axes.axvline(x=0, color=tc['refline'], lw=0.8, zorder=-1)

        # LEGEND
        if self.get_legend():
            self.axes.legend(
                facecolor=tc['fig_face'], edgecolor=tc['spine'],
                labelcolor=tc['text'])

        # AUTOSCALE — update spinboxes from actual axis limits
        if self.get_autoscale():
            self.set_xlim(self.axes.get_xlim(), quiet=True)
            self.set_ylim(self.axes.get_ylim(), quiet=True)

        # TICKS (log-scale aware)
        def _ticks(lim, n, is_log):
            lo, hi = lim
            if is_log and lo > 0 and hi > 0:
                return np.logspace(np.log10(lo), np.log10(hi), num=n)
            return np.linspace(lo, hi, num=n)

        xl = [s.strip() for s in self._x_ticks.text().split(',')]
        if len(xl) > 1 and xl[0]:
            self.axes.set_xticks(_ticks(self.axes.get_xlim(), len(xl), xscale_log))
            self.axes.set_xticklabels(xl)
        else:
            self.axes.set_xticks(
                _ticks(self.axes.get_xlim(), self._x_numticks.get_val(), xscale_log))

        yl = [s.strip() for s in self._y_ticks.text().split(',')]
        if len(yl) > 1 and yl[0]:
            self.axes.set_yticks(_ticks(self.axes.get_ylim(), len(yl), yscale_log))
            self.axes.set_yticklabels(yl)
        else:
            self.axes.set_yticks(
                _ticks(self.axes.get_ylim(), self._y_numticks.get_val(), yscale_log))

        # Re-apply tick colors after set_xticks/set_yticks regenerate labels
        self.axes.tick_params(colors=tc['tick'], which='both')

        self.applySubplotSettings()
        self.canvas.draw()

    def on_key_press(self, event):
        # print 'Matplotlib-> you pressed:' + str(event.key)
        # implement the default mpl key press events described at
        # http://matplotlib.org/users/navigation_toolbar.html#navigation-
        # keyboard-shortcuts
        try:
            from matplotlib.backend_bases import key_press_handler
            key_press_handler(event, self.canvas, self.mpl_toolbar)
        except Exception:
            pass  # key_press_handler not available in this matplotlib version


class ExternalNode(gpi.NodeAPI):

    """A Qt embedded plot window originally using the code from:
    http://matplotlib.org/examples/user_interfaces/embedding_in_qt4_wtoolbar.html
    Updated by DDB in Feb. 2020 using the qt5 code from:
    https://matplotlib.org/examples/user_interfaces/embedding_in_qt5.html
    keyboard shortcuts can be found here:
    http://matplotlib.org/users/navigation_toolbar.html#navigation-keyboard-shortcuts

    INPUTS
    Up to 8 data sets can be plotted simultaneously
      1D real-valued data are plotted as graph
      2D data where the 2nd dimension is 2 will be plotted as X-Y parametric plot, otherwise
      all other 2D data are plotted as series of 1D plots
    """

    def initUI(self):
        # Widgets
        self.addWidget('MatplotDisplay', 'Plot')

        # IO Ports
        self.inport_range = list(range(0, 8))
        for i in self.inport_range:
            self.addInPort('in' + str(i), 'NPYorTorch', kind='numpy', drange=(1,2), obligation=gpi.OPTIONAL)

    def compute(self):

        # check input ports for data; bundle with port name for legend labels
        in_lst = [(f'in{i}', self.getData('in' + str(i)))
                  for i in self.inport_range if self.getData('in' + str(i)) is not None]

        self.setAttr('Plot', val=in_lst)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_APPLOOP
