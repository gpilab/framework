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


import os
import re
import math
import json

# gpi
import gpi
from gpi import QtCore, QtGui, QtWidgets, QWebView, QT_API_NAME
from .config import Config
from .defaultTypes import GPITYPE_PASS
from .defines import WidgetTYPE, GPI_FLOAT_MIN, GPI_FLOAT_MAX
from .defines import GPI_INT_MIN, GPI_INT_MAX, TranslateFileURI
from .defines import getKeyboardModifiers, printMouseEvent
from .logger import manager
from .sysspecs import Specs
from . import syntax

# TODO: optionally use the newer QtWebEngineWidgets.QWebEngineView in place of
#       the deprecated QWebView.


# start logger for this module
log = manager.getLogger(__name__)


# WIDGET ELEMENT
class BasicPushButton(QtWidgets.QWidget):
    valueChanged = gpi.Signal(bool)

    def __init__(self, parent=None):
        super(BasicPushButton, self).__init__(parent)

        button_title = ''
        self.wdg = QtWidgets.QPushButton(button_title, self)
        self.wdg.setCheckable(False)
        self.wdg.clicked[bool].connect(self.setButtonON)
        self.wdg.clicked[bool].connect(self.valueChanged)
        self.wdg.setMinimumWidth(50)

        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.wdg, 0, 0, 1, 3)
        wdgLayout.setContentsMargins(0, 0, 0, 0)  # no spaces around this item
        wdgLayout.setSpacing(0)
        self.setLayout(wdgLayout)

        self._value = False

    # setters
    def set_toggle(self, val):
        self.wdg.setCheckable(val)

    def set_button_title(self, title):
        self.wdg.setText(title)

    def set_val(self, value):
        if self.wdg.isCheckable():
            self.wdg.setChecked(value)
        self._value = bool(value)

    def set_reset(self):
        # don't reset if its a toggle
        if not self.wdg.isCheckable():
            self.set_val(False)

    # getters
    def get_toggle(self):
        return self.wdg.isCheckable()

    def get_button_title(self):
        return self.wdg.text()

    def get_val(self):
        return self._value
    # support

    def setButtonON(self):
        if self.wdg.isCheckable():
            self._value = self.wdg.isChecked()
        else:
            self._value = True

# WIDGET ELEMENT

class GPIDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, parent=None):
        super(GPIDoubleSpinBox, self).__init__(parent)

        # these variables have to be updated b/c the lineEdit().isModified()
        # and lineEdit.returnPressed() don't work as part of the spinbox.
        self._last_val = self.value()
        self._valChanged = False
        self._focusOutEvent = False

    def focusOutEvent(self, event):

        # keep track of this event as a focusOutEvent for downstream
        # differentiation.
        self._focusOutEvent = True

        # determine whether there was a change to the lineEdit
        if self._last_val == self.value():
            self._valChanged = False
        else:
            self._valChanged = True
            self._last_val = self.value()

        super(GPIDoubleSpinBox, self).focusOutEvent(event)

    def isFocusOutEvent(self):
        return self._focusOutEvent

    def valueDidChange(self):
        return self._valChanged

    def updateTrackedEvents(self):
        self._valChanged = False
        self._focusOutEvent = False
        self._last_val = self.value()

    def setValue(self, val):
        self._last_val = val
        super(GPIDoubleSpinBox, self).setValue(val)

class BasicDoubleSpinBox(QtWidgets.QWidget):
    valueChanged = gpi.Signal(float)

    def __init__(self, parent=None):
        super(BasicDoubleSpinBox, self).__init__(parent)

        self.spin_label = QtWidgets.QLabel()
        self.spin_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.spin_label.hide()
        self.curSpinBox = GPIDoubleSpinBox()
        self.curSpinBox.setSingleStep(1)
        self.curSpinBox.setKeyboardTracking(False)

        wdgLayout = QtWidgets.QHBoxLayout()
        wdgLayout.addWidget(self.spin_label)
        wdgLayout.addWidget(self.curSpinBox)
        wdgLayout.setContentsMargins(0, 0, 0, 0)  # no spaces around this item
        wdgLayout.setSpacing(0)
        wdgLayout.setStretch(0, 0)
        wdgLayout.setStretch(1, 0)
        self.setLayout(wdgLayout)

        # defaults
        self.set_val(0)
        self.set_max(GPI_FLOAT_MAX)
        self.set_min(GPI_FLOAT_MIN)

        self._immediate = False
        self.curSpinBox.editingFinished.connect(self.finishedEditing)
        self.curSpinBox.valueChanged.connect(self.finishedChanging)

    # setters
    def set_keyboardtracking(self, val):
        self.curSpinBox.setKeyboardTracking(val)

    def set_max(self, val):
        self.curSpinBox.setMaximum(val)

    def set_min(self, val):
        self.curSpinBox.setMinimum(val)

    def set_val(self, val):
        self.curSpinBox.setValue(val)

    def set_label(self, val):
        if val != '':
            self.spin_label.setText(val)
            self.spin_label.setVisible(True)
        else:
            self.spin_label.setVisible(False)

    def set_wrapping(self, val):
        self.curSpinBox.setWrapping(val)

    def set_decimals(self, val):
        self.curSpinBox.setDecimals(val)

    def set_singlestep(self, val):
        self.curSpinBox.setSingleStep(val)

    def set_immediate(self, val):
        self._immediate = val

    # getters
    def get_keyboardtracking(self):
        return self.curSpinBox.keyboardTracking()

    def get_max(self):
        return self.curSpinBox.maximum()

    def get_min(self):
        return self.curSpinBox.minimum()

    def get_val(self):
        return self.curSpinBox.value()

    def get_label(self):
        return self.spin_label.text()

    def get_wrapping(self):
        return self.curSpinBox.wrapping()

    def get_decimals(self):
        return self.curSpinBox.decimals()

    def get_singlestep(self):
        return self.curSpinBox.singleStep()

    def get_immediate(self):
        return self._immediate

    # support
    def finishedEditing(self):
        if not self._immediate:
            if self.curSpinBox.isFocusOutEvent():
                if self.curSpinBox.valueDidChange():
                    self.valueChanged.emit(self.get_val())

            else:  # assume return pressed
                self.valueChanged.emit(self.get_val())

            self.curSpinBox.updateTrackedEvents()

    def finishedChanging(self, val):
        if self._immediate:
            self.valueChanged.emit(val)


# WIDGET ELEMENT

class GPISpinBox(QtWidgets.QSpinBox):
    def __init__(self, parent=None):
        super(GPISpinBox, self).__init__(parent)

        # these variables have to be updated b/c the lineEdit().isModified()
        # and lineEdit.returnPressed() don't work as part of the spinbox.
        self._last_val = self.value()
        self._valChanged = False
        self._focusOutEvent = False

    def focusOutEvent(self, event):

        # keep track of this event as a focusOutEvent for downstream
        # differentiation.
        self._focusOutEvent = True

        # determine whether there was a change to the lineEdit
        if self._last_val == self.value():
            self._valChanged = False
        else:
            self._valChanged = True
            self._last_val = self.value()

        super(GPISpinBox, self).focusOutEvent(event)

    def isFocusOutEvent(self):
        return self._focusOutEvent

    def valueDidChange(self):
        return self._valChanged

    def updateTrackedEvents(self):
        self._valChanged = False
        self._focusOutEvent = False
        self._last_val = self.value()

    def setValue(self, val):
        self._last_val = val
        super(GPISpinBox, self).setValue(val)

class BasicSpinBox(QtWidgets.QWidget):
    valueChanged = gpi.Signal(int)

    def __init__(self, parent=None):
        super(BasicSpinBox, self).__init__(parent)

        self.spin_label = QtWidgets.QLabel()
        self.spin_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.spin_label.hide()
        self.curSpinBox = GPISpinBox()
        self.curSpinBox.setSingleStep(1)
        self.curSpinBox.setKeyboardTracking(False)

        wdgLayout = QtWidgets.QHBoxLayout()
        wdgLayout.addWidget(self.spin_label)
        wdgLayout.addWidget(self.curSpinBox)
        wdgLayout.setContentsMargins(0, 0, 0, 0)  # no spaces around this item
        wdgLayout.setSpacing(0)
        wdgLayout.setStretch(0, 0)
        wdgLayout.setStretch(1, 0)
        self.setLayout(wdgLayout)

        # defaults
        self.set_val(0)
        self.set_max(GPI_INT_MAX)
        self.set_min(GPI_INT_MIN)

        self._immediate = False
        self.curSpinBox.editingFinished.connect(self.finishedEditing)
        self.curSpinBox.valueChanged.connect(self.finishedChanging)

    # setters
    def set_max(self, val):
        self.curSpinBox.setMaximum(val)

    def set_min(self, val):
        self.curSpinBox.setMinimum(val)

    def set_val(self, val):
        self.curSpinBox.setValue(val)

    def set_label(self, val):
        if val != '':
            self.spin_label.setText(val)
            self.spin_label.setVisible(True)
        else:
            self.spin_label.setVisible(False)

    def set_wrapping(self, val):
        self.curSpinBox.setWrapping(val)

    def set_singlestep(self, val):
        self.curSpinBox.setSingleStep(val)

    def set_immediate(self, val):
        self._immediate = val

    # getters
    def get_max(self):
        return self.curSpinBox.maximum()

    def get_min(self):
        return self.curSpinBox.minimum()

    def get_val(self):
        return self.curSpinBox.value()

    def get_label(self):
        return self.spin_label.text()

    def get_wrapping(self):
        return self.curSpinBox.wrapping()

    def get_singlestep(self):
        return self.curSpinBox.singleStep()

    def get_immediate(self):
        return self._immediate

    # support
    def finishedEditing(self):
        if not self._immediate:
            if self.curSpinBox.isFocusOutEvent():
                if self.curSpinBox.valueDidChange():
                    self.valueChanged.emit(self.get_val())

            else:  # assume return pressed
                self.valueChanged.emit(self.get_val())

            self.curSpinBox.updateTrackedEvents()

    def finishedChanging(self, val):
        if self._immediate:
            self.valueChanged.emit(val)


# WIDGET ELEMENT

# https://stackoverflow.com/questions/67299834/pyqt-slider-not-come-to-a-specific-location-where-i-click-but-move-to-a-certain
class ProxyStyle(QtWidgets.QProxyStyle):
    def styleHint(self, hint, opt=None, widget=None, returnData=None):
        res = super().styleHint(hint, opt, widget, returnData)
        if hint == self.SH_Slider_AbsoluteSetButtons:
            res |= QtCore.Qt.LeftButton
        return res

class BasicSlider(QtWidgets.QWidget):
    valueChanged = gpi.Signal(int)

    def __init__(self, parent=None):
        super(BasicSlider, self).__init__(parent)
        # self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
        #       QtWidgets.QSizePolicy.Minimum)
        # slider
        self.sl = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.sl.setStyle(ProxyStyle())
        self.sl.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.sl.setTickInterval(10)
        self.sl.setSingleStep(1)
        self.sl.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.sl.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        # spinbox
        self.sp = QtWidgets.QSpinBox(self)
        self.sp.setSingleStep(1)
        self.sp.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.sp.setKeyboardTracking(False)
        # labels
        self.smin = QtWidgets.QLabel(self)
        self.smax = QtWidgets.QLabel(self)
        self.smin.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.smax.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.smin.setAlignment(QtCore.Qt.AlignCenter)
        self.smax.setAlignment(QtCore.Qt.AlignCenter)
        # cross the signals and set output signal
        self.sl.valueChanged.connect(self.sp.setValue)
        self.sp.valueChanged.connect(self.sl.setValue)
        self.sl.valueChanged.connect(self.valueChanged)
        hbox = QtWidgets.QHBoxLayout(self)
        hbox.addWidget(self.smin)
        hbox.addWidget(self.sl)
        hbox.addWidget(self.smax)
        hbox.addWidget(self.sp)
        hbox.setContentsMargins(0, 0, 0, 0)  # we don't need margins here
        hbox.setSpacing(5)  # horizontal between elems
        self.setLayout(hbox)
        # defaults
        self.set_val(0)
        self.set_max(100)
        self.set_min(0)
    # setters

    def set_val(self, value):
        self.sl.setValue(value)

    def set_min(self, value):
        self.sl.setMinimum(value)
        self.sp.setMinimum(value)
        self.smin.setText(str(value))

    def set_max(self, value):
        self.sl.setMaximum(value)
        self.sp.setMaximum(value)
        self.smax.setText(str(value))
    # getters

    def get_max(self):
        return self.sl.maximum()

    def get_min(self):
        return self.sl.minimum()

    def get_val(self):
        return self.sl.value()

# WIDGET ELEMENT


class BasicCWFCSliders(QtWidgets.QWidget):
    # Center, Width, Floor, Ceiling
    valueChanged = gpi.Signal()

    def __init__(self, parent=None):
        super(BasicCWFCSliders, self).__init__(parent)
        # sliders
        self.scenter = BasicSlider()
        self.swidth = BasicSlider()
        self.sfloor = BasicSlider()
        self.sceil = BasicSlider()
        # support functions
        self.scenter.valueChanged.connect(self.centerChanged)
        self.swidth.valueChanged.connect(self.widthChanged)
        self.sfloor.valueChanged.connect(self.floorChanged)
        self.sceil.valueChanged.connect(self.ceilChanged)

        # layout
        wdgLayout = QtWidgets.QVBoxLayout()
        wdgLayout.addWidget(self.scenter)
        wdgLayout.addWidget(self.swidth)
        wdgLayout.addWidget(self.sfloor)
        wdgLayout.addWidget(self.sceil)
        wdgLayout.setSpacing(0)
        wdgLayout.setContentsMargins(0, 3, 0, 0)  # top margin
        self.setLayout(wdgLayout)
        self._min_width = 0
    # support

    def checkCWbounds(self, c, w):
        ci = c
        wi = w
        w2 = w//2
        mx = self.scenter.get_max()
        mn = self.scenter.get_min()
        ct = (c+w2-(not w % 2))
        if ct > mx:
            c = mx-w2+(not w % 2)
        if c-w2 < mn:
            c = mn+w2
        return c, w, ci == c, wi == w

    def checkFCbounds(self, f, c, fchanged):
        fi = f
        ci = c
        if fchanged:
            c = max(f, c)
            f = min(f, c)
        else:
            f = min(f, c)
            c = max(f, c)
        return f, c, fi == f, ci == c

    def centerChanged(self, c):
        self.blockSliderSignals(True)
        w = self.swidth.get_val()
        c, w, cc, wc = self.checkCWbounds(c, w)
        self.scenter.set_val(c)
        if cc or wc:
            self.swidth.set_val(w)
            self.cwChanged(c, w)
        self.blockSliderSignals(False)
        self.valueChanged.emit()

    def widthChanged(self, w):
        self.blockSliderSignals(True)
        c = self.scenter.get_val()
        c, w, cc, wc = self.checkCWbounds(c, w)
        # if w < self._min_width:
        if cc or wc:
            self.scenter.set_val(c)
            self.cwChanged(c, w)
        self.blockSliderSignals(False)
        self.valueChanged.emit()

    def floorChanged(self, f):
        self.blockSliderSignals(True)
        c = self.sceil.get_val()
        f, c, fc, cc = self.checkFCbounds(f, c, True)
        if fc or cc:
            self.sceil.set_val(c)
            self.fcChanged(f, c)
        self.blockSliderSignals(False)
        self.valueChanged.emit()

    def ceilChanged(self, c):
        self.blockSliderSignals(True)
        f = self.sfloor.get_val()
        f, c, fc, cc = self.checkFCbounds(f, c, False)
        if fc or cc:
            self.sfloor.set_val(f)
            self.fcChanged(f, c)
        self.blockSliderSignals(False)
        self.valueChanged.emit()

    def cwChanged(self, c, w):
        self.sfloor.set_val(c-w//2)
        self.sceil.set_val(c+w//2-(not w % 2))

    def fcChanged(self, f, c):
        self.scenter.set_val((c-f)//2+f)
        self.swidth.set_val(c-f+1)

    def blockSliderSignals(self, val):
        self.scenter.blockSignals(val)
        self.swidth.blockSignals(val)
        self.sfloor.blockSignals(val)
        self.sceil.blockSignals(val)

    # setters
    def set_min_width(self, val):
        self._min_width = val

    def set_center(self, val):
        self.scenter.set_val(val)

    def set_width(self, val):
        self.swidth.set_val(val)

    def set_floor(self, val):
        self.sfloor.set_val(val)

    def set_ceiling(self, val):
        self.sceil.set_val(val)

    def set_min(self, val):
        self.scenter.set_min(val)
        self.swidth.set_min(val)
        self.sfloor.set_min(val)
        self.sceil.set_min(val)

    def set_max(self, val):
        self.scenter.set_max(val)
        self.swidth.set_max(val)
        self.sfloor.set_max(val)
        self.sceil.set_max(val)

    def set_cwvisible(self, val):
        self.scenter.setVisible(val)
        self.swidth.setVisible(val)
        self.sfloor.setVisible(not val)
        self.sceil.setVisible(not val)

    def set_fcvisible(self, val):
        self.scenter.setVisible(not val)
        self.swidth.setVisible(not val)
        self.sfloor.setVisible(val)
        self.sceil.setVisible(val)

    def set_slicevisible(self, val):
        self.scenter.setVisible(val)
        self.sfloor.setVisible(not val)
        self.sceil.setVisible(not val)
        self.swidth.setVisible(not val)

    def set_allvisible(self, val):
        self.scenter.setVisible(val)
        self.sfloor.setVisible(val)
        self.sceil.setVisible(val)
        self.swidth.setVisible(val)

    # getters
    def get_min_width(self):
        return self._min_width

    def get_center(self):
        return self.scenter.get_val()

    def get_width(self):
        return self.swidth.get_val()

    def get_floor(self):
        return self.sfloor.get_val()

    def get_ceiling(self):
        return self.sceil.get_val()

    def get_min(self):
        return self.scenter.get_min()

    def get_max(self):
        return self.scenter.get_max()

# WIDGET ELEMENT

class GPIFileDialog(QtWidgets.QFileDialog):
    def __init__(self, parent=None, cur_fname='', **kwargs):
        super(GPIFileDialog, self).__init__(parent, **kwargs)

        self._cur_fname = cur_fname

        # if there is an existing filename, then populate the line
        if cur_fname != '':
            self.selectFile(os.path.basename(cur_fname))
        else:
            self.selectFile('Untitled')

        # set the mount or media directories for easy use
        pos_uri = self._listMediaDirs() # needs to be done each time for changing media
        cur_sidebar = self.sidebarUrls()
        for uri in pos_uri:
            if QtCore.QUrl(uri) not in cur_sidebar:
                cur_sidebar.append(QtCore.QUrl(uri))

        # since the sidebar is remembered, we have to remove non-existing paths
        cur_sidebar = [uri for uri in cur_sidebar if os.path.isdir(uri.path())]
        self.setSidebarUrls(cur_sidebar)

        self.setOption(QtWidgets.QFileDialog.DontUseNativeDialog)

    def selectedFilteredFiles(self):
        # enforce the selected filter in the captured filename
        fnames = self.selectedFiles()

        if len(fnames) == 0:
            # no files were selected
            return []

        fnames_flt = [] # output
        for fname in fnames:
            # the default filter is 'All Files (*)'
            fnames_flt.append(self.applyFilterToPath(fname))

        return fnames_flt

    def _listMediaDirs(self):
        if Specs.inOSX():
            rdir = '/Volumes'
            if os.path.isdir(rdir):
                return ['file://'+rdir+'/'+p for p in os.listdir(rdir)]
        elif Specs.inLinux():
            rdir = '/media'
            if os.path.isdir(rdir):
                return ['file://'+rdir+'/'+p for p in os.listdir(rdir)]
            rdir = '/mnt'
            if os.path.isdir(rdir):
                return ['file://'+rdir+'/'+p for p in os.listdir(rdir)]
        return []

    def applyFilterToPath(self, fname):
        # Given a QFileDialog filter string, make sure the given path adheres
        # to the filter and return the filtered path string.
        flt = str(self.selectedNameFilter())

        # Enforce the selected filter in the captured filename
        # filters are strings with content of the type:
        #   'Images (*.png *.xpm *.jpg);;Text files (*.txt);;XML files (*.xml)'
        par = ''.join(re.findall('\([^()]*\)', str(flt))) # just take whats in parens
        suf = ' '.join(re.split('[()]', par)) # split out parens
        suf = suf.split() # split on whitespace
        suf = [os.path.splitext(s)[-1] for s in suf] # remove asterisks

        # check for a valid suffix
        basename, ext = os.path.splitext(fname)
        if ext in suf:
            return fname

        # take the first suffix if the filename doesn't match any in the list
        # append to fname (as opposed to basename) to allow the user to include
        # dots in the filename.
        return fname+suf[0]

    def runSaveFileDialog(self):
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        self.setFileMode(QtWidgets.QFileDialog.AnyFile)
        self.setOption(QtWidgets.QFileDialog.DontConfirmOverwrite, False)
        self.exec_()
        return self.result()

    def runOpenFileDialog(self):
        self.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        self.setFileMode(QtWidgets.QFileDialog.ExistingFile)

        if self._cur_fname != '':
            if os.path.isfile(self._cur_fname):
                self.selectFile(os.path.basename(self._cur_fname))

        self.exec_()
        return self.result()

# PARTIAL WIDGET


class HidableGroupBox(QtWidgets.QGroupBox):
    collapseChanged = gpi.Signal()
    def __init__(self, title, parent=None):
        super(HidableGroupBox, self).__init__(title, parent)
        self._isCollapsed = False

    def set_collapsed(self, col=True):
        self._isCollapsed = col
        self.collapseChanged.emit()
        for wdg in self.children():
            if hasattr(wdg, 'setVisible'):
                wdg.setVisible(not col)

    def mouseDoubleClickEvent(self, event):
        event.accept()
        if self._isCollapsed:
            self.set_collapsed(False)
        else:
            self.set_collapsed(True)


# WIDGET GROUP BOX


class GenericWidgetGroup(QtWidgets.QGroupBox):
    """This is the base-class for all widgets.  It provides abstract methods
    and default behavior.  From the node-developer's perspective, this
    provides the widget-port, visibility, and collapsibility options.
    """
    GPIWdgType = WidgetTYPE  # ensures the subclass is of THIS class
    portStateChange = gpi.Signal()
    returnWidgetToOrigin = gpi.Signal(str)
    widgetMoved = gpi.Signal(str)

    def __init__(self, title, parent=None):
        super(GenericWidgetGroup, self).__init__(title, parent)
        # self.setFlat(True)
        self._id = None
        self.set_id()
        self.inPort_ON = False
        self.outPort_ON = False
        self._isVisible = True
        self._isCollapsed = False
        self._title = title

        self._nodename = ''
        self._nodelabel = ''

    # setters #
    # used in modifyWidget_setter()

    def set_quietval(self, val):
        """(same type as val) | Set the central value of a widget without triggering an event."""
        # block val changes from copy/paste/net that have called get_quietval().
        if val is not None:
            self.blockSignals(True)
            self.set_val(val)
            self.blockSignals(False)

    def set_val(self, val):
        """type(val) | Set the central value of a widget."""
        pass

    def set_reset(self):
        """No Arg | Widgets that need to be reset automatically
        implement this function (e.g. pushbuttons
        where the button needs to be raised again
        after the node compute())."""
        pass

    def set_inport(self, st):
        """bool | Turn the widget inport on/off with a bool."""
        self.inPort_ON = st

    def set_outport(self, st):
        """bool | Turn the widget outport on/off with a bool."""
        self.outPort_ON = st

    def set_visible(self, visible=True):
        """bool | Set the widget groupbox's visibility within
        the node menu."""
        self._isVisible = visible
        self.setVisible(visible)

    def set_collapsed(self, col=True):
        """bool | Only hide the 'collapsable' elements of a
        widget within its groupbox.
        """
        self._isCollapsed = col
        for wdg in self.children():
            if hasattr(wdg, 'setVisible'):
                wdg.setVisible(not col)

    def set_id(self, value=None):
        """int | INTERNAL USE ONLY: used for saving network
        information that will aid in reinstantiation.
        """
        if value is None:
            self._id = id(self)  # this will always be unique
        else:
            self._id = value

    # getters #

    def get_id(self):
        return self._id

    def get_quietval(self):
        '''Don't use/implement quietval since networks will use it to modify val.
        '''
        return None

    def get_val(self):
        return None

    def get_collapsed(self):
        return self._isCollapsed

    def get_visible(self):
        return self._isVisible

    def get_inport(self):
        return self.inPort_ON

    def get_outport(self):
        return self.outPort_ON

    # support #

    def setNodeName(self, nodename):
        self._nodename = str(nodename)

    def _setNodeLabel(self, newlabel=''):
        self._nodelabel = str(newlabel)
        self.setDispTitle()

    def setDispTitle(self):
        # if its the node menu then reset title
        if hasattr(self.parent(), 'GPIExtNodeType'):
            self.setTitle(self._title)
        else:
            if self._nodelabel == '':
                augtitle = self._nodename+"."+self._title
            else:
                augtitle = self._nodename+"."+self._title+": "+self._nodelabel
            self.setTitle(augtitle)

    def getTitle(self):
        return self._title

    def getType(self):
        return str(type(self))

    def defaultValue(self):
        return None

    def setValueQuietly(self, value):
        self.blockSignals(True)  # prevent double events
        self.set_val(value)
        self.blockSignals(False)

    # Translate the type(val) to a python_GPITYPE. If no
    # translatable type exists, then set to PASS which
    # will be the GPIDefaultType().
    # NOTE: This won't work for widgets that don't start
    #       with an initialized get_val().
    #           -It will have to be implemented
    #            specifically by the widget.
    # TODO: This list should be populated by the list of
    # known types from the library
    def getDataType(self):
        t = type(self.get_val())
        if t == int:
            return 'INT'
        if t == float:
            return 'FLOAT'
        if t == str:
            return 'STRING'
        if t == int:
            return 'LONG'
        if t == list:
            return 'LIST'
        if t == tuple:
            return 'TUPLE'
        if t == dict:
            return 'DICT'
        if t == complex:
            return 'COMPLEX'
        return GPITYPE_PASS

    def getSettings(self):  # WIDGET SETTINGS
        '''These are the minimum settings required to re-instantiate each
        widget.  Save all 'get_<name>' attributes as '<name>'.  This list is
        also used in the GPI_PROCESS to buffer widget attributes.
        '''
        s = {}
        s['name'] = self.getTitle()
        s['type'] = self.getType()
        kwargs = {}  # args for modifyWidget_direct()

        # save every attribute that starts with 'get_'
        for func_name in dir(self):
            if func_name.startswith('get_'):
                attr = func_name[4:]
                if attr != 'val':
                    func = getattr(self, func_name)
                    kwargs[attr] = func()

        # do 'val' separately since it might fail
        try:  # this fails if the object is not picklable
            # pickle.dumps(self.get_val())
            json.dumps(self.get_val())
            kwargs['val'] = self.get_val()
        except:
            kwargs['val'] = self.defaultValue()
        s['kwargs'] = kwargs  # possibly deepcopy here
        # print s
        return s

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            event.accept()
            if self._isCollapsed:
                self.set_collapsed(False)
            else:
                self.set_collapsed(True)
        else:
            super(GenericWidgetGroup, self).mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):  # WIDGET
        printMouseEvent(self, event)
        modifiers = getKeyboardModifiers()

        modmidbutton_event = (event.button() == QtCore.Qt.LeftButton
                              and modifiers == QtCore.Qt.AltModifier)
        if event.button() == QtCore.Qt.RightButton:
            event.accept()
            self.rightButtonMenu(event)

        # middle button for Linux, modleftbutton for OSX
        elif event.button() == QtCore.Qt.MidButton or modmidbutton_event:
            log.debug("mod mouse event")
            event.accept()

            # from fridgemagnets example
            id_str = str(id(self))
            id_str_bytes = bytes(id_str, 'ascii')

            itemData = QtCore.QByteArray()
            dataStream = QtCore.QDataStream(
                itemData, QtCore.QIODevice.WriteOnly)
            dataStream << QtCore.QByteArray(id_str_bytes) << QtCore.QPoint(
                event.pos() - self.rect().topLeft())

            mimeData = QtCore.QMimeData()
            mimeData.setData('application/gpi-widget', itemData)
            mimeData.setText(id_str)

            drag = QtGui.QDrag(self)
            drag.setMimeData(mimeData)
            drag.setHotSpot(event.pos() - self.rect().topLeft())
            if QT_API_NAME == 'PyQt5':
                wdgpixmap = self.grab()
            else:
                wdgpixmap = QtGui.QPixmap().grabWidget(self)
            drag.setPixmap(wdgpixmap)

            self.hide()

            # Start the drag:
            # all results cause the widget to move
            #   MoveAction:
            #       1) the widget moved within a layout
            #       2) the widget moved to another layout
            #   else:
            #       1) the widget move was invalid so it is returned to origin
            self.parent().widgetMovingEvent(id(self))
            dragact = drag.exec_(QtCore.Qt.IgnoreAction | QtCore.Qt.MoveAction,
                          QtCore.Qt.IgnoreAction)

            if dragact == QtCore.Qt.MoveAction:
                self.show()
            else:
                # anything but move will be interpreted as a replacement of the
                # widget to its origin node menu.
                self.returnWidgetToOrigin.emit(str(id(self)))

            # parent changed
            #print "Wdg: my parent is: "+str(self.parent())
            self.setDispTitle()

        else:
            super(GenericWidgetGroup, self).mousePressEvent(event)

    def returnToOrigin(self):
        self.returnWidgetToOrigin.emit(str(id(self)))

    def rightButtonMenu(self, event):
        menu = QtWidgets.QMenu(self)
        addInPort = menu.addAction("add In Port")
        addInPort.setCheckable(True)
        if self.inPort_ON:
            addInPort.setChecked(True)
        else:
            addInPort.setChecked(False)
        addOutPort = menu.addAction("add Out Port")
        addOutPort.setCheckable(True)
        if self.outPort_ON:
            addOutPort.setChecked(True)
        else:
            addOutPort.setChecked(False)
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == addInPort:
            if self.inPort_ON:
                self.inPort_ON = False
            else:
                self.inPort_ON = True
            self.portStateChange.emit()
        if action == addOutPort:
            if self.outPort_ON:
                self.outPort_ON = False
            else:
                self.outPort_ON = True
            self.portStateChange.emit()

# WIDGET


class SaveFileBrowser(GenericWidgetGroup):
    """Provide a QFileDialog() at the push of a button.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super(SaveFileBrowser, self).__init__(title, parent)

        button_title = ''
        self.pb = QtWidgets.QPushButton(button_title, self)
        self.pb.setMinimumWidth(50)
        self.pb.setCheckable(False)
        self.pb.clicked.connect(self.launchBrowser)

        self.le = QtWidgets.QLineEdit()
        self.le.returnPressed.connect(self.textChanged)

        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.pb, 0, 0, 1, 1)
        wdgLayout.addWidget(self.le, 0, 1, 1, 2)
        wdgLayout.setColumnStretch(1, 1)
        self.setLayout(wdgLayout)

        self._value = ''
        self._filter = None
        self._caption = None
        self._directory = Config.GPI_DATA_PATH # start in usr chosen data dir
        self._last = ''

    # setters
    def set_filter(self, val):
        """str | Set the file extension filter (e.g. \'io_field (*.fld);;all (*)\').
        """
        self._filter = val

    def set_directory(self, val):
        """str | Set the default directory (str)."""
        if type(val) is str:
            if Config.GPI_FOLLOW_CWD:
                self._directory = TranslateFileURI(val)

    def set_caption(self, val):
        """str | Set browser title-bar (str)."""
        self._caption = val

    def set_button_title(self, title):
        """str | A title centered on the pushbutton (str)."""
        self.pb.setText(title)

    def set_val(self, value):
        """str | The filename and path (str)."""
        self.le.setText(value)
        self._value = value
        self._last = value
        if Config.GPI_FOLLOW_CWD:
            self._directory = os.path.dirname(value)

    # getters
    def get_val(self):
        return self._value

    def get_directory(self):
        return self._directory

    # support
    def textChanged(self):
        # if its been changed by the label widget
        val = TranslateFileURI(str(self.le.text()))

        if self._filter is not None:
            val = GPIFileDialog(filter=self._filter).applyFilterToPath(val)

        if val != self._last:
            self.set_val(val)
            self.valueChanged.emit()

    def launchBrowser(self):
        kwargs = {}
        kwargs['cur_fname'] = self.get_val()
        if self._filter:
            kwargs['filter'] = self._filter
        if self._caption:
            kwargs['caption'] = self._caption
        if self._directory:
            kwargs['directory'] = self._directory

        # create dialog box
        dia = GPIFileDialog(self, **kwargs)

        # don't run if cancelled
        if dia.runSaveFileDialog():

            # save the current directory for next browse
            if Config.GPI_FOLLOW_CWD:
                self._directory = str(dia.directory().path())

            # enforce the selected filter in the captured filename
            fname = dia.selectedFilteredFiles()[0]

            # allow browser to overwrite file if the same one is chosen
            # this way the user has to approve an overwrite
            self.set_val(fname)
            self.valueChanged.emit()

# WIDGET


class OpenFileBrowser(GenericWidgetGroup):
    """Provide a QFileDialog() at the push of a button.
    """
    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super(OpenFileBrowser, self).__init__(title, parent)

        button_title = ''
        self.pb = QtWidgets.QPushButton(button_title, self)
        self.pb.setMinimumWidth(50)
        self.pb.setCheckable(False)
        self.pb.clicked.connect(self.launchBrowser)

        self.le = QtWidgets.QLineEdit()
        self.le.returnPressed.connect(self.textChanged)

        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.pb, 0, 0, 1, 1)
        wdgLayout.addWidget(self.le, 0, 1, 1, 2)
        wdgLayout.setColumnStretch(1, 1)
        self.setLayout(wdgLayout)

        self._value = ''
        self._filter = None
        self._caption = None
        self._directory = Config.GPI_DATA_PATH # start in usr chosen data dir
        self._last = ''

    # setters
    def set_filter(self, val):
        """str | Set the file extension filter (e.g. \'io_field (*.fld);;all (*)\').
        """
        self._filter = val

    def set_directory(self, val):
        """str | Set the default directory (str)."""
        if type(val) is str:
            if Config.GPI_FOLLOW_CWD:
                self._directory = TranslateFileURI(val)

    def set_caption(self, val):
        """str | Set browser title-bar (str)."""
        self._caption = val

    def set_button_title(self, title):
        """str | A title centered on the pushbutton (str)."""
        self.pb.setText(title)

    def set_val(self, value):
        """str | The filename and path (str)."""
        self.le.setText(value)
        self._value = value
        self._last = value
        if Config.GPI_FOLLOW_CWD:
            self._directory = os.path.dirname(value)

    # getters
    def get_val(self):
        return self._value

    def get_directory(self):
        return self._directory

    # support
    def textChanged(self):
        val = TranslateFileURI(str(self.le.text()))
        if val != self._last:
            self.set_val(val)
            self.valueChanged.emit()

    def launchBrowser(self):
        kwargs = {}
        kwargs['cur_fname'] = self.get_val()
        if self._filter:
            kwargs['filter'] = self._filter
        if self._caption:
            kwargs['caption'] = self._caption
        if self._directory:
            kwargs['directory'] = self._directory

        # create dialog box
        dia = GPIFileDialog(self, **kwargs)

        # don't run if cancelled
        if dia.runOpenFileDialog():

            # save the current directory for next browse
            if Config.GPI_FOLLOW_CWD:
                self._directory = str(dia.directory().path())

            fname = str(dia.selectedFiles()[0])

            # allow the browser to re-open a file
            self.set_val(fname)
            self.valueChanged.emit()

# WIDGET


class TextEdit(GenericWidgetGroup):
    """Provides an editable text window with
    scrollbar and python code syntax highlighting.
    """

    valueChanged = gpi.Signal(int)

    def __init__(self, title, parent=None):
        super(TextEdit, self).__init__(title, parent)

        self.wdg = QtWidgets.QTextEdit()
        self.wdg.setTabStopWidth(16)
        # self.wdg.setTextBackgroundColor(QtGui.QColor(QtCore.Qt.black))
        # should check if the editor is going to be used on python code
        self.highlighter = syntax.PythonHighlighter(self.wdg.document())
        # self.wdg.setPlainText(val)
        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.wdg, 0, 0, 5, 3)
        wdgLayout.setRowStretch(0, 2)
        self.setLayout(wdgLayout)

    # setters
    def set_val(self, value):
        """str | The full plain-text to be displayed (str)."""
        self.wdg.setPlainText(value)

    # getters
    def get_val(self):
        return str(self.wdg.toPlainText())

# WIDGET


class TextBox(GenericWidgetGroup):
    """Provides a multi-line plain-text display."""

    valueChanged = gpi.Signal(int)

    def __init__(self, title, parent=None):
        super(TextBox, self).__init__(title, parent)

        self.wdg = QtWidgets.QLabel()
        self.wdg.setText('')

        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.wdg, 0, 0, 1, 3)
        wdgLayout.setRowStretch(0, 2)
        self.setLayout(wdgLayout)

    # setters
    def set_val(self, val):
        """str | The full plain-text to be displayed (str)."""
        self.wdg.setText(val)

    def set_wordwrap(self, val):
        """bool | Turn on/off with boolean True/False."""
        self.wdg.setWordWrap(val)

    def set_openExternalLinks(self, val):
        """bool | Open hyperrefs"""
        self.wdg.setOpenExternalLinks(val)

    # getters
    def get_val(self):
        return str(self.wdg.text())

    def get_wordwrap(self):
        return self.wdg.wordWrap()

    def get_openExternalLinks(self):
        return self.wdg.openExternalLinks()



# WIDGET

class GPILabel(QtWidgets.QLabel):
    '''For use with the DisplayBox widget
    '''
    annotationChanged = gpi.Signal()

    def __init__(self, wdgGroup, parent=None):
        super(GPILabel, self).__init__(parent=parent)
        self._wg = wdgGroup

        self._line_p1 = None
        self._line_p2 = None

    def paintEvent(self, event):
        super(GPILabel, self).paintEvent(event)

        if self._wg.isPointer():
            self.drawPoint(event)
        elif self._wg.isLine():
            self.drawLine(event)
        elif self._wg.isRectangle():
            self.drawRectangle(event)
        elif self._wg.isEllipse():
            self.drawEllipse(event)

    def drawPoint(self, event):
        if self._line_p1:

            s = self._wg._scaleFact

            x = ("%.0f" % (self._line_p1.x()/s))
            y = ("%.0f" % (self._line_p1.y()/s))
            buf_p1 = "("+x+","+y+")"

            p = QtGui.QPainter()
            p.begin(self)

            font = p.font()
            font.setPointSize(14)
            p.setFont(font)
            fm = QtGui.QFontMetricsF(font)
            bw_p1 = fm.width(buf_p1)
            bh = fm.height()

            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtCore.Qt.green)
            p.drawPoint(self._line_p1)

            # buf p1
            adj_x = 2
            if self._line_p1.x() > self._wg.imageLabel.size().width()//2:
                adj_x = -bw_p1 -2

            adj_y = -2
            if self._line_p1.y() < self._wg.imageLabel.size().height()//2:
                adj_y = bh +2

            p.drawText(self._line_p1 + QtCore.QPoint(adj_x, adj_y), buf_p1)

            p.end()

    def drawLine(self, event):

        if self._line_p1 and self._line_p2:

            s = self._wg._scaleFact

            diff = self._line_p1 - self._line_p2
            dist = math.sqrt(diff.x() * diff.x() + diff.y() * diff.y())
            dist /= s

            p = QtGui.QPainter()
            p.begin(self)

            x = ("%.0f" % (self._line_p1.x()/s))
            y = ("%.0f" % (self._line_p1.y()/s))
            buf_p1 = "("+x+","+y+")"

            buf_p2 = "l = "+ ("%.1f" % dist)
            x = ("%.0f" % (self._line_p2.x()/s))
            y = ("%.0f" % (self._line_p2.y()/s))
            buf_p2 += " ("+x+","+y+")"

            font = p.font()
            font.setPointSize(14)
            p.setFont(font)
            fm = QtGui.QFontMetricsF(font)
            bw_p1 = fm.width(buf_p1)
            bw_p2 = fm.width(buf_p2)
            bh = fm.height()

            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtCore.Qt.green)
            p.drawLine(self._line_p1, self._line_p2)

            # buf p1
            adj_x = 2
            if self._line_p1.x() > self._wg.imageLabel.size().width()//2:
                adj_x = -bw_p1 -2

            adj_y = -2
            if self._line_p1.y() < self._wg.imageLabel.size().height()//2:
                adj_y = bh +2

            p.drawText(self._line_p1 + QtCore.QPoint(adj_x, adj_y), buf_p1)

            # buf p2
            adj_x = 2
            if self._line_p2.x() > self._wg.imageLabel.size().width()//2:
                adj_x = -bw_p2 -2

            adj_y = -2
            if self._line_p2.y() < self._wg.imageLabel.size().height()//2:
                adj_y = bh +2

            p.drawText(self._line_p2 + QtCore.QPoint(adj_x, adj_y), buf_p2)

            p.end()

    def drawRectangle(self, event):

        if self._line_p1 and self._line_p2:

            s = self._wg._scaleFact

            diff = self._line_p1 - self._line_p2
            dist = math.sqrt(diff.x() * diff.x() + diff.y() * diff.y())
            dist /= s

            p = QtGui.QPainter()
            p.begin(self)

            x = ("%.0f" % (self._line_p1.x()/s))
            y = ("%.0f" % (self._line_p1.y()/s))
            buf_p1 = "("+x+","+y+")"

            buf_p2 = "A = "+ ("%.1f" % math.fabs(diff.x()*diff.y()))
            x = ("%.0f" % (self._line_p2.x()/s))
            y = ("%.0f" % (self._line_p2.y()/s))
            buf_p2 += " ("+x+","+y+")"

            font = p.font()
            font.setPointSize(14)
            p.setFont(font)
            fm = QtGui.QFontMetricsF(font)
            bw_p1 = fm.width(buf_p1)
            bw_p2 = fm.width(buf_p2)
            bh = fm.height()

            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtCore.Qt.green)
            p.drawRect(QtCore.QRectF(self._line_p1, self._line_p2))

            # buf p1
            adj_x = 2
            if self._line_p1.x() > self._wg.imageLabel.size().width()//2:
                adj_x = -bw_p1 -2

            adj_y = -2
            if self._line_p1.y() < self._wg.imageLabel.size().height()//2:
                adj_y = bh +2

            p.drawText(self._line_p1 + QtCore.QPoint(adj_x, adj_y), buf_p1)

            # buf p2
            adj_x = 2
            if self._line_p2.x() > self._wg.imageLabel.size().width()//2:
                adj_x = -bw_p2 -2

            adj_y = -2
            if self._line_p2.y() < self._wg.imageLabel.size().height()//2:
                adj_y = bh +2

            p.drawText(self._line_p2 + QtCore.QPoint(adj_x, adj_y), buf_p2)

            p.end()

    def drawEllipse(self, event):

        if self._line_p1 and self._line_p2:

            s = self._wg._scaleFact

            diff = self._line_p1 - self._line_p2
            dist = math.sqrt(diff.x() * diff.x() + diff.y() * diff.y())
            dist /= s

            p = QtGui.QPainter()
            p.begin(self)

            x = ("%.0f" % (self._line_p1.x()/s))
            y = ("%.0f" % (self._line_p1.y()/s))
            buf_p1 = "("+x+","+y+")"

            buf_p2 = "A = "+ ("%.1f" % math.fabs(math.pi*diff.x()*diff.y()/4.0))
            x = ("%.0f" % (self._line_p2.x()/s))
            y = ("%.0f" % (self._line_p2.y()/s))
            buf_p2 += " ("+x+","+y+")"

            font = p.font()
            font.setPointSize(14)
            p.setFont(font)
            fm = QtGui.QFontMetricsF(font)
            bw_p1 = fm.width(buf_p1)
            bw_p2 = fm.width(buf_p2)
            bh = fm.height()

            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtCore.Qt.green)
            p.drawEllipse(QtCore.QRectF(self._line_p1, self._line_p2))

            # buf p1
            adj_x = 2
            if self._line_p1.x() > self._wg.imageLabel.size().width()//2:
                adj_x = -bw_p1 -2

            adj_y = -2
            if self._line_p1.y() < self._wg.imageLabel.size().height()//2:
                adj_y = bh +2

            p.drawText(self._line_p1 + QtCore.QPoint(adj_x, adj_y), buf_p1)

            # buf p2
            adj_x = 2
            if self._line_p2.x() > self._wg.imageLabel.size().width()//2:
                adj_x = -bw_p2 -2

            adj_y = -2
            if self._line_p2.y() < self._wg.imageLabel.size().height()//2:
                adj_y = bh +2

            p.drawText(self._line_p2 + QtCore.QPoint(adj_x, adj_y), buf_p2)

            p.end()

    def mousePressEvent(self, event):
        super(GPILabel, self).mousePressEvent(event)
        self._line_p1 = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        super(GPILabel, self).mouseMoveEvent(event)
        if self._wg.isPointer():
            self._line_p1 = event.pos()
        else:
            self._line_p2 = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        super(GPILabel, self).mouseReleaseEvent(event)
        self._line_p2 = event.pos()

        if not self._wg.isPointer():
            if self._line_p1 == self._line_p2:
                self._line_p1 = None
                self._line_p2 = None

        self.update()
        self.annotationChanged.emit()

    def getPoints(self):
        '''return drawn line coords if present'''
        if self._line_p1 and self._line_p2:
            s = self._wg._scaleFact
            return ((self._line_p1.x()/s, self._line_p1.y()/s), (self._line_p2.x()/s, self._line_p2.y()/s))

    def getLine(self):
        '''return drawn line coords if present'''
        if self._line_p1 and self._line_p2:
            s = self._wg._scaleFact
            return ((self._line_p1.x()/s, self._line_p1.y()/s), (self._line_p2.x()/s, self._line_p2.y()/s))

    def getPoint(self):
        if self._line_p1:
            s = self._wg._scaleFact
            return (self._line_p1.x()/s, self._line_p1.y()/s)




class DisplayBox(GenericWidgetGroup):
    """A 2D QPixmap using a QLabel using built-in interpolation schemes.
    """

    valueChanged = gpi.Signal(int)

    def __init__(self, title, parent=None):
        super(DisplayBox, self).__init__(title, parent)

        self.collapsables = []
        self.imageLabel = GPILabel(self)
        self.imageLabel.annotationChanged.connect(self.somethingChanged)
        self.imageLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.imageLabel.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.imageLabel.setScaledContents(True)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setBackgroundRole(QtGui.QPalette.Dark)
        self.scrollArea.setWidget(self.imageLabel)
        self.scrollArea.setWidgetResizable(False)

        self.factSpinBox = BasicDoubleSpinBox()
        self.factSpinBox.set_label('Scale Factor:')
        self.factSpinBox.set_min(0.001)
        self.factSpinBox.set_max(100)
        self.factSpinBox.set_singlestep(0.1)
        self.factSpinBox.set_val(1.0)
        self.factSpinBox.set_decimals(3)
        self.factSpinBox.set_immediate(True)
        self.factSpinBox.set_keyboardtracking(False)

        self.factSpinBox.valueChanged.connect(self.setImageScale)
        self.collapsables.append(self.factSpinBox)

        self.scaleCheckBox = QtWidgets.QCheckBox('No Scrollbars')
        self.scaleCheckBox.setCheckState(QtCore.Qt.Checked)
        self.scaleCheckBox.stateChanged.connect(self.fitMinWindowSize)
        self.collapsables.append(self.scaleCheckBox)

        self.interpCheckBox = QtWidgets.QCheckBox('Interpolated Scaling')
        self.interpCheckBox.setCheckState(QtCore.Qt.Unchecked)
        self.interpCheckBox.stateChanged.connect(self.applyImageScale)
        self.collapsables.append(self.interpCheckBox)

        self._clipboard_btn = BasicPushButton()
        self._clipboard_btn.set_button_title('Copy')
        self._clipboard_btn.set_toggle(False)
        self._clipboard_btn.valueChanged.connect(self.copytoclipboard)
        self.collapsables.append(self._clipboard_btn)

        self._savefile_btn = BasicPushButton()
        self._savefile_btn.set_button_title('Save')
        self._savefile_btn.set_toggle(False)
        self._savefile_btn.valueChanged.connect(self.savetopng)
        self.collapsables.append(self._savefile_btn)
        self._directory = None
        self._filter = 'Image (*.png)'
        self._caption = 'Save to PNG'
        self._cur_fname = ''

        # COPY/SAVE btns
        hbox_cpysv = QtWidgets.QHBoxLayout()
        hbox_cpysv.addWidget(self._clipboard_btn)
        hbox_cpysv.addWidget(self._savefile_btn)

        btns = ['Pointer', 'Line', 'Rectangle', 'Ellipse']
        self.ann_box = QtWidgets.QHBoxLayout()
        for btnl in btns:
            btn = QtWidgets.QCheckBox(btnl)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            if btnl == 'Line':
                btn.setChecked(True)
            else:
                btn.setChecked(False)
            btn.stateChanged.connect(self.annotationButton)
            self.ann_box.addWidget(btn)
            self.collapsables.append(btn)
        self.ann_type = 'Line'

        # LEFT PANEL
        vbox_l = QtWidgets.QVBoxLayout()
        vbox_l.addLayout(hbox_cpysv)
        vbox_l.addWidget(self.factSpinBox)

        # CENTER PANEL
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.scaleCheckBox)
        vbox.addWidget(self.interpCheckBox)
        vbox.addLayout(self.ann_box)

        # RIGHT PANEL
        #vbox_r = QtWidgets.QVBoxLayout()
        #vbox_r.addWidget(self._clipboard_btn)

        hboxGroup = QtWidgets.QHBoxLayout()
        hboxGroup.addLayout(vbox_l)
        hboxGroup.addLayout(vbox)
        #hboxGroup.addLayout(vbox_r)
        hboxGroup.setStretch(0, 0)

        self.wdg = self.scrollArea

        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.wdg, 1, 0, 3, 3)
        wdgLayout.addLayout(hboxGroup, 0, 0)
        wdgLayout.setRowStretch(1, 2)
        self.setLayout(wdgLayout)

        self._pixmap = None
        self._value = None
        self._scaleFact = 1.0
        self.set_collapsed(True)  # hide options by default

    def savetopng(self):

        if self._pixmap is None:
            log.warn('DisplayBox: There is no image to save, skipping.')
            return

        kwargs = {}
        kwargs['cur_fname'] = self._cur_fname
        kwargs['filter'] = self._filter
        kwargs['caption'] = self._caption
        kwargs['directory'] = self._directory

        # create dialog box
        dia = GPIFileDialog(self, **kwargs)

        # don't run if cancelled
        if dia.runSaveFileDialog():

            # save the current directory for next browse
            if Config.GPI_FOLLOW_CWD:
                self._directory = str(dia.directory().path())

            # enforce the selected filter in the captured filename
            self._cur_fname = dia.selectedFilteredFiles()[0]

            if self._pixmap.save(self._cur_fname, format='PNG'):
                log.dialog('Image successfully saved.')
            else:
                log.warn('Image failed to save.')

    def annotationButton(self, value):
        if value:
            for i in range(self.ann_box.count()):
                if self.ann_box.itemAt(i).widget().isChecked():
                    self.ann_type = str(self.ann_box.itemAt(i).widget().text())

    def annType(self):
        return self.ann_type

    def isPointer(self):
        return self.ann_type == 'Pointer'
    def isLine(self):
        return self.ann_type == 'Line'
    def isRectangle(self):
        return self.ann_type == 'Rectangle'
    def isEllipse(self):
        return self.ann_type == 'Ellipse'

    def copytoclipboard(self):
        if self._pixmap is not None:
            QtWidgets.QApplication.clipboard().setPixmap(self._pixmap)
            log.dialog('DisplayBox image copied to clipboard.')
        else:
            log.warn('DisplayBox: There is no image to copy to the clipboard, skipping.')

    # setters
    def set_collapsed(self, val):
        """bool | Only collapse the display options, not the QPixmap/QLabel window.
        """
        self._isCollapsed = val
        for wdg in self.collapsables:
            if hasattr(wdg, 'setVisible'):
                wdg.setVisible(not val)

    def set_val(self, image):
        '''QImage | Image is a QImage().
        '''
        self._value = image
        # QImages get filtered out of network serialization
        # this is a bandaid, this code should instead work
        # with a serializeable object.
        if image is not None:
            self._pixmap = QtGui.QPixmap.fromImage(image)
            self.setImageScale(self._scaleFact)

    def set_noscroll(self, val):
        """bool | Turn display window scroll on/off with boolean False/True."""
        self.scaleCheckBox.setChecked(val)

    def set_interp(self, val):
        """bool | Interpolated scaling / nearest neighbor, boolean True/False."""
        self.interpCheckBox.setChecked(val)

    def set_scale(self, val):
        """float | Pre-defined image dimension scale (float)"""
        self.factSpinBox.set_val(val)

    def set_pixmap(self, val):
        """QPixmap | A QPixmap to be displayed."""
        self._pixmap = val
        self.setImageScale(self._scaleFact)

    def set_line(self, val):
        '''N/A | Doesn't do anything yet.
        '''
        pass

    def set_points(self, val):
        '''N/A | Doesn't do anything yet.
        '''
        pass

    # getters
    def get_scale(self):
        return self.factSpinBox.get_val()

    def get_interp(self):
        return self.interpCheckBox.isChecked()

    def get_noscroll(self):
        return self.scaleCheckBox.isChecked()

    def get_val(self):
        # QImage is not serializable
        #return self._value
        pass

    def get_line(self):
        return self.imageLabel.getLine()

    def get_points(self):
        if self.isPointer():
            return self.imageLabel.getPoint()
        elif self.isLine():
            return self.imageLabel.getLine()
        elif self.isRectangle():
            return self.imageLabel.getPoints()
        elif self.isEllipse():
            return self.imageLabel.getPoints()

    # support
    def somethingChanged(self):
        '''send a downstream event.'''
        self.valueChanged.emit(0)

    def setImageScale(self, scale):
        self._scaleFact = scale
        if self._pixmap is not None:
            self.applyImageScale()
        self.fitMinWindowSize()

    def applyImageScale(self):
        if self.interpCheckBox.checkState():
            scale_type = QtCore.Qt.SmoothTransformation
        else:
            scale_type = QtCore.Qt.FastTransformation

        if self._pixmap is not None:
            newpixmap = self._pixmap.scaled(self._pixmap.size() * self._scaleFact,
                                        aspectRatioMode=QtCore.Qt.KeepAspectRatio,
                                        transformMode=scale_type)
            self.imageLabel.setPixmap(newpixmap)
            self.imageLabel.adjustSize()

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                               + ((factor - 1) * scrollBar.pageStep()//2)))

    def fitMinWindowSize(self):
        labsize = self.imageLabel.size()
        h = labsize.height()
        w = labsize.width()
        pad = 4  # scroll won't turn off unless
        if self.scaleCheckBox.checkState():
            self.wdg.resize(labsize)
            self.wdg.setMinimumSize(QtCore.QSize(w+pad, h+pad))
        else:
            self.wdg.setMinimumSize(QtCore.QSize(0, 0))

        self.wdg.setMaximumSize(QtCore.QSize(w+pad+1, h+pad+1))

# WIDGET


class PushButton(GenericWidgetGroup):
    """A simple single pushbutton box."""
    valueChanged = gpi.Signal(bool)

    def __init__(self, title, parent=None):
        super(PushButton, self).__init__(title, parent)
        self.wdg = BasicPushButton()
        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.wdg, 0, 0, 1, 4)
        wdgLayout.setVerticalSpacing(0)
        self.setLayout(wdgLayout)
        self.wdg.valueChanged.connect(self.valueChanged)

    # setters
    def set_toggle(self, val):
        """bool | Make the pushbutton a toggle button on/off -> True/False."""
        self.wdg.set_toggle(val)

    def set_button_title(self, val):
        """str | Place a title, centered, on the button."""
        self.wdg.set_button_title(val)

    def set_val(self, val):
        """bool | The button state is a bool: on/off -> True/False."""
        self.wdg.set_val(val)

    def set_reset(self):
        """No Arg | Overrides the generic reset to specifically set the QPushButton.
        For oneshot functionality this gets called automatically after the
        node compute().
        """
        self.wdg.set_reset()

    # getters
    def get_toggle(self):
        return self.wdg.get_toggle()

    def get_button_title(self):
        return self.wdg.get_button_title()

    def get_val(self):
        return self.wdg.get_val()

# WIDGET

# A simple tool for storing strings in a non-plaintext manner
#  NOTE: NOT for strong security.
# Temporarily taken out since zlib.decompress causes segfault on otherside of fork.
#import zlib
#def unhash_String(s):
#    return zlib.decompress(s)
#def hash_String(s):
#    return zlib.compress(s)

def unhash_String(s):
    return s
def hash_String(s):
    return s



class StringBox(GenericWidgetGroup):
    """A simple single line string box."""

    valueChanged = gpi.Signal()

    def __init__(self, title, parent=None):
        super(StringBox, self).__init__(title, parent)

        self.wdg = QtWidgets.QLineEdit()

        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.wdg, 0, 0, 1, 3)
        self.setLayout(wdgLayout)

        self.wdg.returnPressed.connect(self.valueChanged)

        self._mask = False

    # setters
    def set_val(self, value):
        """str | Set the string (str)."""
        self.wdg.setText(value)

    def set_mask(self, val):
        '''bool | Toggle input mask'''
        self._mask = val
        if val:
            self.wdg.setEchoMode(QtWidgets.QLineEdit.Password)
        else:
            self.wdg.setEchoMode(QtWidgets.QLineEdit.Normal)

    def set_maskedval(self, val):
        '''None | No setter for storing.
        '''
        pass

    def set_placeholder(self, val):
        '''str | Set the placeholder text (str).'''
        self.wdg.setPlaceholderText(val)

    # getters
    def get_val(self):
        '''If its in masked mode then it must be
        specifically handled thru get_maskedval().
        '''
        if self._mask:
            return ''
        return str(self.wdg.text())

    def get_maskedval(self):
        '''If the string box is acting as a password
        then this getter must be used.
        '''
        return hash_String(str(self.wdg.text()))

    def get_mask(self):
        return self._mask

    def get_placeholder(self):
        return str(self.wdg.placeholderText())


# WIDGET


class DoubleSpinBox(GenericWidgetGroup):
    """Spin box for floating point values. """
    valueChanged = gpi.Signal(float)

    def __init__(self, title, parent=None):
        super(DoubleSpinBox, self).__init__(title, parent)
        self.wdg = BasicDoubleSpinBox()
        wdgLayout = QtWidgets.QHBoxLayout()
        wdgLayout.addWidget(self.wdg)
        # wdgLayout.setVerticalSpacing(0)
        wdgLayout.setContentsMargins(0, 0, 0, 0)  # no spaces around this item
        wdgLayout.setSpacing(0)
        self.setLayout(wdgLayout)
        self.wdg.valueChanged.connect(self.valueChanged)

    # setters
    def set_max(self, val):
        """float | Max float value (<=)."""
        self.wdg.set_max(val)

    def set_min(self, val):
        """float | Min float value (>=)."""
        self.wdg.set_min(val)

    def set_val(self, val):
        """float | The value (float)."""
        self.wdg.set_val(val)

    def set_label(self, val):
        """str | Set a text left of the spinbox (str)."""
        self.wdg.set_label(val)

    def set_wrapping(self, val):
        """bool | Allow the up/down buttons to cause a wrap
        when exceeding max or min values (bool)."""
        self.wdg.set_wrapping(val)

    def set_decimals(self, val):
        """int | The number of displayed decimal places (int)."""
        self.wdg.set_decimals(val)

    def set_singlestep(self, val):
        """float | The stepsize of one up/down button click (float)."""
        self.wdg.set_singlestep(val)

    def set_immediate(self, val):
        """bool | Make the value changes immediate with scroll wheel etc..."""
        self.wdg.set_immediate(val)

    # getters
    def get_immediate(self):
        return self.wdg.get_immediate()

    def get_max(self):
        return self.wdg.get_max()

    def get_min(self):
        return self.wdg.get_min()

    def get_val(self):
        return self.wdg.get_val()

    def get_label(self):
        return self.wdg.get_label()

    def get_wrapping(self):
        return self.wdg.get_wrapping()

    def get_decimals(self):
        return self.wdg.get_decimals()

    def get_singlestep(self):
        return self.wdg.get_singlestep()

# WIDGET


class WebBox(GenericWidgetGroup):
    """For loading web urls. """
    valueChanged = gpi.Signal(str)

    def __init__(self, title, parent=None):
        super(WebBox, self).__init__(title, parent)
        if QWebView is None:
            raise ImportError(
                "Neither QtWebKit.QWebView or QtWebKitWidgets.QWebView "
                "is available in this Qt installation "
                "({}).".format(QT_API_NAME))
        self.wdg = QWebView()
        wdgLayout = QtWidgets.QHBoxLayout()
        wdgLayout.addWidget(self.wdg)
        wdgLayout.setStretch(0, 2)
        # wdgLayout.setVerticalSpacing(0)
        wdgLayout.setContentsMargins(0, 0, 0, 0)  # no spaces around this item
        #wdgLayout.setSpacing(0)
        self.setLayout(wdgLayout)
        self.wdg.urlChanged.connect(self.urlToString)

        self._user = None
        self._passwd = None
        self._url = None

    # setters
    def set_val(self, val):
        """str | The url (str)."""

        self._url = QtCore.QUrl(val)
        if self._user:
            self._url.setUserName(self._user)
        if self._passwd:
            self._url.setPassword(self._passwd)
        if self._url.isValid():
            self.wdg.load(self._url)
        else:
            self._url = None

    def set_username(self, usr):
        '''str | For login sites'''
        self._user = usr

        if self._user is None:
            return

        if self._url:
            self._url.setUserName(self._user)
            self.wdg.load(self._url)

    def set_passwd(self, passwd):
        '''str | For login sites'''
        # can be used with masked_val from Stringbox
        self._passwd = passwd

        if self._passwd is None:
            return

        if self._url:
            self._url.setPassword(unhash_String(self._passwd))
            self.wdg.load(self._url)

    # getters
    def get_val(self):
        url = QtCore.QUrl(self.wdg.url())
        # wipe user and pass
        url.setPassword('')
        url.setUserName('')
        return url.toString()

    def get_username(self):
        return None

    def get_passwd(self):
        return None

    # support
    def urlToString(self, url):
        self.valueChanged.emit(url.toString())


# WIDGET


class SpinBox(GenericWidgetGroup):
    """Spin box for integer values. """
    valueChanged = gpi.Signal(int)

    def __init__(self, title, parent=None):
        super(SpinBox, self).__init__(title, parent)
        self.wdg = BasicSpinBox()
        wdgLayout = QtWidgets.QHBoxLayout()
        wdgLayout.addWidget(self.wdg)
        # wdgLayout.setVerticalSpacing(0)
        wdgLayout.setContentsMargins(0, 0, 0, 0)  # no spaces around this item
        wdgLayout.setSpacing(0)
        self.setLayout(wdgLayout)
        self.wdg.valueChanged.connect(self.valueChanged)

    # setters
    def set_max(self, val):
        """int | Max integer value (<=)."""
        self.wdg.set_max(val)

    def set_min(self, val):
        """int | Min integer value (>=)."""
        self.wdg.set_min(val)

    def set_val(self, val):
        """int | The value (int)."""
        self.wdg.set_val(val)

    def set_label(self, val):
        """str | Set a text left of the spinbox (str)."""
        self.wdg.set_label(val)

    def set_wrapping(self, val):
        """int | The number of displayed decimal places (int)."""
        self.wdg.set_wrapping(val)

    def set_singlestep(self, val):
        """int | The stepsize of one up/down button click (int)."""
        self.wdg.set_singlestep(val)

    def set_immediate(self, val):
        """bool | Make the value changes immediate with scroll wheel etc..."""
        self.wdg.set_immediate(val)

    # getters
    def get_immediate(self):
        return self.wdg.get_immediate()

    def get_max(self):
        return self.wdg.get_max()

    def get_min(self):
        return self.wdg.get_min()

    def get_val(self):
        return self.wdg.get_val()

    def get_label(self):
        return self.wdg.get_label()

    def get_wrapping(self):
        return self.wdg.get_wrapping()

    def get_singlestep(self):
        return self.wdg.get_singlestep()

# WIDGET


class Slider(GenericWidgetGroup):
    """A slider for integer values. """
    valueChanged = gpi.Signal(int)

    def __init__(self, title, parent=None):
        super(Slider, self).__init__(title, parent)
        self.wdg = BasicSlider()
        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.wdg, 0, 0, 1, 4)
        wdgLayout.setVerticalSpacing(0)
        self.setLayout(wdgLayout)
        self.wdg.valueChanged.connect(self.valueChanged)

    # setters
    def set_val(self, value):
        """int | The value (int)."""
        self.wdg.set_val(value)

    def set_min(self, value):
        """int | Min integer value (>=)."""
        self.wdg.set_min(value)

    def set_max(self, value):
        """int | Max integer value (<=)."""
        self.wdg.set_max(value)

    # getters
    def get_max(self):
        return self.wdg.get_max()

    def get_min(self):
        return self.wdg.get_min()

    def get_val(self):
        return self.wdg.get_val()

# WIDGET


class ExclusivePushButtons(GenericWidgetGroup):
    """Provides a set of check boxes for different labels.
    -Buttons are placed side-by-side.
    """
    valueChanged = gpi.Signal(bool)

    def __init__(self, title, parent=None):
        super(ExclusivePushButtons, self).__init__(title, parent)

        # at least one button
        self.buttons = []
        btn = QtWidgets.QPushButton()
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setChecked(True)
        self.buttons.append(btn)
        self.vbox = QtWidgets.QHBoxLayout()
        self.vbox.setSpacing(0)
        for button in self.buttons:
            self.vbox.addWidget(button)
            button.clicked.connect(self.findValue)
            button.clicked.connect(self.valueChanged)
        # self.vbox.addStretch(1)
        self.setLayout(self.vbox)

    # setters
    def set_val(self, value):
        """ int | The position of the chosen button (zero-based, int)."""
        self._value = value
        if value < len(self.buttons):
            self.buttons[value].setChecked(True)
        else:
            msg = "In widget \'"+str(self._title)+"\':\n"
            msg += "\t\tExclusivePushButtons: set_val(): requrested button \'"
            msg += str(value)+"\' exceeds button list len of \'"
            msg += str(len(self.buttons))+"\'"
            log.critical(msg)

    #def set_visibility_mask(self, mask):
    #    """A list of booleans that determine which buttons are visible or not"""

    def set_buttons(self, names):
        """list(str,str,...) | A list of labels (e.g. ['b1', 'b2',...])."""
        # add buttons if necessary
        while len(names) > len(self.buttons):
            newbutton = QtWidgets.QPushButton()
            newbutton.setCheckable(True)
            newbutton.setAutoExclusive(True)
            self.buttons.append(newbutton)
            self.vbox.addWidget(newbutton)
            newbutton.clicked.connect(self.findValue)
            newbutton.clicked.connect(self.valueChanged)

        # remove buttons if necessary
        while len(names) < len(self.buttons):
            oldbutton = self.buttons.pop()
            oldbutton.setParent(None)

        if len(names) != len(self.buttons):
            log.critical("ExclusivePushButtons: set_buttons(): len not properly set.")

        for i in range(len(self.buttons)):
            self.buttons[i].setText(names[i])

        [button.setMinimumWidth(50) for button in self.buttons]

    # getters
    def get_val(self):
        return self._value

    # support
    def findValue(self, value):
        cnt = 0
        for button in self.buttons:
            if button.isChecked():
                self._value = cnt
                return
            cnt += 1

# WIDGET

# JGP 13jun20
# RKR modified 13jul10

class NonExclusivePushButtons(GenericWidgetGroup):
    """Provides a set of check boxes for different labels.
    -Buttons are placed side-by-side.
    """
    valueChanged = gpi.Signal(bool)

    def __init__(self, title, parent=None):
        super(NonExclusivePushButtons, self).__init__(title, parent)

        # at least one button
        self.buttons = []
        btn = QtWidgets.QPushButton()
        btn.setCheckable(True)
        btn.setAutoExclusive(False)
        btn.setChecked(False)
        self.buttons.append(btn)
        self.vbox = QtWidgets.QHBoxLayout()
        self.vbox.setSpacing(0)
        for button in self.buttons:
            self.vbox.addWidget(button)
            button.clicked.connect(self.findValue)
            button.clicked.connect(self.valueChanged)
        # self.vbox.addStretch(1)
        self.setLayout(self.vbox)

    # setters
    def set_val(self, value):
        """int or list(int,int,...) | The position of the chosen button (zero-based, int or list)."""
        if type(value) is not list:
            value = [value]
        self._value = value
        for button_ind in range(len(self.buttons)):
            if button_ind in value:
                self.buttons[button_ind].setChecked(True)
            else:
                self.buttons[button_ind].setChecked(False)

    def set_buttons(self, names):
        """list(str,str,...) | A list of labels (e.g. ['b1', 'b2',...])."""
        # add buttons if necessary
        while len(names) > len(self.buttons):
            newbutton = QtWidgets.QPushButton()
            newbutton.setCheckable(True)
            newbutton.setAutoExclusive(False)
            self.buttons.append(newbutton)
            self.vbox.addWidget(newbutton)
            newbutton.clicked.connect(self.findValue)
            newbutton.clicked.connect(self.valueChanged)

        # remove buttons if necessary
        while len(names) < len(self.buttons):
            oldbutton = self.buttons.pop()
            oldbutton.setParent(None)

        if len(names) != len(self.buttons):
            log.critical("set_buttons(): len not properly set.")

        for i in range(len(self.buttons)):
            self.buttons[i].setText(names[i])

        [button.setMinimumWidth(50) for button in self.buttons]

    # getters
    def get_val(self):
        return self._value

    # support
    def findValue(self, value):
        cnt = 0
        valarr = []
        for button in self.buttons:
            if button.isChecked():
                valarr.append(cnt)
            cnt += 1
        self._value = valarr
        return


# WIDGET

class ComboBox(GenericWidgetGroup):
    """Provides a popup list for different labels.
    """

    valueChanged = gpi.Signal(int)

    def __init__(self, title, parent=None):
        super(ComboBox, self).__init__(title, parent)

        self.wdg = QtWidgets.QComboBox()
        wdgLayout = QtWidgets.QGridLayout()
        wdgLayout.addWidget(self.wdg)
        wdgLayout.setVerticalSpacing(0)
        self.setLayout(wdgLayout)
        self.wdg.currentIndexChanged.connect(self.valueChanged)

    # setters
    def set_items(self, items):
        '''list(str,str,...) | list of items to choose from. Only one item can be chosen from the list. '''
        self.wdg.clear()
        self.wdg.addItems(items)

    def set_val(self, item_text):
        '''int | item index'''
        item_text_index = 0
        nr_items = self.wdg.count()
        for index in range(nr_items):
            if item_text == str(self.wdg.itemText(index)):
                item_text_index = index
        self.wdg.setCurrentIndex(item_text_index)

    def set_index(self, index):
        '''int | gives the corresponding index of the chosen item, starting at 0.  So, for example, self.getAttr('myfruitbox',index) would return a 2 if 'orange' were selected from the item list given in this table, while self.getVal('myfruitbox') would return the string 'orange'. '''
        # protect against async widget loading and user input
        if index < self.wdg.count() and index >= 0:
            self.wdg.setCurrentIndex(index)

    # getters
    def get_items(self):
        items = []
        nr_items = self.wdg.count()
        for index in range(nr_items):
            items.append(str(self.wdg.itemText(index)))
        return items

    def get_val(self):
        return str(self.wdg.currentText())

    def get_index(self):
        return self.wdg.currentIndex()


# WIDGET


class ExclusiveRadioButtons(GenericWidgetGroup):
    """Provides a set of check boxes for different labels.
    -Buttons are stacked.
    """

    valueChanged = gpi.Signal(bool)

    def __init__(self, title, parent=None):
        super(ExclusiveRadioButtons, self).__init__(title, parent)

        # at least one button
        self.buttons = []
        self.buttons.append(QtWidgets.QRadioButton())
        self.vbox = QtWidgets.QVBoxLayout()
        for button in self.buttons:
            self.vbox.addWidget(button)
            button.clicked.connect(self.findValue)
            button.clicked.connect(self.valueChanged)
        # self.vbox.addStretch(1)
        self.setLayout(self.vbox)

    # setters
    def set_val(self, value):
        """int | The position of the chosen button (zero-based, int)."""
        self._value = value
        self.buttons[value].setChecked(True)

    def set_buttons(self, names):
        """list(str,str,...) | A list of labels (e.g. ['b1', 'b2',...])."""
        # add buttons if necessary
        while len(names) > len(self.buttons):
            newbutton = QtWidgets.QRadioButton()
            self.buttons.append(newbutton)
            self.vbox.addWidget(newbutton)
            newbutton.clicked.connect(self.findValue)
            newbutton.clicked.connect(self.valueChanged)

        # remove buttons if necessary
        while len(names) < len(self.buttons):
            oldbutton = self.buttons.pop()
            oldbutton.setParent(None)

        if len(names) != len(self.buttons):
            log.critical("set_buttons(): len not properly set.")

        for i in range(len(self.buttons)):
            self.buttons[i].setText(names[i])

    # getters
    def get_val(self):
        return self._value

    # support
    def findValue(self, value):
        cnt = 0
        for button in self.buttons:
            if button.isChecked():
                self._value = cnt
                return
            cnt += 1
