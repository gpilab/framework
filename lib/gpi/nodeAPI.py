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
import traceback
import collections

# gpi
import gpi
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

class NodeAPI:
    '''This is the class that all external modules must implement.'''
    GPIExtNodeType = ExternalNodeType  # ensures the subclass is of THIS class

    def __init__(self, node):
        self._name = __file__[:-7]  # strips off the _GPI.py, prob won't work
        self._label = ''
        self._detailLabel = ''
        self._detailElideMode = 'middle'
        self._docText = None

        # dictionary of all widgets
        # ordered such that they can appear in the proper order in the NodeUI
        # key: widget title
        # value: dict of widget values, min, max, etc.
        # value *must include* {'wdg' : widget_type}
        self._widgets = collections.OrderedDict()
        # TODO: add label and detailLabel to the widgets dict here?

        self._inPorts = collections.OrderedDict()
        self._outPorts = collections.OrderedDict()

        # allow logger to be used in initUI()
        self.log = manager.getLogger(self._name)

        try:
            self._initUI_ret = self.initUI()
        except:
            log.error('initUI() failed. '+str(node.item.fullpath)+'\n'+str(traceback.format_exc()))
            self._initUI_ret = -1  # error

        self.setTitle(self._name)

        self._starttime = 0
        self._startline = 0

    def initUI_return(self):
        return self._initUI_ret

    # Property decorators could make things better/cleaner? I'm not sure it's
    # worth it, as we need to preserve the current API anyway.
    # @property
    # def widgets(self):
    #     return self._widgets

    # @widgets.setter
    # def widgets(self, w):
    #     self._widgets = w

    # @widgets.deleter
    # def widgets(self):
    #     del self._widgets

    # @property
    # def ports(self):
    #     return self._ports

    # @ports.setter
    # def ports(self, p):
    #     self._ports = p

    # @ports.deleter
    # def ports(self):
    #     del self._ports

    def getWidgets(self):
        # return a list of widgets
        return self._widgets

    def getWidgetNames(self):
        return list(self._widgets.keys())

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

    def execType(self):
        # default executable type
        # return GPI_THREAD
        return GPI_PROCESS  # this is the safest
        # return GPI_APPLOOP

    # TODO: move to node.py? All results here acces the node instance anyway...
    # def setReQueue(self, val=False):  # NODEAPI
    #     # At the end of a nodeQueue, these tasked are checked for
    #     # more events.
    #     if self.node.inDisabledState():
    #         return
    #     if self.node.nodeCompute_thread.execType() == GPI_PROCESS:
    #         self.node.nodeCompute_thread.addToQueue(['setReQueue', val])
    #     else:
    #         self.node._requeue = val

    # def reQueueIsSet(self):
    #     return self.node._requeue

    def getLabel(self):
        return self._label

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

    def setLabel(self, newlabel=''):
        self._label = str(newlabel)

    def setDetailLabel(self, newDetailLabel='', elideMode='middle'):
        '''An additional label displayed on the node directly'''
        self._detailLabel = str(newDetailLabel)
        self._detailElideMode = elideMode

    def getDetailLabel(self):
        '''An additional label displayed on the node directly'''
        return self._detailLabel

    def getDetailLabelElideMode(self):
        '''How the detail label should be elided if it's too long'''
        return self._detailElideMode

    # to be subclassed and reimplemented.
    def initUI(self):

        # window
        #self.setWindowTitle(self.node.name)

        # IO Ports
        #self.addInPort('in1', str, obligation=REQUIRED)
        #self.addOutPort('out2', int)
        pass

    # TODO: needs to basically just return self._widgets, I think, but maybe it
    # should be re-structured to serialize in the way it did before?
    def getSettings(self):  # NODEAPI
        '''Wrap up all settings from each widget.'''
        s = {}
        s['label'] = self._label
        s['parms'] = []
        for title, parms in self._widgets.items():
            parm_dict = {'title' : title}
            parm_dict.update(parms)
            s['parms'].append(parm_dict)
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
        node_doc = "NODE: \'" + self._name + "\'\n" + "    " + \
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
        for widget_name, wdg in self._widgets.items():
            log.debug("widget: " + widget_name)
            log.debug("value: " + wdg['val'])

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
        self._inPorts[title] = kwargs
        self._inPorts[title].update({'type' : type,
                                     'obligation' : obligation,
                                     'menuWidget' : menuWidget,
                                     'cyclic' : cyclic,
                                     'data' : None})

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
        self._outPorts[title] = kwargs
        self._outPorts[title].update({'type' : type,
                                     'obligation' : obligation,
                                     'menuWidget' : menuWidget,
                                     'data' : None})

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
        if title in self._widgets.keys():
            log.critical("addWidget(): Widget title \'" + str(title) \
                + "\' is already in use! Aborting.")
            return

        self._widgets[title] = kwargs
        self._widgets[title].update({'wdg' : wdg})

    # TODO: move these to NodeUI?
    # def findWidgetByName(self, title):
    #     for parm in self.parmList:
    #         if parm.getTitle() == title:
    #             return parm

    # def findWidgetByID(self, wdgID):
    #     for parm in self.parmList:
    #         if parm.id() == wdgID:
    #             return parm

    # TODO: these belong in NodeUI, I think
    # def modifyWidget_setter(self, src, kw, val):
    #     sfunc = "set_" + kw
    #     if hasattr(src, sfunc):
    #         func = getattr(src, sfunc)
    #         func(val)
    #     else:
    #         try:
    #             ttl = src.getTitle()
    #         except:
    #             ttl = str(src)

    #         log.critical("modifyWidget_setter(): Widget \'" + stw(ttl) \
    #             + "\' doesn't have attr \'" + stw(sfunc) + "\'.")

    # def modifyWidget_direct(self, pnumORtitle, **kwargs):
    #     src = self.getWidget(pnumORtitle)

    #     for k, v in list(kwargs.items()):
    #         if k != 'val':
    #             self.modifyWidget_setter(src, k, v)

    #     # set 'val' last so that bounds don't cause a temporary conflict.
    #     if 'val' in kwargs:
    #         self.modifyWidget_setter(src, 'val', kwargs['val'])

    # def modifyWidget_buffer(self, title, **kwargs):
    #     '''GPI_PROCESSes have to use buffered widget attributes to effect the
    #     same changes to attributes during compute() as with GPI_THREAD or
    #     GPI_APPLOOP.
    #     '''
    #     src = self.getWdgFromBuffer(title)

    #     try:
    #         for k, v in list(kwargs.items()):
    #             src['kwargs'][k] = v
    #     except:
    #         log.critical("modifyWidget_buffer() FAILED to modify buffered attribute")

    def setTitle(self, title):
        self._name = title

    # Queue actions for widgets and ports
    def setAttr(self, title, **kwargs):
        """title = (str) the corresponding widget name.
        kwargs = args corresponding to the get_<arg> methods of the wdg-class.
        """
        self._widgets[title].update(kwargs)

    def allocArray(self, shape=(1,), dtype=np.float32, name='local'):
        '''return a shared memory array if the node is run as a process.
            -the array name needs to be unique
        '''
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
        """title = (str) name of the OutPort to send the object reference.
        data = (object) any object corresponding to a GPIType class.
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
        if GPI_PORT_EVENT in self.getEvent():
            return self.getEvent()[GPI_PORT_EVENT]
        return None

    def widgetEvent(self):
        '''Specifically check for a wdg event.'''
        log.warn('The \'widgetEvent()\' function is deprecated, use \'widgetEvents()\' (its the plural form). '+str(self.node.getFullPath()))
        if GPI_WIDGET_EVENT in self.getEvent():
            return self.getEvent()[GPI_WIDGET_EVENT]
        return None
############### DEPRECATED NODE API

    # TODO: the Node class should call this whenever there are new events
    # self._events should be a queue or list of all events, then the getEvents
    # methods below can iterate over them and/or filter them. The getEvents
    # methods should also (by default, at least?) clear the events from the
    # main queue as they are processed.
    def setEvents(self, events):
        pass

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

    # TODO: deprecate in user API?
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
            val = self._widgets[title]['val']
        except:
            print(str(traceback.format_exc()))
            raise GPIError_nodeAPI_getVal('self.getVal(\''+stw(title)+'\') failed in the node definition, check the widget name.')

    def getAttr(self, title, attr):
        """title = (str) wdg-class name
        attr = (str) corresponds to the get_<arg> of the desired attribute.
        """
        try:
            attr_val = self._widgets[title][attr]
        except:
            print(str(traceback.format_exc()))
            raise GPIError_nodeAPI_getAttr('self.getAttr(\''+stw(title)+'\',...) failed in the node definition, check widget name and attribute name.')

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
