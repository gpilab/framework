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
#    MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
#    SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.


import os
import imp
import time
import copy
import inspect
import tempfile
import traceback
from multiprocessing import sharedctypes # numpy xfer

# gpi
import gpi
from gpi import QtCore, QtGui
from .defines import ExternalNodeType, GPI_PROCESS, GPI_THREAD, stw, GPI_SHDM_PATH
from .defines import GPI_WIDGET_EVENT, REQUIRED, OPTIONAL, GPI_PORT_EVENT
from .functor import NumpyProxyDesc
from .logger import manager
from .port import InPort, OutPort
from .widgets import HidableGroupBox
import widgets as BUILTIN_WIDGETS
import syntax


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


class NodeAPI(QtGui.QWidget):
    '''This is the class that all external modules must implement.'''
    GPIExtNodeType = ExternalNodeType  # ensures the subclass is of THIS class
    modifyWdg = gpi.Signal(str, dict)

    def __init__(self, node):
        super(NodeAPI, self).__init__()

        #self.setToolTip("Double Click to Show/Hide each Widget")
        self.node = node

        self.label = ''
        self._docText = None
        self.parmList = []  # deprecated, since dicts have direct name lookup
        self.parmDict = {}  # mirror parmList for now
        self.parmSettings = {}  # for buffering wdg parms before copying to a PROCESS
        self.shdmDict = {} # for storing base addresses

        # grid for module widgets
        self.layout = QtGui.QGridLayout()

        # this must exist before user-widgets are added so that they can get
        # node label updates
        self.wdglabel = QtGui.QLineEdit(self.label)

        # allow logger to be used in initUI()
        self.log = manager.getLogger(node.getModuleName())

        try:
            self._initUI_ret = self.initUI()
        except:
            log.error('initUI() failed. '+str(node.item.fullpath)+'\n'+str(traceback.format_exc()))
            self._initUI_ret = -1  # error

        # make a label box with the unique id
        labelGroup = HidableGroupBox("Node Label")
        labelLayout = QtGui.QGridLayout()
        self.wdglabel.textChanged.connect(self.setLabel)
        labelLayout.addWidget(self.wdglabel, 0, 1)
        labelGroup.setLayout(labelLayout)
        self.layout.addWidget(labelGroup, len(self.parmList) + 1, 0)
        labelGroup.set_collapsed(True)
        labelGroup.setToolTip("Displays the Label on the Canvas (Double Click)")

        # make a label box with the unique id
        self.aboutGroup = HidableGroupBox("About")
        aboutLayout = QtGui.QGridLayout()
        self.wdgabout = QtGui.QTextEdit()
        self.wdgabout.setTabStopWidth(16)
        self._highlighter = syntax.PythonHighlighter(self.wdgabout.document())
        self.wdgabout.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.aboutGroup.setToolTip("Node Documentation (docstring + autodocs, Double Click)")

        aboutLayout.addWidget(self.wdgabout, 0, 1)
        self.aboutGroup.setLayout(aboutLayout)
        self.layout.addWidget(self.aboutGroup, len(self.parmList) + 2, 0)
        self.aboutGroup.set_collapsed(True)
        self.aboutGroup.collapseChanged.connect(self.generateHelpText)

        hbox = QtGui.QHBoxLayout()
        self._statusbar_sys = QtGui.QLabel('')
        self._statusbar_usr = QtGui.QLabel('')
        hbox.addWidget(self._statusbar_sys)
        hbox.addWidget(self._statusbar_usr, 0, (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter))

        # window resize grip
        self._grip = QtGui.QSizeGrip(self)
        hbox.addWidget(self._grip)

        self.layout.addLayout(hbox, len(self.parmList) + 3, 0)
        self.layout.setRowStretch(len(self.parmList) + 3, 0)

        # uid display
        # uid   = QtGui.QLabel("uid: "+str(self.node.getID()))
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
        return self.parmDict.keys()

    def starttime(self):
        self._startline = inspect.currentframe().f_back.f_lineno
        self._starttime = time.time()

    def endtime(self, msg=''):
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
        '''Give the user a simple module checker for the node validate
        function.
        '''
        try:
            imp.find_module(name)
        except ImportError:
            return False
        else:
            return True

    def moduleValidated(self, name):
        '''Provide a stock error message in the event a c/ext module cannot
        be found.
        '''
        if not self.moduleExists(name):
            log.error("The \'" + name + "\' module cannot be found, compute() aborted.")
            return 1
        return 0

    def setLabelWidget(self, newlabel=''):
        self.wdglabel.setText(newlabel)

    def setLabel(self, newlabel=''):
        self.label = str(newlabel)
        self.updateTitle()
        self.node.graph.scene().update(self.node.boundingRect())
        self.node.update()

    # to be subclassed and reimplemented.
    def initUI(self):

        # window
        #self.setWindowTitle(self.node.name)

        # IO Ports
        #self.addInPort('in1', str, obligation=REQUIRED)
        #self.addOutPort('out2', int)
        pass

    def windowActivationChange(self, test):
        self.node.graph.scene().makeOnlyTheseNodesSelected([self.node])

    def getSettings(self):  # NODEAPI
        '''Wrap up all settings from each widget.'''
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

        self.wdgabout.setPlainText(self._docText)

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
        """title = (str) port-title shown in tooltips
        type = (str) class name of extended type
        obligation = gpi.REQUIRED or gpi.OPTIONAL (default REQUIRED)
        menuWidget = INTERNAL USE
        kwargs = any set_<arg> method belonging to the
                    GPIDefaultType derived class.
        """
        self.node.addInPort(title, type, obligation, menuWidget, cyclic, **kwargs)
        self.node.update()

    # abstracting IF for user
    def addOutPort(self, title=None, type=None, obligation=REQUIRED,
                   menuWidget=None, **kwargs):
        """title = (str) port-title shown in tooltips
        type = (str) class name of extended type
        obligation = dummy parm to match function footprint
        menuWidget = INTERNAL USE
        kwargs = any set_<arg> method belonging to the
                    GPIDefaultType derived class.
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
        """wdg = (str) corresponds to the widget class name
        title = (str) is the string label given in the node-menu
        kwargs = corresponds to the set_<arg> methods specific
                    to the chosen wdg-class.
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
        wdgGroup.setNodeLabel(self.label)

        wdgGroup.valueChanged.connect(lambda: self.wdgEvent(title))
        wdgGroup.portStateChange.connect(lambda: self.changePortStatus(title))
        wdgGroup.returnWidgetToOrigin.connect(self.returnWidgetToNodeMenu)
        self.wdglabel.textChanged.connect(wdgGroup.setNodeLabel)

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
        '''Block all signals, especially valueChanged.'''
        for parm in self.parmList:
            parm.blockSignals(val)

    def blockSignals_byWdg(self, title, val):
        # get the over-reporting widget by name and block it
        self.parmDict[title].blockSignals(val)

    def changePortStatus(self, title):
        '''Add a new in- or out-port tied to this widget.'''
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

        for k, v in kwargs.iteritems():
            if k != 'val':
                self.modifyWidget_setter(src, k, v)

        # set 'val' last so that bounds don't cause a temporary conflict.
        if 'val' in kwargs:
            self.modifyWidget_setter(src, 'val', kwargs['val'])

    def modifyWidget_buffer(self, title, **kwargs):
        '''GPI_PROCESSes have to use buffered widget attributes to effect the
        same changes to attributes during compute() as with GPI_THREAD or
        GPI_APPLOOP.
        '''
        src = self.getWdgFromBuffer(title)

        try:
            for k, v in kwargs.iteritems():
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
        """title = (str) the corresponding widget name.
        kwargs = args corresponding to the get_<arg> methods of the wdg-class.
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

    def getSHMF(self, name='local'):
        '''return a unique shared mem handle for this gpi instance, node and port.
        '''
        return os.path.join(GPI_SHDM_PATH, str(name)+'_'+str(self.node.getID()))

    def allocArray(self, name='local', shape=(1,), dtype=np.float32):
        '''return a shared memory array if the node is run as a process.
            -the array name needs to be unique
        '''
        if self.node.nodeCompute_thread.execType() == GPI_PROCESS:
            fn = self.getSHMF(name)
            shd = np.memmap(fn, dtype=dtype, mode='w+', shape=tuple(shape))
            buf = np.frombuffer(shd.data, dtype=shd.dtype)
            buf.shape = shd.shape
            self.shdmDict[str(id(buf))] = shd.filename
            return buf
        else:
            return np.ndarray(shape, dtype=dtype)

    def setData(self, title, data):
        """title = (str) name of the OutPort to send the object reference.
        data = (object) any object corresponding to a GPIType class.
        """
        try:
            # start = time.time()
            # either set directly or save a queue
            if self.node.inDisabledState():
                return
            if self.node.nodeCompute_thread.execType() == GPI_PROCESS:

                # if the user creates a memmapped numpy w/o using allocArray()
                if type(data) is np.memmap:               
                    s = NumpyProxyDesc()
                    s['shape'] = tuple(data.shape)
                    s['shdf'] = data.filename
                    s['dtype'] = data.dtype
                    self.node.nodeCompute_thread.addToQueue(['setData', title, s])
 
                # if the user is using an ndarray interface directly
                elif type(data) is np.ndarray:

                    # if the user creates a memmapped numpy using allocArray()
                    if str(id(data)) in self.shdmDict:
                        s = NumpyProxyDesc()
                        s['shape'] = tuple(data.shape)
                        s['shdf'] = self.shdmDict[str(id(data))]
                        s['dtype'] = data.dtype
                        self.node.nodeCompute_thread.addToQueue(['setData', title, s])

                    # if the user doesn't generate a memmapped array ahead of
                    # setData().
                    else:
                        s = NumpyProxyDesc()
                        s['shape'] = tuple(data.shape)
                        s['dtype'] = data.dtype
                        s['shdf'] = self.getSHMF(title)
                        fp = np.memmap(s['shdf'], dtype=data.dtype, mode='w+', shape=s['shape'])
                        fp[:] = data[:] # full copy
                        self.node.nodeCompute_thread.addToQueue(['setData', title, s])

                # all other non-numpy data that is pickleable
                else:
                    # PROCESS output other than numpy
                    self.node.nodeCompute_thread.addToQueue(['setData', title, data])
            else:
                # THREAD or APPLOOP
                self.node.setData(title, data)
                # log.debug("setData(): time: "+str(time.time() - start)+" sec")

        except:
            #print str(traceback.format_exc())
            raise GPIError_nodeAPI_setData('self.setData(\''+stw(title)+'\',...) failed in the node definition, check the output name and data type().')

    def getData(self, title):
        """title = (str) the name of the InPort.
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
        '''Allow node developer to get information about what event has caused
        the node to run.'''
        log.warn('The \'getEvent()\' function is deprecated, use \'getEvents()\' (its the plural form). '+str(self.node.getFullPath()))
        return self.node.getPendingEvent()

    def portEvent(self):
        '''Specifically check for a port event.'''
        log.warn('The \'portEvent()\' function is deprecated, use \'portEvents()\' (its the plural form). '+str(self.node.getFullPath()))
        if self.getEvent().has_key(GPI_PORT_EVENT):
            return self.getEvent()[GPI_PORT_EVENT]
        return None

    def widgetEvent(self):
        '''Specifically check for a wdg event.'''
        log.warn('The \'widgetEvent()\' function is deprecated, use \'widgetEvents()\' (its the plural form). '+str(self.node.getFullPath()))
        if self.getEvent().has_key(GPI_WIDGET_EVENT):
            return self.getEvent()[GPI_WIDGET_EVENT]
        return None
############### DEPRECATED NODE API

    def getEvents(self):
        '''Allow node developer to get information about what event has caused
        the node to run.'''
        return self.node.getPendingEvents().events
    
    def portEvents(self):
        '''Specifically check for a port event.  Widget-ports count as both.'''
        return self.node.getPendingEvents().port

    def widgetEvents(self):
        '''Specifically check for a wdg event.'''
        return self.node.getPendingEvents().widget

    def widgetMovingEvent(self, wdgid):
        '''Called when a widget drag is being initiated.
        '''
        pass

    def getWidgetByID(self, wdgID):
        for parm in self.parmList:
            if parm.id() == wdgID:
                return parm
        log.critical("getWidgetByID(): Cannot find widget id:" + str(wdgID))

    def getWidget(self, pnum):
        '''Returns the widget desc handle and position number'''
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
        '''Get list of parms (dict) in self.parmSettings['parms'].
        Called by GPI_PROCESS functor to capture all widget settings needed
        in compute().
        '''
        self.parmSettings = self.getSettings()

    def getWdgFromBuffer(self, title):
        # find a specific widget by title
        for wdg in self.parmSettings['parms']:
            if 'name' in wdg:
                if wdg['name'] == title:
                    return wdg


    def getVal(self, title):
        """Returns get_val() from wdg-class (see getAttr()).
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
            raise GPIError_nodeAPI_getVal('self.getVal(\''+stw(title)+'\') failed in the node definition, check the widget name.')

    def getAttr(self, title, attr):
        """title = (str) wdg-class name
        attr = (str) corresponds to the get_<arg> of the desired attribute.
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
            raise GPIError_nodeAPI_getAttr('_getAttr() failed for widget \''+stw(title)+'\'')

    def validate(self):
        '''The pre-compute validation step
        '''
        log.debug("Default module validate().")
        return (0)

    def compute(self):
        '''The module compute routine
        '''
        log.debug("Default module compute().")
        return (0)

    def post_compute_widget_update(self):
        # reset any widget that requires it (i.e. PushButton)
        for parm in self.parmList:
            if hasattr(parm, 'set_reset'):
                parm.set_reset()
