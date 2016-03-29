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

    # top-level methods
    # to be subclassed and reimplemented.
    def initUI(self):
        pass

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
                                     'cyclic' : cyclic,
                                     'changed' : False})

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
                                     'changed' : False})

    def getData(self, title):
        """title = (str) the name of the Port.
        """
        try:
            port = self._inPorts[title]
        except KeyError:
            pass
        except:
            raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition. Check the port name.')
        else:
            return port.get('data', None)

        try:
            port = self._outPorts[title]
        except KeyError:
            raise Exception("getData", "Invalid Port Title")
        except:
            raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition. Check the port name.')
        else:
            return port.get('data', None)

    def setData(self, title, data):
        """title = (str) name of the OutPort to send the object reference.
        data = (object) any object corresponding to a GPIType class.
        """
        try:
            port = self._outPorts[title]
        except KeyError:
            raise Exception("setData", "Invalid Port Title")
        except:
             raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition. Check the port name.')
        else:
            if self._exec_type == GPI_PROCESS:
                self._setDataProcess(title, data)
            else:
                port['data'] = data
                port['changed'] = True

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
        if self.execType is GPI_PROCESS:
            self._proxy.append(['setAttr', title, kwargs])
        else:
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
        return GPI_PROCESS  # this is the safest
        # return GPI_THREAD
        # return GPI_APPLOOP

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

    # TODO: needs to basically just return self._widgets, I think, but maybe it
    # should be re-structured to serialize in the way it did before?
    def getSettings(self):
        '''Wrap up all settings from each widget.'''
        s = {}
        s['parms'] = []
        for title, parms in self._widgets.items():
            parm_dict = {'title' : title}
            parm_dict.update(parms)
            s['parms'].append(parm_dict)
        print(s)
        print(self._widgets)
        return s

    def loadSettings(self, s):
        self.setLabelWidget(s['label'])

        # modify node widgets
        for parm in s['parms']:
            # the NodeAPI has instantiated the widget by name, this will
            # change the wdg-ID, however, this step is only dependent on
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

    def printWidgetValues(self):
        # for debugging
        for widget_name, wdg in self._widgets.items():
            log.debug("widget: " + widget_name)
            log.debug("value: " + wdg['val'])

    def setTitle(self, title):
        self._module_name = title

    def getEvents(self):
        '''Allow node developer to get information about what event has caused
        the node to run.'''
        return self._events

    def portEvents(self):
        '''Specifically check for a port event.  Widget-ports count as both.'''
        port_events = self._events[GPI_PORT_EVENT]
        return port_events

    def widgetEvents(self):
        '''Specifically check for a wdg event.'''
        widget_events = self._events[GPI_WIDGET_EVENT]
        return widget_events

    # 'protected' methods - to be called by other GPI framework classes (not
    # users/devs)
    def config(self, nodeID, exec_type):
        self._nodeID = nodeID
        self._exec_type = exec_type

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
                self._inPorts[title]['changed'] = False
            except KeyError:
                pass
            except:
                raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition check the port name.')
            else:
                continue

            try:
                self._outPorts[title].update(portData[title])
                self._outPorts[title]['changed'] = False
            except KeyError:
                raise Exception("updatePortData", "Invalid Port Title")
            except:
                 raise GPIError_nodeAPI_getData('self.getData(\''+stw(title)+'\') failed in the node definition check the port name.')

    def updateEvents(self, eventManager):
        self._events.update(eventManager.events)

    def initUI_return(self):
        return self._initUI_ret

    # 'private' methods
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

