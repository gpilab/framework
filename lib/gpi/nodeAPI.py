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

import time
import inspect
import traceback
import collections

# gpi
from .defines import ExternalNodeType
from .defines import GPI_PROCESS, GPI_THREAD, stw, GPI_SHDM_PATH
from .defines import GPI_WIDGET_EVENT, REQUIRED, OPTIONAL, GPI_PORT_EVENT
from .dataproxy import DataProxy
from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)

# for PROCESS data hack
import numpy as np

# Developer Interface Exceptions
class GPIError_nodeAPI_setData(Exception):
    def __init__(self, value):
        super().__init__(value)

class GPIError_nodeAPI_getData(Exception):
    def __init__(self, value):
        super().__init__(value)

class GPIError_nodeAPI_setAttr(Exception):
    def __init__(self, value):
        super().__init__(value)

class GPIError_nodeAPI_getAttr(Exception):
    def __init__(self, value):
        super().__init__(value)

class GPIError_nodeAPI_getVal(Exception):
    def __init__(self, value):
        super().__init__(value)


class NodeAPI:
    '''This is the class that all external modules must implement.'''
    GPIExtNodeType = ExternalNodeType  # ensures the subclass is of THIS class

    def __init__(self, module_name='', fullpath=''):
        self._module_name = module_name
        self._fullpath = fullpath
        self._label = ''
        self._detailLabel = ''
        self._detailElideMode = 'middle'
        self._docText = None

        # dictionary of all widgets
        # ordered such that they can appear in the proper order in the NodeUI
        # key: widget title
        # value: dict of widget values - val, min, max, etc.
        # value *must include* {'wdg' : widget_type}
        self._widgets = collections.OrderedDict()
        # TODO: add label and detailLabel to the widgets dict here?

        self._inPorts = collections.OrderedDict()
        self._outPorts = collections.OrderedDict()

        self._events = {}

        # allow logger to be used in initUI()
        self.log = manager.getLogger(self._module_name)

        try:
            self._initUI_ret = self.initUI()
        except:
            log.error('initUI() failed. '+str(self._fullpath)+'\n'+str(traceback.format_exc()))
            self._initUI_ret = -1  # error

        self._nodeID = None
        self._proxy = None
        self._exec_type = self.execType()
        self.shdmDict = {}

        self.setTitle(self._module_name)

        self._starttime = 0
        self._startline = 0

    def initUI_return(self):
        return self._initUI_ret

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
                                     'cyclic' : cyclic})

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
                                     'menuWidget' : menuWidget})

    def setData(self, title, data):
        """title = (str) name of the OutPort to send the object reference.
        data = (object) any object corresponding to a GPIType class.
        """
        # TODO: can you even setData on an inPort?
        try:
            port = self._inPorts[title]
        except KeyError:
            pass
        except:
            raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition check the port name.')
        else:
            if self._exec_type == GPI_PROCESS:
                self._setDataProcess(title, data)
            else:
                port['data'] = data

        try:
            port = self._outPorts[title]
        except KeyError:
            raise Exception("getData", "Invalid Port Title")
        except:
             raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition check the port name.')
        else:
            if self._exec_type == GPI_PROCESS:
                self._setDataProcess(title, data)
            else:
                port['data'] = data

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

    def getVal(self, title):
        """Returns get_val() from wdg-class (see getAttr()).
        """
        try:
            val = self._widgets[title]['val']
        except:
            print(str(traceback.format_exc()))
            raise GPIError_nodeAPI_getVal('self.getVal(\''+stw(title)+'\') failed in the node definition, check the widget name.')
        return val

    def getAttr(self, title, attr):
        """title = (str) wdg-class name
        attr = (str) corresponds to the get_<arg> of the desired attribute.
        """
        try:
            attr_val = self._widgets[title][attr]
        except:
            print(str(traceback.format_exc()))
            raise GPIError_nodeAPI_getAttr('self.getAttr(\''+stw(title)+'\',...) failed in the node definition, check widget name and attribute name.')

    # Queue actions for widgets and ports
    def setAttr(self, title, **kwargs):
        """title = (str) the corresponding widget name.
        kwargs = args corresponding to the get_<arg> methods of the wdg-class.
        """
        self._widgets[title].update(kwargs)

    def getInPorts(self):
        return self._inPorts

    def getOutPorts(self):
        return self._outPorts

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

    def getLabel(self):
        return self._label

    def moduleExists(self, name):
        '''Give the user a simple module checker for the node validate
        function.
        '''
        import imp
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
        node_doc = "NODE: \'" + self._module_name + "\'\n" + "    " + \
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


    def setTitle(self, title):
        self._module_name = title

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

    def config(self, nodeID, exec_type):
        self._nodeID = nodeID
        self._exec_type = exec_type

    def _setDataProcess(self, title, data):
        if type(data) is np.memmap or type(data) is np.ndarray:
            if str(id(data)) in self.shdmDict: # pre-alloc
                s = DataProxy().NDArray(data, shdf=self.shdmDict[str(id(data))], nodeID=self._nodeID, portname=title)
            else:
                s = DataProxy().NDArray(data, nodeID=self._nodeID, portname=title)

            # for split objects to pass thru individually
            # this will be a list of DataProxy objects
            if type(s) is list:
                for i in s:
                    self._proxy.append(['setData', title, i])
            # a single DataProxy object
            else:
                self._proxy.append(['setData', title, s])

        # all other non-numpy data that are pickleable
        else:
            # PROCESS output other than numpy
            self._proxy.append(['setData', title, data])

        # try:
        #     # start = time.time()
        #     # either set directly or save a queue
        #     if self.node.inDisabledState():
        #         return
        #     if self.node.nodeCompute_thread.execType() == GPI_PROCESS:

        #         #  numpy arrays
        #         if type(data) is np.memmap or type(data) is np.ndarray:
        #             if str(id(data)) in self.shdmDict: # pre-alloc
        #                 s = DataProxy().NDArray(data, shdf=self.shdmDict[str(id(data))], nodeID=self.node.getID(), portname=title)
        #             else:
        #                 s = DataProxy().NDArray(data, nodeID=self.node.getID(), portname=title)

        #             # for split objects to pass thru individually
        #             # this will be a list of DataProxy objects
        #             if type(s) is list:
        #                 for i in s:
        #                     self.node.nodeCompute_thread.addToQueue(['setData', title, i])
        #             # a single DataProxy object
        #             else:
        #                 self.node.nodeCompute_thread.addToQueue(['setData', title, s])

        #         # all other non-numpy data that are pickleable
        #         else:
        #             # PROCESS output other than numpy
        #             self.node.nodeCompute_thread.addToQueue(['setData', title, data])
        #     else:
        #         # THREAD or APPLOOP
        #         self.node.setData(title, data)
        #         # log.debug("setData(): time: "+str(time.time() - start)+" sec")

        # except:
        #     print((str(traceback.format_exc())))
        #     raise GPIError_nodeAPI_setData('self.setData(\''+stw(title)+'\',...) failed in the node definition, check the output name and data type().')

    def getData(self, title):
        """title = (str) the name of the Port.
        """
        try:
            port = self._inPorts[title]
        except KeyError:
            pass
        except:
            raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition check the port name.')
        else:
            return port.get('data', None)

        try:
            port = self._outPorts[title]
        except KeyError:
            raise Exception("getData", "Invalid Port Title")
        except:
             raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition check the port name.')
        else:
            return port.get('data', None)

    # TODO: deprecate these two functions?
    # def getInPort(self, pnumORtitle):
    #     return self.node.getInPort(pnumORtitle)

    # def getOutPort(self, pnumORtitle):
    #     return self.node.getOutPort(pnumORtitle)

    def updateWidgets(self, widgets):
        for title in widgets.keys():
            try:
                self._widgets[title].update(widgets[title])
            except KeyError:
                log.warn("{} node tried to update {}".format(self._module_name, title)
                         + " widget, but it was not found")

    def updatePortData(self, portData):
        for title in portData.keys():
            try:
                self._inPorts[title].update(portData[title])
            except KeyError:
                pass
            except:
                raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition check the port name.')
            else:
                continue

            try:
                self._outPorts[title].update(portData[title])
            except KeyError:
                raise Exception("getData", "Invalid Port Title")
            except:
                 raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition check the port name.')

    # TODO: the Node class should call this whenever there are new events
    # self._events should be a queue or list of all events, then the getEvents
    # methods below can iterate over them and/or filter them. The getEvents
    # methods should also (by default, at least?) clear the events from the
    # main queue as they are processed. (Then again, this may not be necessary)
    def updateEvents(self, eventManager):
        self._events.update(eventManager.events)

    def getEvents(self):
        '''Allow node developer to get information about what event has caused
        the node to run.'''
        events = self._events
        self._events = {}
        return events

    def portEvents(self):
        '''Specifically check for a port event.  Widget-ports count as both.'''
        port_events = filter(lambda x: (x in self._inPorts.keys()
                                        or x in self._outPorts.keys()),
                             self._events[GPI_PORT_EVENT])
        self._events[GPI_PORT_EVENT] = filter(lambda x:
                                              not (x in self._inPorts.keys()
                                              or x in self._outPorts.keys()),
                                              self._events[GPI_PORT_EVENT])
        return port_events
        # return self.node.getPendingEvents().port

    def widgetEvents(self):
        '''Specifically check for a wdg event.'''
        widget_events = filter(lambda x: x in self._widgets.keys(),
                               self._events[GPI_WIDGET_EVENT])
        self._events[GPI_WIDGET_EVENT] = filter(lambda x:
                                                x not in self._widgets.keys(),
                                                self._events[GPI_WIDGET_EVENT])
        return widget_events
        # return self.node.getPendingEvents().widget

    def widgetMovingEvent(self, wdgid):
        '''Called when a widget drag is being initiated.
        '''
        pass

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


    def _compute(self, procTitle='unknown', procLabel='unknown', proxy=None):
        self._proxy = proxy
        if self._proxy is not None:
            try:
                self._proxy.append(['retcode', self.compute()])
            except:
                err_str = 'PROCESS: \'{}\':\'{}\' compute() failed.\n{}'
                log.error(err_str.format(procTitle,
                                         procLabel,
                                         traceback.format_exc()))
                self._proxy.append(['retcode', -1])
        else:
            return self.compute()

