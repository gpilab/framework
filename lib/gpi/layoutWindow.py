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


# gpi
import gpi
from gpi import QtCore, QtGui, QtWidgets
from .defines import isWidget
from .widgets import HidableGroupBox
from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)


class LayoutWindow(QtWidgets.QFrame):
    '''This class controls the low level operations on "Layout Windows". It 
    handles the drag and drop events for pulling widgets out of "Node Menus".
    It also handles low-level serialization.
    '''

    changed = gpi.Signal()

    def __init__(self, graph, layoutType, label, parent=None):
        super(LayoutWindow, self).__init__(parent)
        self.setAcceptDrops(True)

        self._graph = graph
        self.setLabel(label)
        self.setLayoutType(layoutType)

        # keep track of child order since Qt doesn't
        self._wdgidList = []

    def setLayoutType(self, typ):
        '''The basic layout is VBox or HBox.
        '''
        self._layoutType = typ
        if typ == 'vbox':
            self._layout = QtWidgets.QVBoxLayout()
        elif typ == 'hbox':
            self._layout = QtWidgets.QHBoxLayout()

    def setLabel(self, lab):
        '''This label allows the layoutWindow to be placed in the correct place
        within the MasterLayout.
        '''
        self._label = lab

    def pushWdgID(self, wdgid):
        '''Push a newly dropped widget to the end of the list.
        '''
        self._wdgidList.append(wdgid)

    def widgetMovingEvent(self, wdgid):
        '''If a drag is initiated the widget will always be moved.
        --see the widget drag event for details in widgets.py.
        '''
        self._wdgidList.remove(wdgid)

    def label(self):
        return self._label

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/gpi-widget'):
            # event.acceptProposedAction()
            event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/gpi-widget'):
            # event.acceptProposedAction()
            event.accept()

    def dropEvent(self, event):
        log.debug("dropped in test window")
        if event.mimeData().hasFormat('application/gpi-widget'):
            mime = event.mimeData()
            itemData = mime.data('application/gpi-widget')
            dataStream = QtCore.QDataStream(
                itemData, QtCore.QIODevice.ReadOnly)

            text = QtCore.QByteArray()
            offset = QtCore.QPoint()
            dataStream >> text >> offset

            if self.addWidgetByID(self._graph.getAllNodes(), int(text)):
                # event.acceptProposedAction()
                event.accept()
            else:
                event.ignore()

    def dragLeaveEvent(self, event):
        event.accept()

    def addWidgetByID(self, nodeList, wdgid):
        '''Only search for widgets within the nodeList.
        '''
        parm = self._graph.findWidgetByID(nodeList, wdgid)
        if parm is None:
            log.error("LayoutWindow(): addWidget failed, wdgid not found!!!")
            return False

        # save the actual id
        self.pushWdgID(id(parm))
        self._layout.addWidget(parm)
        self.setLayout(self._layout)

        parm.setDispTitle()  # parent changed

        self.changed.emit()
        return True

    def count(self):
        return len(self._wdgidList)

    def getSettings(self):
        '''Get widget id's from this layout.
        NOTE: widgets are not stored by the QObject in any particular order.
        '''
        s = {}
        s['label'] = self.label()
        s['layoutType'] = self._layoutType
        s['wdgids'] = self._wdgidList

        return s

    def loadSettings(self, s, nodeList):
        '''Given the information generated by getSettings(), load the
        corresponding widgets.  Searches for widgets within the supplied
        nodeList.
        '''
        self.setLayoutType(s['layoutType'])
        for wdg in s['wdgids']:
            log.debug("\t adding wdgid: " + str(wdg))
            self.blockSignals(True)  # keep from calling columnAdjust()
            self.addWidgetByID(nodeList, int(wdg))
            self.blockSignals(False)

    def getWdgByID(self, wdgid):
        for wdg in self.getGPIWidgets():
            if wdgid == wdg.get_id():
                return wdg

    def getGPIWidgets(self):
        '''Search all children for valid GPI widget objects and list them.
        '''
        gpichilds = []
        for wdg in self.children():
            if isWidget(wdg):
                gpichilds.append(wdg)
        return gpichilds


class LayoutMaster(QtWidgets.QWidget):
    '''This is the main "Layout-Window" API.  It controls the layout config,
    reinstantiation of layouts, opening and closing, etc...
    '''

    def __init__(self, graph, config=0, macro=False, labelWin=False, parent=None):
        super(LayoutMaster, self).__init__(parent)

        self._graph = graph
        self._isMacroWdg = macro
        self._labelWin = labelWin

        self.initLayout(config)

    def initLayout(self, config):
        '''Given the config initialize all layout objects overwriting any
        existing layouts.
        '''
        self._config = config
        self._lwList = []

        # delete layout if one exists
        # TODO: this needs to work if Layouts are to be re-initialized
        #if self.layout():
        #    print "delete layout before setting a new one."
        #    for lw in self._lwList:
        #        for c in lw.children():
        #            c.setParent(None)
        #        lw.setParent(None)
        #    self.layout().setParent(None)

        hbox = QtWidgets.QVBoxLayout(self)

        if config == 0:
            top = LayoutWindow(self._graph, 'vbox', 'top')
            top.setFrameShape(QtWidgets.QFrame.StyledPanel)
            hbox.addWidget(top)
            self._lwList.append(top)

        elif config == 1:
            top = LayoutWindow(self._graph, 'hbox', 'top')
            top.setFrameShape(QtWidgets.QFrame.StyledPanel)
            hbox.addWidget(top)
            self._lwList.append(top)

        elif config == 2:
            top = LayoutWindow(self._graph, 'hbox', 'top')
            top.setFrameShape(QtWidgets.QFrame.StyledPanel)
            self._lwList.append(top)

            mid = LayoutWindow(self._graph, 'hbox', 'mid')
            mid.setFrameShape(QtWidgets.QFrame.StyledPanel)
            self._lwList.append(mid)

            bottomleft = LayoutWindow(self._graph, 'vbox', 'bottomleft')
            bottomleft.setFrameShape(QtWidgets.QFrame.StyledPanel)
            self._lwList.append(bottomleft)
            bottommid = LayoutWindow(self._graph, 'vbox', 'bottommid')
            bottommid.setFrameShape(QtWidgets.QFrame.StyledPanel)
            self._lwList.append(bottommid)
            bottomright = LayoutWindow(self._graph, 'vbox', 'bottomright')
            bottomright.setFrameShape(QtWidgets.QFrame.StyledPanel)
            self._lwList.append(bottomright)

            splitter1 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
            splitter1.addWidget(top)
            splitter1.addWidget(mid)

            splitter2 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
            splitter2.addWidget(bottomleft)
            splitter2.addWidget(bottommid)
            splitter2.addWidget(bottomright)

            splitter3 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
            splitter3.addWidget(splitter1)
            splitter3.addWidget(splitter2)

            hbox.addWidget(splitter3)

        elif config == 3:
            top = LayoutWindow(self._graph, 'vbox', 'top')
            top.setFrameShape(QtWidgets.QFrame.StyledPanel)
            top.changed.connect(self.columnAdjust)
            self.topsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
            self.topsplitter.addWidget(top)

            bottom = LayoutWindow(self._graph, 'vbox', 'bottom')
            bottom.setFrameShape(QtWidgets.QFrame.StyledPanel)
            bottom.changed.connect(self.columnAdjust)
            self.bottomsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
            self.bottomsplitter.addWidget(bottom)

            vsplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
            vsplitter.addWidget(self.topsplitter)
            vsplitter.addWidget(self.bottomsplitter)

            hbox.addWidget(vsplitter)

        if self._labelWin:
            # make a label box with the unique id
            self.wdglabel = QtWidgets.QLineEdit('')
            labelGroup = HidableGroupBox("Node Label")
            labelLayout = QtWidgets.QVBoxLayout()
            labelLayout.addWidget(self.wdglabel)
            labelGroup.setLayout(labelLayout)
            hbox.addWidget(labelGroup)
            labelGroup.set_collapsed(True)
            labelGroup.setToolTip(
                "Displays the Label on the Canvas (Double Click)")

        self.setLayout(hbox)

    def getSettings(self):
        '''Serialize widget ids and layout patterns into a dict.
        The list of layout keys is specific to each config.
        '''
        s = {}
        s['config'] = self.config()
        s['layouts'] = {}
        for lw in self.findChildren(LayoutWindow):
            s['layouts'][lw.label()] = lw.getSettings()
        return s

    def loadSettings(self, s, nodeList):
        '''Deserialize layout settings and reconstruct layout.
        '''

        log.debug("LayoutMaster loadSettings():")
        log.debug(str(s))

        # Change layout if necessary.
        # After this, all layoutWindows will be populated and their labels
        # set.
        # TODO: initLayout() can't be called twice, yet...
        if s['config'] != self._config:
            self.initLayout(s['config'])

        # add all necessary top and bottom columns for expanding layout
        # wls: window layout settings
        if self._config == 3:
            curlabels = [lw.label() for lw in self.findChildren(LayoutWindow)]
            for label, wls in list(s['layouts'].items()):
                if label not in curlabels:
                    if label.startswith('top'):
                        self.addTopColumn(label)
                    else:
                        self.addBottomColumn(label)

        # assign widgets to each layout
        # wls: window layout settings
        for label, wls in list(s['layouts'].items()):
            log.debug("trying " + label)

            for lw in self.findChildren(LayoutWindow):
                if lw.label() == label:
                    log.debug("adding " + label)
                    lw.loadSettings(wls, nodeList)

    def config(self):
        '''returns the layout config identifier.
        '''
        return self._config

    def addDummyTopColumn(self):
        '''To allow the user to add to the next topsplitter, there must be an
        open LayoutBox to drop to. -so there always needs to be one extra.'''
        lab = 'top' + str(self.topsplitter.count())
        self.addTopColumn(lab)

    def addTopColumn(self, lab):
        top = LayoutWindow(self._graph, 'vbox', lab)
        top.setFrameShape(QtWidgets.QFrame.StyledPanel)
        top.changed.connect(self.columnAdjust)
        self.topsplitter.addWidget(top)

    def addBottomColumn(self, lab):
        bottom = LayoutWindow(self._graph, 'vbox', lab)
        bottom.setFrameShape(QtWidgets.QFrame.StyledPanel)
        bottom.changed.connect(self.columnAdjust)
        self.bottomsplitter.addWidget(bottom)

    def emptyCount(self):
        emptycnt = 0
        for lw in self.topsplitter.findChildren(LayoutWindow):
            emptycnt += (lw.count() == 0)
        return emptycnt

    def columnAdjust(self):
        '''For config 3, variable column count.'''

        # add leading dummy box
        if self.emptyCount() > 1:
            for lw in self.topsplitter.findChildren(LayoutWindow):
                if self.emptyCount() > 1:
                    if lw.count() == 0:
                        lw.setParent(None)
                        lw.close()
        elif self.emptyCount() < 1:
            self.addDummyTopColumn()

        # fewer columns than hstack
        if (self.topsplitter.count() - 1) > self.bottomsplitter.count():
            lab = 'bottom' + str(self.bottomsplitter.count())
            self.addBottomColumn(lab)

        # more columns than hstack
        elif (self.topsplitter.count() - 1) < self.bottomsplitter.count():
            # need to make sure they are empty first
            for lw in self.bottomsplitter.findChildren(LayoutWindow):
                if (self.topsplitter.count() - 1) < self.bottomsplitter.count():
                    if not lw.count():
                        lw.setParent(None)
                        lw.close()

    def widgetCount(self):
        cnt = 0
        for lw in self.findChildren(LayoutWindow):
            cnt += lw.count()
        return cnt

    def removeLayoutWindowRefs(self):
        # remove self (THIS widget) from the graph's layout list
        try:
            l = self._graph._layoutwindowList
            l[l.index(self)] = None
        except:
            log.critical("FixMe: this is why graph side operations shouldn't be " + "performed within a graph child.")

    def forceClose(self):
        '''Return all menu widgets to proper node before closing.
        '''
        log.debug("force closing widget")
        if self.widgetCount():
            for lw in self.findChildren(LayoutWindow):
                for wdg in lw.getGPIWidgets():
                    wdg.returnToOrigin()
                lw.close()
        self.close()

    def closeEvent(self, event):

        if self._isMacroWdg:
            log.debug("is a macro so continue to close")
            event.accept()
            return

        # don't close if any are attached
        if not self.widgetCount():
            self.removeLayoutWindowRefs()
            event.accept()
            return
        event.ignore()
