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
import imp
import time
import copy
import hashlib
import inspect
import traceback
from multiprocessing import sharedctypes # numpy xfer

# gpi
import gpi
from gpi import QtCore, QtGui, QtWidgets
from .defines import ExternalNodeType, GPI_PROCESS, GPI_THREAD, stw, GPI_SHDM_PATH
from .defines import GPI_WIDGET_EVENT, REQUIRED, OPTIONAL, GPI_PORT_EVENT
from .dataproxy import DataProxy, ProxyType
from .logger import manager
from .port import InPort, OutPort
from .widgets import HidableGroupBox
from . import widgets as BUILTIN_WIDGETS
from . import syntax


# start logger for this module
log = manager.getLogger(__name__)

# for PROCESS data hack
import numpy as np

# Developer Interface Exceptions
class GPIError_nodeAPI_setData(Exception):
    def __init__(self, value):
        super(GPIError_nodeAPI_setData, self).__init__(value)

class GPIError_nodeAPI_getData(Exception):
    def __init__(self, value):
        super(GPIError_nodeAPI_getData, self).__init__(value)

class GPIError_nodeAPI_setAttr(Exception):
    def __init__(self, value):
        super(GPIError_nodeAPI_setAttr, self).__init__(value)

class GPIError_nodeAPI_getAttr(Exception):
    def __init__(self, value):
        super(GPIError_nodeAPI_getAttr, self).__init__(value)

class GPIError_nodeAPI_getVal(Exception):
    def __init__(self, value):
        super(GPIError_nodeAPI_getVal, self).__init__(value)

class NodeAPI(QtWidgets.QWidget):
    """
    Base class for all external nodes.

    External nodes implement the extensible methods of this class: i.e.
    compute(), validate(), execType(), etc... to create a unique Node module.
    """
    GPIExtNodeType = ExternalNodeType  # ensures the subclass is of THIS class
    modifyWdg = gpi.Signal(str, dict)

    def __init__(self, node):
        super(NodeAPI, self).__init__()

        #self.setToolTip("Double Click to Show/Hide each Widget")
        self.node = node

        self.label = ''
        self._detailLabel = ''
        self._docText = None
        self.parmList = []  # deprecated, since dicts have direct name lookup
        self.parmDict = {}  # mirror parmList for now
        self.parmSettings = {}  # for buffering wdg parms before copying to a PROCESS
        self.shdmDict = {} # for storing base addresses

        # grid for module widgets
        self.layout = QtWidgets.QGridLayout()

        # this must exist before user-widgets are added so that they can get
        # node label updates
        self.wdglabel = QtWidgets.QLineEdit(self.label)

        # allow logger to be used in initUI()
        self.log = manager.getLogger(node.getModuleName())

        try:
            self._initUI_ret = self.initUI()
        except:
            log.error('initUI() failed. '+str(node.item.fullpath)+'\n'+str(traceback.format_exc()))
            self._initUI_ret = -1  # error

        # make a label box with the unique id
        labelGroup = HidableGroupBox("Node Label")
        labelLayout = QtWidgets.QGridLayout()
        self.wdglabel.textChanged.connect(self.setLabel)
        labelLayout.addWidget(self.wdglabel, 0, 1)
        labelGroup.setLayout(labelLayout)
        self.layout.addWidget(labelGroup, len(self.parmList) + 1, 0)
        labelGroup.set_collapsed(True)
        labelGroup.setToolTip("Displays the Label on the Canvas (Double Click)")

        # make an about box with the unique id
        self.aboutGroup = HidableGroupBox("About")
        aboutLayout = QtWidgets.QGridLayout()
        self.about_button = QtWidgets.QPushButton("Open Node &Documentation")
        self.about_button.clicked.connect(self.openNodeDocumentation)
        aboutLayout.addWidget(self.about_button, 0, 1)
        self.aboutGroup.setLayout(aboutLayout)
        self.layout.addWidget(self.aboutGroup, len(self.parmList) + 2, 0)
        self.aboutGroup.set_collapsed(True)
        self.aboutGroup.setToolTip("Node Documentation (docstring + autodocs, Double Click)")

        # window (just a QTextEdit) that will show documentation text
        self.doc_text_win = QtWidgets.QTextEdit()
        self.doc_text_win.setPlainText(self.generateHelpText())
        self.doc_text_win.setReadOnly(True)
        doc_text_font = QtGui.QFont("Monospace", 14)
        self.doc_text_win.setFont(doc_text_font)
        self.doc_text_win.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.doc_text_win.setWindowTitle(node.getModuleName() + " Documentation")

        hbox = QtWidgets.QHBoxLayout()
        self._statusbar_sys = QtWidgets.QLabel('')
        self._statusbar_usr = QtWidgets.QLabel('')
        hbox.addWidget(self._statusbar_sys)
        hbox.addWidget(self._statusbar_usr, 0, (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter))

        # window resize grip
        self._grip = QtWidgets.QSizeGrip(self)
        hbox.addWidget(self._grip)

        self.layout.addLayout(hbox, len(self.parmList) + 3, 0)
        self.layout.setRowStretch(len(self.parmList) + 3, 0)

        # uid display
        # uid   = QtWidgets.QLabel("uid: "+str(self.node.getID()))
        # uid.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        # self.layout.addWidget(uid,len(self.parmList)+2,0)

        # instantiate the layout
        self.setLayout(self.layout)

        # run through all widget titles since each widget parent is now set.
        for parm in self.parmList:
            parm.setDispTitle()

        # instantiate the layout
        # self.setGeometry(50, 50, 300, 40)

        self.setTitle(node.getModuleName())

        self._starttime = 0
        self._startline = 0

    def initUI_return(self):
        return self._initUI_ret

    def getWidgets(self):
        # return a list of widgets
        return self.parmList

    def getWidgetNames(self):
        return list(self.parmDict.keys())

    def starttime(self):
        """Begin the timer for the node `Wall Time` calculation.

        Nodes store their own runtime, which is displayed in a tooltip when
        hovering over the node on the canvas (see :doc:`../ui`). Normally, each
        node reports the complete time it takes to run its :py:meth:`compute`
        function. However, a dev can use this method along with
        :py:meth:`endtime` to set the portion of :py:meth:`compute` to be used
        to calculate the `Wall Time`.
        """
        self._startline = inspect.currentframe().f_back.f_lineno
        self._starttime = time.time()

    def endtime(self, msg=''):
        """Begin the timer for the node `Wall Time` calculation.

        Nodes store their own runtime, which is displayed in a tooltip when
        hovering over the node on the canvas (see :doc:`../ui`). Normally, each
        node reports the complete time it takes to run its :py:meth:`compute`
        function. However, a dev can use this method along with
        :py:meth:`starttime` to set the portion of :py:meth:`compute` to be
        used to calculate the `Wall Time`. This method also prints the `Wall
        Time` to stdout, along with an optional additional message, using
        :py:meth:`gpi.logger.PrintLogger.node`).

        Args:
            msg (string): a message to be sent to stdout (using
                :py:meth:`gpi.logger.PrintLogger.node`) along with the `Wall
                Time`
        """
        ttime = time.time() - self._starttime
        eline = inspect.currentframe().f_back.f_lineno
        log.node(self.node.getName()+' - '+str(ttime)+'sec, between lines:'+str(self._startline)+'-'+str(eline)+'. '+msg)

    def stringifyExecType(self):
        if self.execType() is GPI_PROCESS:
            return " [Process]"
        elif self.execType() is GPI_THREAD:
            return " [Thread]"
        else:
            return " [App-Loop]"

    def setStatus_sys(self, msg):
        msg += self.stringifyExecType()
        self._statusbar_sys.setText(msg)

    def setStatus(self, msg):
        self._statusbar_usr.setText(msg)

    def execType(self):
        # default executable type
        # return GPI_THREAD
        return GPI_PROCESS  # this is the safest
        # return GPI_APPLOOP

    def setReQueue(self, val=False):  # NODEAPI
        # At the end of a nodeQueue, these tasked are checked for
        # more events.
        if self.node.inDisabledState():
            return
        if self.node.nodeCompute_thread.execType() == GPI_PROCESS:
            self.node.nodeCompute_thread.addToQueue(['setReQueue', val])
        else:
            self.node._requeue = val

    def reQueueIsSet(self):
        return self.node._requeue

    def getLabel(self):
        return self.label

    def moduleExists(self, name):
        """Give the user a simple module checker for the node validate
        function.
        """
        try:
            imp.find_module(name)
        except ImportError:
            return False
        else:
            return True

    def moduleValidated(self, name):
        """Provide a stock error message in the event a c/ext module cannot
        be found.
        """
        if not self.moduleExists(name):
            log.error("The \'" + name + "\' module cannot be found, compute() aborted.")
            return 1
        return 0

    def setLabelWidget(self, newlabel=''):
        self.wdglabel.setText(newlabel)

    def setLabel(self, newlabel=''):
        self.label = str(newlabel)
        self.updateTitle()
        self.node.updateOutportPosition()
        self.node.graph.scene().update(self.node.boundingRect())
        self.node.update()

    def openNodeDocumentation(self):
        self.doc_text_win.show()

        # setting the size only works if we have shown the widget
        # set the width based on some ideal width (max at 800px)
        docwidth = self.doc_text_win.document().idealWidth()
        lmargin = self.doc_text_win.contentsMargins().left()
        rmargin = self.doc_text_win.contentsMargins().right()
        scrollbar_width = 20 # estimate, scrollbar overlaps content otherwise
        total_width = min(lmargin + docwidth + rmargin + scrollbar_width, 800)
        self.doc_text_win.setFixedWidth(total_width)

        # set the height based on the content size
        docheight= self.doc_text_win.document().size().height()
        self.doc_text_win.setMinimumHeight(min(docheight, 200))
        self.doc_text_win.setMaximumHeight(docheight)

    def setDetailLabel(self, newDetailLabel='', elideMode='middle'):
        """Set an additional label for the node.

        This offers a way to programmatically set an additional label for a
        node (referred to as the `detail label`), which shows up underneath the
        normal node tile and label (as set wihtin the node menu). This is used
        by the `core` library to show file paths for the file reader/writer
        nodes, for example.

        Args:
            newDetailLabel (string): The detail label for the node (e.g. file
                path, operator, ...)
            elideMode ({'middle', 'left', 'right', 'none'}, optional): Method
                to use when truncating the detail label with an ellipsis.
        """
        self._detailLabel = str(newDetailLabel)
        self._detailElideMode = elideMode
        self.node.updateOutportPosition()

    def getDetailLabel(self):
        """Get the current node detail label.

        Returns:
            string: The node detail label, as set by :py:meth:`setDetailLabel`
        """
        return self._detailLabel

    def getDetailLabelElideMode(self):
        """How the detail label should be elided if it's too long:"""
        mode = self._detailElideMode
        qt_mode = QtCore.Qt.ElideMiddle
        if mode == 'left':
            qt_mode = QtCore.Qt.ElideLeft
        elif mode == 'right':
            qt_mode = QtCore.Qt.ElideRight
        elif mode == 'none':
            qt_mode = QtCore.Qt.ElideNone
        else: # default, mode == 'middle'
            qt_mode = QtCore.Qt.ElideMiddle

        return qt_mode

    # to be subclassed and reimplemented.
    def initUI(self):
        """Initialize the node UI (Node Menu).

        This method is intended to be reimplemented by the external node
        developer. This is where :py:class:`Port` and :py:class:`Widget`
        objects are added and initialized. This method is called whenever a
        node is added to the canvas.

        See :ref:`adding-widgets` and :ref:`adding-ports` for more detail.
        """

        # window
        #self.setWindowTitle(self.node.name)

        # IO Ports
        #self.addInPort('in1', str, obligation=REQUIRED)
        #self.addOutPort('out2', int)
        pass

    def windowActivationChange(self, test):
        self.node.graph.scene().makeOnlyTheseNodesSelected([self.node])

    def getSettings(self):  # NODEAPI
        """Wrap up all settings from each widget."""
        s = {}
        s['label'] = self.label
        s['parms'] = []
        for parm in self.parmList:
            s['parms'].append(copy.deepcopy(parm.getSettings()))
        return s

    def loadSettings(self, s):
        self.setLabelWidget(s['label'])

        # modify node widgets
        for parm in s['parms']:
            # the NodeAPI has instantiated the widget by name, this will
            # change the wdg-ID, however, this step is only dependend on
            # unique widget names.

            if not self.getWidget(parm['name']):
                log.warn("Trying to load settings; can't find widget with name: \'" + \
                    stw(parm['name']) + "\', skipping...")
                continue

            log.debug('Setting widget: \'' + stw(parm['name']) + '\'')
            try:
                self.modifyWidget_direct(parm['name'], **parm['kwargs'])
            except:
                log.error('Failed to set widget: \'' + stw(parm['name']) + '\'\n' + str(traceback.format_exc()))

            if parm['kwargs']['inport']:  # widget-inports
                self.addWidgetInPortByName(parm['name'])
            if parm['kwargs']['outport']:  # widget-outports
                self.addWidgetOutPortByName(parm['name'])


    def generateHelpText(self):
        """Gather the __doc__ string of the ExternalNode derived class,
        all the set_ methods for each attached widget, and any attached
        GPI-types from each of the ports.
        """
        if self._docText is not None:
            return self._docText

        # NODE DOC
        node_doc = "NODE: \'" + self.node._moduleName + "\'\n" + "    " + \
            str(self.__doc__)

        # WIDGETS DOC
        # parm_doc = ""  # contains parameter info
        wdg_doc = "\n\nAPPENDIX A: (WIDGETS)\n"  # generic widget ref info
        for parm in self.parmList:  # wdg order matters
            wdg_doc += "\n  \'" + parm.getTitle() + "\': " + \
                str(parm.__class__) + "\n"
            numSpaces = 8
            set_doc = "\n".join((numSpaces * " ") + i for i in str(
                parm.__doc__).splitlines())
            wdg_doc += set_doc + "\n"
            # set methods
            for member in dir(parm):
                if member.startswith('set_'):
                    wdg_doc += (8 * " ") + member + inspect.formatargspec(
                        *inspect.getargspec(getattr(parm, member)))
                    set_doc = str(inspect.getdoc(getattr(parm, member)))
                    numSpaces = 16
                    set_doc = "\n".join((
                        numSpaces * " ") + i for i in set_doc.splitlines())
                    wdg_doc += "\n" + set_doc + "\n"

        # PORTS DOC
        port_doc = "\n\nAPPENDIX B: (PORTS)\n"  # get the port type info
        for port in self.node.getPorts():
            typ = port.GPIType()
            port_doc += "\n  \'" + port.portTitle + "\': " + \
                str(typ.__class__) + "|" + str(type(port)) + "\n"
            numSpaces = 8
            set_doc = "\n".join((numSpaces * " ") + i for i in str(
                typ.__doc__).splitlines())
            port_doc += set_doc + "\n"

            # set methods
            for member in dir(typ):
                if member.startswith('set_'):
                    port_doc += (8 * " ") + member + inspect.formatargspec(
                        *inspect.getargspec(getattr(typ, member)))
                    set_doc = str(inspect.getdoc(getattr(typ, member)))
                    numSpaces = 16
                    set_doc = "\n".join((
                        numSpaces * " ") + i for i in set_doc.splitlines())
                    port_doc += "\n" + set_doc + "\n"

        # GETTERS/SETTERS
        getset_doc = "\n\nAPPENDIX C: (GETTERS/SETTERS)\n\n"
        getset_doc += (8 * " ") + "Node Initialization Setters: (initUI())\n\n"
        getset_doc += self.formatFuncDoc(self.addWidget)
        getset_doc += self.formatFuncDoc(self.addInPort)
        getset_doc += self.formatFuncDoc(self.addOutPort)
        getset_doc += (
            8 * " ") + "Node Compute Getters/Setters: (compute())\n\n"
        getset_doc += self.formatFuncDoc(self.getVal)
        getset_doc += self.formatFuncDoc(self.getAttr)
        getset_doc += self.formatFuncDoc(self.setAttr)
        getset_doc += self.formatFuncDoc(self.getData)
        getset_doc += self.formatFuncDoc(self.setData)

        self._docText = node_doc  # + wdg_doc + port_doc + getset_doc

        self.doc_text_win.setPlainText(self._docText)

        return self._docText

    def formatFuncDoc(self, func):
        """Generate auto-doc for passed func obj."""
        numSpaces = 24
        fdoc = inspect.getdoc(func)
        set_doc = "\n".join((
            numSpaces * " ") + i for i in str(fdoc).splitlines())
        rdoc = (16 * " ") + func.__name__ + \
            inspect.formatargspec(*inspect.getargspec(func)) \
            + "\n" + set_doc + "\n\n"
        return rdoc

    def printWidgetValues(self):
        # for debugging
        for parm in self.parmList:
            log.debug("widget: " + str(parm))
            log.debug("value: " + str(parm.get_val()))

    # abstracting IF for user
    def addInPort(self, title=None, type=None, obligation=REQUIRED,
                  menuWidget=None, cyclic=False, **kwargs):
        """Add an input port to the node.

        Input ports collect data from other nodes for use/processing within a
        node compute function. Ports may only be added in the :py:meth:`initUI`
        routine. Data at an input node can be accessed using
        :py:meth:`getData`, but is typically read-only.

        Args:
            title (str): port title (shown in tooltips) and unique identifier
            type (str): class name of extended type (e.g. ``np.complex64``)
            obligation: ``gpi.REQUIRED`` (default) or ``gpi.OPTIONAL``
            menuWidget: `for internal use`, devs should leave as default
                ``None``
            cyclic (bool): whether the port should allow reverse-flow from
                downstream nodes (default is ``False``)
            kwargs: any set_<arg> method belonging to the ``GPIDefaultType``
                derived class
        """
        self.node.addInPort(title, type, obligation, menuWidget, cyclic, **kwargs)
        self.node.update()

    # abstracting IF for user
    def addOutPort(self, title=None, type=None, obligation=REQUIRED,
                   menuWidget=None, **kwargs):
        """Add an output port to the node.

        Output nodes provide a conduit for passing data to downstream nodes.
        Ports may only be added in the :py:meth:`initUI` routine.  Data at an
        output port can be accessed using :py:meth:`setData` and
        :py:meth:`getData` from within :py:meth:`validate` and
        :py:meth:`compute`.

        Args:
            title (str): port title (shown in tooltips) and unique identifier
            type (str): class name of extended type (e.g. ``np.float32``)
            obligation: ``gpi.REQUIRED`` (default) or ``gpi.OPTIONAL``
            menuWidget: `for internal use`, debs should leave as default
                ``None``
            kwargs: any set_<arg> method belonging to the ``GPIDefaultType``
                derived class
        """
        self.node.addOutPort(title, type, obligation, menuWidget, **kwargs)
        self.node.update()

    def addWidgetInPortByName(self, title):
        wdg = self.findWidgetByName(title)
        self.addWidgetInPort(wdg)

    def addWidgetInPortByID(self, wdgID):
        wdg = self.findWidgetByID(wdgID)
        self.addWidgetInPort(wdg)

    def addWidgetInPort(self, wdg):
        self.addInPort(title=wdg.getTitle(), type=wdg.getDataType(),
                       obligation=OPTIONAL, menuWidget=wdg)

    def removeWidgetInPort(self, wdg):
        port = self.findWidgetInPortByName(wdg.getTitle())
        self.node.removePortByRef(port)

    def addWidgetOutPortByID(self, wdgID):
        wdg = self.findWidgetByID(wdgID)
        self.addWidgetOutPort(wdg)

    def addWidgetOutPortByName(self, title):
        wdg = self.findWidgetByName(title)
        self.addWidgetOutPort(wdg)

    def addWidgetOutPort(self, wdg):
        self.addOutPort(
            title=wdg.getTitle(), type=wdg.getDataType(), menuWidget=wdg)

    def removeWidgetOutPort(self, wdg):
        port = self.findWidgetOutPortByName(wdg.getTitle())
        self.node.removePortByRef(port)

    def addWidget(self, wdg=None, title=None, **kwargs):
        """Add a widget to the node UI.

        Args:
            wdg (str): The widget class name (see :doc:`widgets` for a list of
                built-in widget classes)
            title (str): A unique name for the widget, and title shown in the
                Node Menu
            kwargs: Additional arguments passed to the set_<arg> methods
                specific to the chosen widget class
        """

        if (wdg is None) or (title is None):
            log.critical("addWidget(): widgets need a title" \
                + " AND a wdg-str! Aborting.")
            return

        # check existence first
        if self.node.titleExists(title):
            log.critical("addWidget(): Widget title \'" + str(title) \
                + "\' is already in use! Aborting.")
            return

        ypos = len(self.parmList)

        # try widget def's packaged with node def first
        wdgGroup = None

        # first see if the node code contains the widget def
        wdgGroup = self.node.item.getWidget(wdg)

        # get widget from standard gpi widgets
        if wdgGroup is None:
            if hasattr(BUILTIN_WIDGETS, wdg):
                wdgGroup = getattr(BUILTIN_WIDGETS, wdg)

        # if its still not found then its a big deal
        if wdgGroup is None:
            log.critical("\'" + wdg + "\' widget not found.")
            raise Exception("Widget not found.")

        # instantiate if not None
        else:
            wdgGroup = wdgGroup(title)

        wdgGroup.setNodeName(self.node.getModuleName())
        wdgGroup._setNodeLabel(self.label)

        wdgGroup.valueChanged.connect(lambda: self.wdgEvent(title))
        wdgGroup.portStateChange.connect(lambda: self.changePortStatus(title))
        wdgGroup.returnWidgetToOrigin.connect(self.returnWidgetToNodeMenu)
        self.wdglabel.textChanged.connect(wdgGroup._setNodeLabel)

        # add to menu layout
        self.layout.addWidget(wdgGroup, ypos, 0)
        self.parmList.append(wdgGroup)
        self.parmDict[title] = wdgGroup  # the new way

        self.modifyWidget_direct(title, **kwargs)

    def returnWidgetToNodeMenu(self, wdgid):
        # find widget by id
        wdgid = int(wdgid)
        ind = 0
        for parm in self.parmList:
            if wdgid == parm.get_id():
                self.layout.addWidget(parm, ind, 0)
                if self.node.isMarkedForDeletion():
                    parm.hide()
                else:
                    parm.show()
                break
            ind += 1

    def blockWdgSignals(self, val):
        """Block all signals, especially valueChanged."""
        for parm in self.parmList:
            parm.blockSignals(val)

    def blockSignals_byWdg(self, title, val):
        # get the over-reporting widget by name and block it
        self.parmDict[title].blockSignals(val)

    def changePortStatus(self, title):
        """Add a new in- or out-port tied to this widget."""
        log.debug("changePortStatus: " + str(title))
        wdg = self.findWidgetByName(title)

        # make sure the port is either added or will be added.
        if wdg.inPort_ON:
            if self.findWidgetInPortByName(title) is None:
                self.addWidgetInPort(wdg)
        else:
            if self.findWidgetInPortByName(title):
                self.removeWidgetInPort(wdg)
        if wdg.outPort_ON:
            if self.findWidgetOutPortByName(title) is None:
                self.addWidgetOutPort(wdg)
        else:
            if self.findWidgetOutPortByName(title):
                self.removeWidgetOutPort(wdg)

    def findWidgetByName(self, title):
        for parm in self.parmList:
            if parm.getTitle() == title:
                return parm

    def findWidgetByID(self, wdgID):
        for parm in self.parmList:
            if parm.id() == wdgID:
                return parm

    def findWidgetInPortByName(self, title):
        for port in self.node.inportList:
            if port.isWidgetPort():
                if port.portTitle == title:
                    return port

    def findWidgetOutPortByName(self, title):
        for port in self.node.outportList:
            if port.isWidgetPort():
                if port.portTitle == title:
                    return port

    def modifyWidget_setter(self, src, kw, val):
        sfunc = "set_" + kw
        if hasattr(src, sfunc):
            func = getattr(src, sfunc)
            func(val)
        else:
            try:
                ttl = src.getTitle()
            except:
                ttl = str(src)

            log.critical("modifyWidget_setter(): Widget \'" + stw(ttl) \
                + "\' doesn't have attr \'" + stw(sfunc) + "\'.")

    def modifyWidget_direct(self, pnumORtitle, **kwargs):
        src = self.getWidget(pnumORtitle)

        for k, v in list(kwargs.items()):
            if k != 'val':
                self.modifyWidget_setter(src, k, v)

        # set 'val' last so that bounds don't cause a temporary conflict.
        if 'val' in kwargs:
            self.modifyWidget_setter(src, 'val', kwargs['val'])

    def modifyWidget_buffer(self, title, **kwargs):
        """GPI_PROCESSes have to use buffered widget attributes to effect the
        same changes to attributes during compute() as with GPI_THREAD or
        GPI_APPLOOP.
        """
        src = self.getWdgFromBuffer(title)

        try:
            for k, v in list(kwargs.items()):
                src['kwargs'][k] = v
        except:
            log.critical("modifyWidget_buffer() FAILED to modify buffered attribute")


    def lockWidgetUpdates(self):
        self._widgetUpdateMutex_locked = True

    def unlockWidgetUpdates(self):
        self._widgetUpdateMutex_locked = False

    def widgetsUpdatesLocked(self):
        return self._widgetUpdateMutex_locked

    def wdgEvent(self, title):
        # Captures all valueChanged events from widgets.
        # 'title' is for interrogating who changed in compute().

        # Once the event status has been set, disable valueChanged signals
        # until the node has successfully completed.
        # -this was b/c sliders etc. were causing too many signals resulting
        # in a recursion overload to this function.
        #self.blockWdgSignals(True)
        self.blockSignals_byWdg(title, True)

        if self.node.hasEventPending():
            self.node.appendEvent({GPI_WIDGET_EVENT: title})
            return
        else:
            self.node.setEventStatus({GPI_WIDGET_EVENT: title})

        # Can start event from any applicable 'check' transition
        if self.node.graph.inIdleState():
            self.node.graph._switchSig.emit('check')

    # for re-drawing the menu title to match module/node instance
    def updateTitle(self):
        # Why is this trying the scrollArea? isn't it always a scroll???
        if self.label == '':
            try:
                self.node._nodeIF_scrollArea.setWindowTitle(self.node.name)
            except:
                self.setWindowTitle(self.node.name)
        else:
            try:
                augtitle = self.node.name + ": " + self.label
                self.node._nodeIF_scrollArea.setWindowTitle(augtitle)
            except:
                augtitle = self.node.name + ": " + self.label
                self.setWindowTitle(augtitle)

    def setTitle(self, title):
        self.node.name = title
        self.updateTitle()

    # Queue actions for widgets and ports
    def setAttr(self, title, **kwargs):
        """Set specific attributes of a given widget.

        This method may be used to set attributes of any widget during any of
        the core node functions: :py:meth:`initUI`, :py:meth:`validate`, or
        :py:meth:`compute`.

        Args:
            title (str): the widget name (unique identifier)
            kwargs: args corresponding to the ``get_<arg>`` methods of the
                widget class. See :doc:`widgets` for the list of built-in
                widgets and associated attributes.
        """
        try:
            # start = time.time()
            # either emit a signal or save a queue
            if self.node.inDisabledState():
                return
            if self.node.nodeCompute_thread.execType() == GPI_PROCESS:
                # PROCESS
                self.node.nodeCompute_thread.addToQueue(['modifyWdg', title, kwargs])
                #self.modifyWidget_buffer(title, **kwargs)
            elif self.node.nodeCompute_thread.execType() == GPI_THREAD:
                # THREAD
                # can't modify QObjects in thread, but we can send a signal to do
                # so
                self.modifyWdg.emit(title, kwargs)
            else:
                # APPLOOP
                self.modifyWidget_direct(str(title), **kwargs)

        except:
            raise GPIError_nodeAPI_setAttr('self.setAttr(\''+stw(title)+'\',...) failed in the node definition, check the widget name, attribute name and attribute type().')

        # log.debug("modifyWdg(): time: "+str(time.time() - start)+" sec")

    def allocArray(self, shape=(1,), dtype=np.float32, name='local'):
        """return a shared memory array if the node is run as a process.
            -the array name needs to be unique
        """
        if self.node.nodeCompute_thread.execType() == GPI_PROCESS:
            buf, shd = DataProxy()._genNDArrayMemmap(shape, dtype, self.node.getID(), name)

            if shd is not None:
                # saving the reference id allows the node developer to decide
                # on the fly if the preallocated array will be used in the final
                # setData() call.
                self.shdmDict[str(id(buf))] = shd.filename

            return buf
        else:
            return np.ndarray(shape, dtype=dtype)

    def setData(self, title, data):
        """Set the data at an :py:class:`OutPort`.

        This is typically called in :py:meth:`compute` to set data at an output
        port, making the data available to downstream nodes.
        :py:class:`InPort` ports are read-only, so this method should only be used
        with :py:class:`OutPort` ports.

        Args:
            title (str): name of the port to send the object reference
            data: any object corresponding to a ``GPIType`` class allowed by
                this port
        """
        try:
            # start = time.time()
            # either set directly or save a queue
            if self.node.inDisabledState():
                return
            if self.node.nodeCompute_thread.execType() == GPI_PROCESS:

                #  numpy arrays
                if type(data) is np.memmap or type(data) is np.ndarray:
                    if str(id(data)) in self.shdmDict: # pre-alloc
                        s = DataProxy().NDArray(data, shdf=self.shdmDict[str(id(data))], nodeID=self.node.getID(), portname=title)
                    else:
                        s = DataProxy().NDArray(data, nodeID=self.node.getID(), portname=title)

                    # for split objects to pass thru individually
                    # this will be a list of DataProxy objects
                    if type(s) is list:
                        for i in s:
                            self.node.nodeCompute_thread.addToQueue(['setData', title, i])
                    # a single DataProxy object
                    else:
                        self.node.nodeCompute_thread.addToQueue(['setData', title, s])

                # all other non-numpy data that are pickleable
                else:
                    # PROCESS output other than numpy
                    self.node.nodeCompute_thread.addToQueue(['setData', title, data])
            else:
                # THREAD or APPLOOP
                self.node.setData(title, data)
                # log.debug("setData(): time: "+str(time.time() - start)+" sec")

        except:
            print((str(traceback.format_exc())))
            raise GPIError_nodeAPI_setData('self.setData(\''+stw(title)+'\',...) failed in the node definition, check the output name and data type().')

    def getData(self, title):
        """Get the data from a :py:class:`Port` for this node.

        Usually this is used to get input data from a :py:class:`InPort`,
        though in some circumstances (e.g. in the `Glue` node) it may be used
        to get data from an :py:class:`OutPort`. This method is available for
        devs to use in :py:meth:`validate` and :py:meth:`compute`.

        Args:
            title (str): the name of the GPI :py:class:`Port` object
        Returns:
            Data from the :py:class:`Port` object. The return will have a type
            corresponding to a ``GPIType`` class allowed by this port.
        """
        try:
            port = self.node.getPortByNumOrTitle(title)
            if isinstance(port, InPort):
                data = port.getUpstreamData()
                if type(data) is np.ndarray:
                    # don't allow users to change original array attributes
                    # that aren't protected by the 'writeable' flag
                    buf = np.frombuffer(data.data, dtype=data.dtype)
                    buf.shape = tuple(data.shape)
                    return buf
                else:
                    return data

            elif isinstance(port, OutPort):
                return port.data
            else:
                raise Exception("getData", "Invalid Port Title")
        except:
            raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition check the port name.')

    def getInPort(self, pnumORtitle):
        return self.node.getInPort(pnumORtitle)

    def getOutPort(self, pnumORtitle):
        return self.node.getOutPort(pnumORtitle)

############### DEPRECATED NODE API
# TTD v0.3

    def getAttr_fromWdg(self, title, attr):
        """title = (str) wdg-class name
        attr = (str) corresponds to the get_<arg> of the desired attribute.
        """
        log.warn('The \'getAttr_fromWdg()\' function is deprecated, use \'getAttr()\' instead.  '+str(self.node.getFullPath()))
        return self.getAttr(title, attr)

    def getVal_fromParm(self, title):
        """Returns get_val() from wdg-class (see getAttr()).
        """
        log.warn('The \'getVal_fromParm()\' function is deprecated, use \'getVal()\' instead.  '+str(self.node.getFullPath()))
        return self.getVal(title)

    def getData_fromPort(self, title):
        """title = (str) the name of the InPort.
        """
        log.warn('The \'getData_fromPort()\' function is deprecated, use \'getData()\' instead.  '+str(self.node.getFullPath()))
        return self.getData(title)

    def setData_ofPort(self, title, data):
        """title = (str) name of the OutPort to send the object reference.
        data = (object) any object corresponding to a GPIType class.
        """
        log.warn('The \'setData_ofPort()\' function is deprecated, use \'setData()\' instead.  '+str(self.node.getFullPath()))
        self.setData(title, data)

    def modifyWidget(self, title, **kwargs):
        """title = (str) the corresponding widget name.
        kwargs = args corresponding to the get_<arg> methods of the wdg-class.
        """
        log.warn('The \'modifyWidget()\' function is deprecated, use \'setAttr()\' instead.  '+str(self.node.getFullPath()))
        self.setAttr(title, **kwargs)

    def getEvent(self):
        """Allow node developer to get information about what event has caused
        the node to run."""
        log.warn('The \'getEvent()\' function is deprecated, use \'getEvents()\' (its the plural form). '+str(self.node.getFullPath()))
        return self.node.getPendingEvent()

    def portEvent(self):
        """Specifically check for a port event."""
        log.warn('The \'portEvent()\' function is deprecated, use \'portEvents()\' (its the plural form). '+str(self.node.getFullPath()))
        if GPI_PORT_EVENT in self.getEvent():
            return self.getEvent()[GPI_PORT_EVENT]
        return None

    def widgetEvent(self):
        """Specifically check for a wdg event."""
        log.warn('The \'widgetEvent()\' function is deprecated, use \'widgetEvents()\' (its the plural form). '+str(self.node.getFullPath()))
        if GPI_WIDGET_EVENT in self.getEvent():
            return self.getEvent()[GPI_WIDGET_EVENT]
        return None
############### DEPRECATED NODE API

    def getEvents(self):
        """Get information about events that caused the node to run.

        Returns a dictionary containing names of widgets and ports that have
        changed values since the last time the node ran. Additionally contains
        information regarding ``init`` or ``requeue`` events trigered by GPI's
        node-evaluation routines.

        `Note: events from widget-ports count as both widget and port events.`

        Returns:
            dict: all events accumulated since the node was last run

                The event dictionary contains four key:value pairs:
                    * ``GPI_WIDGET_EVENT`` : `set(widget_titles (string)`)
                    * ``GPI_PORT_EVENT`` : `set(port_titles (string)`)
                    * ``GPI_INIT_EVENT`` : ``True`` or ``False``
                    * ``GPI_REQUEUE_EVENT`` : ``True`` or ``False``
        """
        return self.node.getPendingEvents().events

    def portEvents(self):
        """Specifically check for port events.

        Get the names (unique identifier strings) of any ports that have
        changed data since the last run.

        `Note: events from widget-ports count as both widget and port events.`

        Returns:
            set: names (strings) of all ports modified since the node last ran
        """
        return self.node.getPendingEvents().port

    def widgetEvents(self):
        """Specifically check for a widget events.

        Get the names (unique identifier strings) of any widgets that have
        changed data since the last run.

        `Note: events from widget-ports count as both widget and port events.`

        Returns:
            set: names (strings) of all widgets modified since the node last
                ran
        """
        return self.node.getPendingEvents().widget

    def widgetMovingEvent(self, wdgid):
        """Called when a widget drag is being initiated.
        """
        pass

    def getWidgetByID(self, wdgID):
        for parm in self.parmList:
            if parm.id() == wdgID:
                return parm
        log.critical("getWidgetByID(): Cannot find widget id:" + str(wdgID))

    def getWidget(self, pnum):
        """Returns the widget desc handle and position number"""
        # fetch by widget number
        if type(pnum) is int:
            if (pnum < 0) or (pnum >= len(self.parmList)):
                log.error("getWidget(): Target widget out of range: " + str(pnum))
                return
            src = self.parmList[pnum]
        # fetch by widget title
        elif type(pnum) is str:
            src = None
            cnt = 0
            for parm in self.parmList:
                if parm.getTitle() == pnum:
                    src = parm
                    pnum = cnt  # change pnum back to int
                cnt += 1
            if src is None:
                log.error("getWidget(): Failed to find widget: \'" + stw(pnum) + "\'")
                return
        else:
            log.error("getWidget(): Widget identifier must be" + " either int or str")
            return
        return src

    def bufferParmSettings(self):
        """Get list of parms (dict) in self.parmSettings['parms'].
        Called by GPI_PROCESS functor to capture all widget settings needed
        in compute().
        """
        self.parmSettings = self.getSettings()

    def getWdgFromBuffer(self, title):
        # find a specific widget by title
        for wdg in self.parmSettings['parms']:
            if 'name' in wdg:
                if wdg['name'] == title:
                    return wdg


    def getVal(self, title):
        """Returns the widget value.

        Each widget class has a corresponding "main" value. This method will
        return the value of the widget, by passing along the return from its
        `get_val()` method.

        Returns:
            The widget value. The type of the widget value is defined by the
            widget class. See :doc:`widgets` for value types for the built-in
            widget classes.
        """
        try:
            # Fetch widget value by title
            if self.node.inDisabledState():
                return

            if self.node.nodeCompute_thread.execType() == GPI_PROCESS:
                return self.getAttr(title, 'val')

            # threads and main loop can access directly
            return self.getAttr(title, 'val')

        except:
            print(str(traceback.format_exc()))
            raise GPIError_nodeAPI_getVal('self.getVal(\''+stw(title)+'\') failed in the node definition, check the widget name.')

    def getAttr(self, title, attr):
        """Get a specific attribute value from a widget.

        This returns the value of a specific attribute of a widget. Widget
        attributes may be modified by the user manipulating the Node Menu,
        during widget creation using the `kwargs` in :py:meth:`addWidget`, or
        programmatically by :py:meth:`setAttr`.

        Args:
            title (str): The widget name (unique identifier)
            attr (str): The desired attribute
        Returns:
            The desired widget attribute. This value is retrieved by calling
            ``get_<attr>`` on the indicated widget. See :doc:`widgets` for a
            list of attributes for the buil-in widget classes.
        """
        try:
            # Fetch widget value by title
            if self.node.inDisabledState():
                return

            if self.node.nodeCompute_thread.execType() == GPI_PROCESS:
                wdg = self.getWdgFromBuffer(title)
                return self._getAttr_fromWdg(wdg, attr)

            # threads and main loop can access directly
            wdg = self.getWidget(title)
            return self._getAttr_fromWdg(wdg, attr)

        except:
            print(str(traceback.format_exc()))
            raise GPIError_nodeAPI_getAttr('self.getAttr(\''+stw(title)+'\',...) failed in the node definition, check widget name and attribute name.')

    def _getAttr_fromWdg(self, wdg, attr):
        try:
            # input is either a dict or a wdg instance.
            if isinstance(wdg, dict):  # buffered values
                if attr in wdg['kwargs']:
                    return wdg['kwargs'][attr]
                else:
                    # build error msg
                    title = wdg['name']
                    funame = attr
            else:  # direct widget access
                funame = 'get_' + attr
                if hasattr(wdg, funame):
                    return getattr(wdg, funame)()
                else:
                    try:
                        title = wdg.getTitle()
                    except:
                        title = "\'no name\'"
            log.critical("_getAttr(): widget \'" + stw(title) + "\' has no attr \'" + stw(funame) + "\'.")
            #return None
            raise GPIError_nodeAPI_getAttr('_getAttr() failed for widget \''+stw(title)+'\'')
        except:
            #log.critical("_getAttr_fromWdg(): Likely the wrong input arg type.")
            #raise
            print(str(traceback.format_exc()))
            raise GPIError_nodeAPI_getAttr('_getAttr() failed for widget \''+stw(title)+'\'')

    def validate(self):
        """The pre-compute validation step.

        This function is intended to be reimplemented by the external node
        developer. Here the developer can access widget and port data (see
        :ref:`accessing-widgets` and :ref:`accessing-ports`) to perform
        validation checks before :py:meth:`compute` is called.

        Returns:
            An integer corresponding to the result of the validation:
                0: The node successfully passed validation

                1: The node failed validation, compute will not be called and
                the canvas will be paused
        """
        log.debug("Default module validate().")
        return 0

    def compute(self):
        """The module compute routine.

        This function is intended to be reimplemented by the external node
        developer. This is where the main computation of the node is performed.
        The developer has full access to the widget and port data (see
        :ref:`accessing-widgets` and :ref:`accessing-ports`).

        Returns:
            An integer corresponding to the result of the computation:
                0: Compute completed successfully

                1: Compute failed in some way, the canvas will be paused
        """
        log.debug("Default module compute().")
        return 0

    def post_compute_widget_update(self):
        # reset any widget that requires it (i.e. PushButton)
        for parm in self.parmList:
            if hasattr(parm, 'set_reset'):
                parm.set_reset()