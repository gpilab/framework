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
from __future__ import print_function
import os
import matplotlib

print('matplotlib version: ', matplotlib.__version__)

import gpi
from gpi import QtCore, QtGui, QtWidgets

import numpy as np
from matplotlib.figure import Figure
#from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.backends.backend_qt5 import SubplotToolQt

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

    def _init_toolbar(self):
        self.basedir = os.path.join(matplotlib.rcParams[ 'datapath' ],'images')

        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self.addSeparator()
            else:
                a = self.addAction(self._icon(image_file + '.png'),
                                         text, getattr(self, callback))
                self._actions[callback] = a
                if callback in ['zoom', 'pan']:
                    a.setCheckable(True)
                if tooltip_text is not None:
                    a.setToolTip(tooltip_text)

        # Add the x,y location widget at the right side of the toolbar
        # The stretch factor is 1 which means any resizing of the toolbar
        # will resize this label instead of the buttons.
        if self.coordinates:
            self.locLabel = QtWidgets.QLabel( "", self )
            self.locLabel.setAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignTop )
            self.locLabel.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                  QtWidgets.QSizePolicy.Ignored))
            labelAction = self.addWidget(self.locLabel)
            labelAction.setVisible(True)

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
except:
    formlayout = None
    print("formlayout can't be found, line options will be disabled")

from matplotlib import markers

def get_icon(name):
    basedir = osp.join(matplotlib.rcParams['datapath'], 'images')
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

COLORS = {'b': '#0000ff', 'g': '#00ff00', 'r': '#ff0000', 'c': '#ff00ff',
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

        # since drawing is slow, don't do it as often, use the timer as a
        # debouncer
        self._on_draw_cnt = 0
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

        plot_options_layout = QtWidgets.QHBoxLayout()
        plot_options_layout.addWidget(self._subplotso_btn)
        plot_options_layout.addWidget(self._lino_btn)

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
        self._data = None
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

    # setters
    def set_val(self, data):
        '''Takes a list of npy arrays.
        '''
        if isinstance(data, list):
            self._data = data
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
        self.fig = Figure((6.0, 4.8), dpi=100, facecolor='0.98', linewidth=6.0, edgecolor='0.93')
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
            print("Matplotlib: no lines to modify, skipping line editor")
            return
        figure_edit(self.axes, self)
        self.copySubplotSettings()
        self.on_draw()

    def subplotSpacingOptions(self):
        if self.fig is None:
            return

        # don't allow the user to open extra windows
        if self.adj_window is not None:
            if self.adj_window.isActive():
                self.adj_window.raise_()
                return

        self.adj_window = MainWin_close()
        self.adj_window.window_closed.connect(self.copySubplotSettings)
        win = self.adj_window

        win.setWindowTitle("Subplot Configuration Tool")
        image = os.path.join( matplotlib.rcParams['datapath'],'images','matplotlib.png' )
        win.setWindowIcon(QtGui.QIcon( image ))

        tool = SubplotToolQt(self.fig, win)
        win.setCentralWidget(tool)
        win.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        win.show()

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
        self._on_draw_cnt += 1
        if not self._updatetimer.isActive():
            self._updatetimer.start()

    def _on_draw(self):

        # HOLD / Create New AXES
        if not self._hold_btn.get_val():
            self.fig.clear()
            self.axes = self.fig.add_subplot(111)

        # AUTOSCALE and LIMITS
        self.axes.set_autoscale_on(self.get_autoscale())
        if not self.get_autoscale():
            self.axes.set_xlim(self.get_xlim())
            self.axes.set_ylim(self.get_ylim())

        # TITLE, XLABEL and YLABEL
        self.axes.set_title(self.get_plotlabels()['title'], fontweight='bold', fontsize=16)
        self.axes.set_xlabel(self.get_plotlabels()['xlabel'], fontsize=14)
        self.axes.set_ylabel(self.get_plotlabels()['ylabel'], fontsize=14)

        # self.axes.plot(self.x, self.y, 'ro')
        # self.axes.imshow(self.data, interpolation='nearest')
        # self.axes.plot([1,2,3])

        # XSCALE
        if self.get_scale()['xscale']:
            self.axes.set_xscale('log')
        else:
            self.axes.set_xscale('linear')

        # YSCALE
        if self.get_scale()['yscale']:
            self.axes.set_yscale('log')
        else:
            self.axes.set_yscale('linear')

        # GRID
        ax_color = '0.5'
        if self.get_grid():
            self.axes.grid(self.get_grid(), color=ax_color)
        else:
            self.axes.grid(self.get_grid())

        # AXES SPINE COLOR
        self.axes.spines['bottom'].set_color(ax_color)
        self.axes.spines['top'].set_color(ax_color)
        self.axes.spines['right'].set_color(ax_color)
        self.axes.spines['left'].set_color(ax_color)
        try:
            # deprecated in Matplotlib 2.0
            self.axes.set_axis_bgcolor('0.97')
        except AttributeError:
            self.axes.set_facecolor('0.97')

        # if self._origin_axes_btn.get_val():
        #     self.axes.spines['left'].set_position('zero')
        #     self.axes.spines['bottom'].set_position('zero')
        #     self.axes.spines['left'].set_smart_bounds(True)
        #     self.axes.spines['bottom'].set_smart_bounds(True)
        #     self.axes.xaxis.set_ticks_position('bottom')
        #     self.axes.yaxis.set_ticks_position('left')

        if self._data is None:
            return

        try:
            self.fig.hold(True)
        except:
            pass

        # plot each set
        # print "--------------------plot the data"
        for data in self._data:
            ln = max(data.shape)
            lw = max(5.0-np.log10(ln), 1.0)
            if ln > 0:
                al = max(1.0-1.0/np.log2(ln), 0.75)
            else:
                al = 0

            if data.shape[-1] == 2:
                self.axes.plot(data[..., 0], data[..., 1], alpha=al, lw=lw)
            else:
                self.axes.plot(data, alpha=al, lw=lw)

        # X=0, Y=0
        if self.get_xline():
            self.axes.axhline(y=0, color='k', zorder=-1, label="y=0")
        if self.get_yline():
            self.axes.axvline(x=0, color='k', zorder=-1, label="x=0")

        # LEGEND
        if self.get_legend():
            handles, labels = self.axes.get_legend_handles_labels()
            self.axes.legend(handles, labels)

        # AUTOSCALE
        if self.get_autoscale():
            self.set_xlim(self.axes.get_xlim(), quiet=True)
            self.set_ylim(self.axes.get_ylim(), quiet=True)

        # X TICKS
        xl = self._x_ticks.text().split(',')
        if len(xl) > 1:
            self.axes.set_xticks(np.linspace(*self.axes.get_xlim(), num=len(xl)))
            self.axes.set_xticklabels(xl)
        else:
            self.axes.set_xticks(np.linspace(*self.axes.get_xlim(), num=self._x_numticks.get_val()))

        # Y TICKS
        yl = self._y_ticks.text().split(',')
        if len(yl) > 1:
            self.axes.set_yticks(np.linspace(*self.axes.get_ylim(), num=len(yl)))
            self.axes.set_yticklabels(yl)
        else:
            self.axes.set_yticks(np.linspace(*self.axes.get_ylim(), num=self._y_numticks.get_val()))

        self.applySubplotSettings()

        self.canvas.draw()

        #print 'draw count: ', self._on_draw_cnt
        self._on_draw_cnt = 0

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
            self.addInPort('in' + str(i), 'NPYarray', drange=(1,2), obligation=gpi.OPTIONAL)

    def compute(self):

        # check input ports for data
        in_lst = [self.getData('in' + str(i))
                  for i in self.inport_range if self.getData('in' + str(i)) is not None]

        self.setAttr('Plot', val=in_lst)

        return 0

    def execType(self):
        '''Could be GPI_THREAD, GPI_PROCESS, GPI_APPLOOP'''
        return gpi.GPI_APPLOOP
