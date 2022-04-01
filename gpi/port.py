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


from gpi import QtCore, QtGui, QtWidgets

# gpi
from .defines import PortTYPE, InPortTYPE, OutPortTYPE, REQUIRED, OPTIONAL
from .defines import GPI_PORT_EVENT, stw
from .defines import getKeyboardModifiers, printMouseEvent
from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)


class Port(QtWidgets.QGraphicsItem):
    '''The base-class of the Node InPorts and OutPorts. This is responsible for
    Tool tips, serialization, drawing, painting, and type matching for
    connectivity.
    '''
    Type = PortTYPE

    def __init__(self, nodeWidget, CanvasBackend, portTitle, portNum, intype=None, dtype=None, ndim=None, menuWidget=None):
        super(Port, self).__init__()

        self._id = None
        self.setID()

        self.node = nodeWidget
        self.menuWidget = menuWidget  # a reference to a module menu widget
        self.graph = CanvasBackend
        self.edgeList = []
        self.newPos = QtCore.QPointF()

        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)
        self.setZValue(3)

        ## TYPE info
        self._GPIType = intype  # basic data type
        # for NPY arrays
        self._dtype = dtype  # array data type
        self._ndim = ndim
        self._obligation = None  # inport use only
        # a link to the data
        self._data = None

        # position
        self.portNum = portNum
        self.portTitle = portTitle
        if portTitle is None:
            self.portTitle = str(portNum)

        # port shape
        self.largenessFact = 3.0
        self.pointsCoord = [[0.0, 0.0], [7.0, 0.0], [3.5, 5]]
        self.setTransformOriginPoint(3.5, 5)
        if isinstance(self, OutPort):
            self.setTransformOriginPoint(3.5, 0)
        # self.portShape = trianglePolygon = QtGui.QPolygonF()
        self.portShape = QtGui.QPolygonF()
        for i in self.pointsCoord:
            self.portShape.append(QtCore.QPointF(i[0], i[1]))

        # box
        # self.pointsCoord_canvasConnect = [[0.0, 0.0], [7.0, 0.0], [7.0, 5], [0.0, 5]]
        # bowtie
        #self.pointsCoord_canvasConnect = [[0.0, 0.0], [7.0, 0.0], [3.5, 2.5], [0.0, 5.0], [7.0, 5.0], [3.5, 2.5]]
        #self.portShape_canvasConnect = QtGui.QPolygonF()
        #for i in self.pointsCoord_canvasConnect:
        #    self.portShape_canvasConnect.append(QtCore.QPointF(i[0], i[1]))

        # box
        # self.pointsCoord_canvasConnect = [[0.0, 0.0], [7.0, 0.0], [7.0, 5], [0.0, 5]]
        # bowtie
        self.pointsCoord_memSave = [[0.0, 0.0], [7.0, 0.0], [3.5, 2.5], [0.0, 5.0], [7.0, 5.0], [3.5, 2.5]]
        self.portShape_memSave = QtGui.QPolygonF()
        for i in self.pointsCoord_memSave:
            self.portShape_memSave.append(QtCore.QPointF(i[0], i[1]))

        self.setCursor(QtCore.Qt.CrossCursor)

        self.setAcceptHoverEvents(True)
        self._beingHovered = False
        self.updateToolTip()

        # src or sink
        self._canvasConnect = False

        # save memory
        self._savemem = False

    def triggerHoverLeaveEvent(self):
        e = QtCore.QEvent(QtCore.QEvent.GraphicsSceneHoverLeave)
        self.hoverLeaveEvent(e)

    def BeingHovered(self):
        return self._beingHovered

    def allowsCyclicConn(self):
        '''Abstract function
        '''
        return False

    def resetPos(self):
        if isinstance(self, InPort):
            self.setPos(-8 + 8 * self.portNum, -12)
            self.updateEdges()

        if isinstance(self, OutPort):
            h = self.getNode().getOutPortVOffset()
            self.setPos(-8 + 8 * self.portNum, h)
            self.updateEdges()

    def setPosByPortNum(self, portNum):
        if isinstance(self, InPort):
            self.setPos(-8 + 8 * portNum, -12)
            self.updateEdges()

        if isinstance(self, OutPort):
            h = self.getNode().getOutPortVOffset()
            self.setPos(-8 + 8 * portNum, h)
            self.updateEdges()

    def setMemSaver(self, val):
        self._savemem = val

    def isMemSaver(self):
        return self._savemem

    def toggleMemSaver(self):
        if self._savemem:
            self._savemem= False
        else:
            self._savemem= True

    def setCanvasConnect(self, val):
        self._canvasConnect= val

    def isCanvasConnected(self):
        return self._canvasConnect

    def toggleCanvasConnect(self):
        if self._canvasConnect:
            self._canvasConnect = False
        else:
            self._canvasConnect = True

    def setID(self, value=None):
        if value is None:
            self._id = id(self)  # this will always be unique
        else:
            self._id = value

    def getID(self):
        return self._id

    def isWidgetPort(self):
        if self.menuWidget is None:
            return False
        else:
            return True

    def GPIType(self):
        return self._GPIType

    def updateToolTip(self):
        # PORTAUTH
        oblBuf = ''
        if isinstance(self, InPort):
            if self.isREQUIRED():
                oblBuf = '(REQUIRED)'
            else:
                oblBuf = '(OPTIONAL)'

            if self.allowsCyclicConn():
                oblBuf += ' Cyclic'

        tip = "\'"+str(self.portTitle)+'\': '+oblBuf+'\n'
        tip += self._GPIType.toolTip_Port()
        tip += '\n'

        if isinstance(self, OutPort):
            tip += '____________________\n'
            tip += 'Data Info: \n'
            tip += self._GPIType.toolTip_Data(self.data)

        self.setToolTip(tip)

    def scaleUp(self):
        self.setScale(self.largenessFact)
        self.update()

    def resetScale(self):
        self.setScale(1)
        self.update()

    def findOppositePorts(self):

        ports = []

        # for outports, find all appropriate inports
        if isinstance(self, OutPort):
            for item in list(self.graph.scene().items()):
                if isinstance(item, InPort):
                    ports.append(item)

        # vica-versa for all inports
        if isinstance(self, InPort):
            for item in list(self.graph.scene().items()):
                if isinstance(item, OutPort):
                    ports.append(item)

        return ports

    def getName(self):
        return self.portTitle

    def getSettings(self):  # PORT SETTINGS
        # get the settings required to re-instantiate this port
        # PORTAUTH
        s = {}

        # Possibly not needed:
        s['id'] = self.getID()
        s['porttitle'] = self.portTitle
        s['porttype'] = self.porttype()

        # data type
        # s['intype']      = self._type
        # s['dtype']       = self._dtype
        # s['ndim']        = self._ndim

        s['obligation'] = self._obligation
        s['portnum'] = self.portNum
        if self.isWidgetPort():
            s['widgetTitle'] = self.menuWidget.getTitle()
        else:
            s['widgetTitle'] = None

        # In loadNetwork() this is the only info used
        # -the rest is instantiated from ExternalNode()
        # derived class.
        s['connections'] = []
        for edge in self.edgeList:
            s['connections'].append(edge.getCoords())
        return s

    def getNodeID(self):
        return self.node.getID()

    def hoverEnterEvent(self, event):

        # Upstream forced hover
        if isinstance(self, InPort):
            for edge in self.edgeList:
                edge.sourcePort().hoverEnterEvent(event)

        self._beingHovered = True
        self.setScale(self.largenessFact)
        self.node.setZValue(101)
        self.update()
        for edge in self.edgeList:
            edge.adjust()
            edge.update()
        self.node.graph.viewAndSceneForcedUpdate()

    def hoverLeaveEvent(self, event):

        # Upstream forced hover
        if isinstance(self, InPort):
            for edge in self.edgeList:
                edge.sourcePort().hoverLeaveEvent(event)

        self._beingHovered = False
        self.setScale(1.0)
        self.node.setZValue(2)
        self.update()
        for edge in self.edgeList:
            edge.adjust()
            edge.update()
        self.node.graph.viewAndSceneForcedUpdate()

    def type(self):
        return Port.Type

    def porttype(self):
        return Port.Type

    def addEdge(self, edge):
        self.edgeList.append(edge)
        edge.adjust()

    def detachEdge(self, edge):
        '''This is a little misleading, it only pops the edge from a port\'s edgelist'''
        self.triggerHoverLeaveEvent()
        for i in range(len(self.edgeList)):
            if self.edgeList[i] == edge:
                return self.edgeList.pop(i)

    def edges(self):  # PORT
        return self.edgeList

    def edgeCount(self):
        return len(self.edgeList)

    # all connected nodes and thier connetion directions
    def getConnectionTuples(self):
        '''Source and dest only apply to the
        order in which the user connected the edge.
        The DAG order is determined by port direction.
        -append( (src -> sink) )
        '''
        c = []
        for edge in self.edgeList:
            if isinstance(edge.sourcePort(), OutPort):
                c.append((edge.sourceNode(), edge.destNode()))
            else:
                c.append((edge.destNode(), edge.sourceNode()))
        return c

    def getNonCyclicConnectionTuples(self):
        c = []
        for edge in self.edgeList:
            if not edge.isCyclicConnection():
                if isinstance(edge.sourcePort(), OutPort):
                    c.append((edge.sourceNode(), edge.destNode()))
                else:
                    c.append((edge.destNode(), edge.sourceNode()))
        return c

    def getDownstreamNodes(self):  # PORT
        '''Get downstream nodes connected to this port.'''
        c = []
        for edge in self.edgeList:
            edge.update()  # update edge-text
            if edge.sourcePort() is self:
                # c[edge.destNode()] = edge.destPort().portTitle
                c.append([edge.destNode(), edge.destPort().portTitle])
                # print edge.destNode().name
        return c

    def getNode(self):
        return self.node

    def boundingRect(self):
        adjust = 2.0
        maxx = max([i for i, j in self.pointsCoord])
        maxy = max([j for i, j in self.pointsCoord])
        return QtCore.QRectF((0 - adjust), (0 - adjust), (maxx + adjust), (maxy + adjust))

    def shape(self):
        path = QtGui.QPainterPath()
        # path.addEllipse(0, 0, 5, 5)
        path.addPolygon(self.portShape)
        self.update()
        return path

    def paint(self, painter, option, widget):  # PORT
        # choose module color
        gradient = QtGui.QRadialGradient(-1, -1, 10)
        if option.state & QtWidgets.QStyle.State_Sunken:
            gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.red).lighter(150))
            gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.darkRed).lighter(150))
        # elif self._beingHovered:
        #    gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.darkRed).lighter(150))
        #    gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.red).lighter(150))
        elif isinstance(self, InPort):
            # if self.menuWidget:
            if self.isREQUIRED():
                # gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.yellow).lighter(200))
                # gradient.setColorAt(1,
                # QtGui.QColor(QtCore.Qt.darkYellow).lighter(200))
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.blue).lighter(200))
                gradient.setColorAt(1, QtGui.QColor(
                    QtCore.Qt.darkBlue).lighter(200))
                # gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.gray).lighter(300))
                # gradient.setColorAt(0,
                # QtGui.QColor(QtCore.Qt.darkGray).lighter(150))
            else:
                gradient.setColorAt(0, QtGui.QColor(
                    QtCore.Qt.green).lighter(200))
                gradient.setColorAt(1, QtGui.QColor(
                    QtCore.Qt.darkGreen).lighter(150))
            #    gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.gray).lighter(150))
            # gradient.setColorAt(1,
            # QtGui.QColor(QtCore.Qt.darkGray).lighter(100))
        elif isinstance(self, OutPort):
            # if self.menuWidget:
                # orange=QtGui.QColor().fromRgbF(1.,0.5,0.)
                # gradient.setColorAt(0, orange.lighter(200))
                # gradient.setColorAt(1, orange.lighter(100))
                # gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.blue).lighter(300))
                # gradient.setColorAt(1,
                # QtGui.QColor(QtCore.Qt.darkBlue).lighter(300))
                if self.dataIsNone():
                    gradient.setColorAt(1, QtGui.QColor(
                        QtCore.Qt.red).lighter(300))
                    gradient.setColorAt(0, QtGui.QColor(
                        QtCore.Qt.darkRed).lighter(150))
                elif self.dataHasChanged():
                    # gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.gray).lighter(200))
                    # gradient.setColorAt(0,
                    # QtGui.QColor(QtCore.Qt.darkGray).lighter(100))
                    gradient.setColorAt(1, QtGui.QColor(
                        QtCore.Qt.blue).lighter(200))
                    gradient.setColorAt(0, QtGui.QColor(
                        QtCore.Qt.darkBlue).lighter(200))
                else:
                    gradient.setColorAt(1, QtGui.QColor(
                        QtCore.Qt.yellow).lighter(200))
                    gradient.setColorAt(0, QtGui.QColor(
                        QtCore.Qt.darkYellow).lighter(150))
            # else:
                # gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.blue).lighter(175))
                # gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.darkBlue).lighter(175))
                # gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.gray).lighter(150))
                # gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.darkGray).lighter(100))
            #    if self.dataIsNone():
            #        gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.red).lighter(150))
            #        gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.darkRed).lighter(100))
            #    elif self.dataHasChanged():
            #        gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.gray).lighter(150))
            #        gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.darkGray).lighter(100))
            #    else:
            #        gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.yellow).lighter(200))
            # gradient.setColorAt(1,
            # QtGui.QColor(QtCore.Qt.darkYellow).lighter(150))

        # draw module box (apply color)
        painter.setBrush(QtGui.QBrush(gradient))
        #painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
        fade = QtGui.QColor(QtCore.Qt.black)
        fade.setAlpha(50)
        painter.setPen(QtGui.QPen(fade, 0))

        # if isinstance(self,InPort):
        #    if self.isREQUIRED():
        #        painter.setPen(QtGui.QPen(QtCore.Qt.red, 0))
        #    else:
        #        painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
        #        #painter.setPen(QtGui.QPen(QtCore.Qt.yellow, 0))

        if self.isMemSaver():
            painter.drawPolygon(self.portShape_memSave)
        else:
            if self.menuWidget:
                painter.drawEllipse(1, 0, 5, 5)
            else:
                painter.drawPolygon(self.portShape)

    def updateEdges(self):
        for edge in self.edgeList:
            edge.adjust()

    def mousePressEvent(self, event):  # PORT
        printMouseEvent(self, event)
        modifiers = getKeyboardModifiers()

        self.update()  # update port color/size/etc
        modmidbutton_event = (event.button() == QtCore.Qt.LeftButton
                              and modifiers == QtCore.Qt.AltModifier)
        if event.button() == QtCore.Qt.MidButton or modmidbutton_event:
            event.accept()
        elif event.button() == QtCore.Qt.LeftButton:
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            event.accept()
        else:
            event.ignore()
        super(Port, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):  # PORT
        printMouseEvent(self, event)

        self.update()  # update port color/size/etc
        if event.button() == QtCore.Qt.MidButton:
            event.accept()
        elif event.button() == QtCore.Qt.LeftButton:
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            event.accept()
        else:
            event.ignore()
        super(Port, self).mouseReleaseEvent(event)

    def advance(self):
        if self.newPos == self.pos():
            return False

        self.setPos(self.newPos)
        return True

    def checkDataType(self, indata):
        # PORTAUTH
        # This checks the inbound data type against the porttype while a
        # connection is being made or when new data is passed downstream.
        return self._GPIType.matchesData(indata)

    def checkTypeAgainstPort(self, uport):
        # PORTAUTH
        # This check verfies a connection between two ports
        # when the user is drawing a connection or when a port
        # is clicked and other connectable ports are highlighted.
        if uport:
            return self._GPIType.matchesType(uport._GPIType)

        # port doesn't exist, not sure why this is being tested.
        return False


class InPort(Port):
    '''Defines the specific behavior for connecting to inports i.e. how to 
    check for upstream data types, and obligation.
    '''

    PortType = InPortTYPE

    def __init__(self, nodeWidget, CanvasBackend, title, portNum, intype=None, dtype=None, ndim=None, obligation=REQUIRED, menuWidget=None, cyclic=False):

        self._cyclic = cyclic

        super(InPort, self).__init__(nodeWidget, CanvasBackend,
                                     title, portNum, intype, dtype, ndim, menuWidget)
        # REQUIRED or OPTIONAL type
        self._obligation = obligation

    def edge(self):
        '''InPorts only have one edge'''
        if len(self.edgeList):
            return self.edgeList[0]

    def allowsCyclicConn(self):
        return self._cyclic

    # matching outports
    def findMatchingOutPorts(self, ports=None):
        if ports == None: ports = self.findOppositePorts()
        matching_ports = []

        # just ignore if its already connected
        if len(self.edges()):
            return matching_ports

        if len(ports):
            for port in ports:
                # skip ports on the same node
                if port.node == self.node:
                    continue
                # check data if available
                if port.data is not None:
                    if self.checkDataType(port.data):
                        matching_ports.append(port)
                # if not, just check against port spec
                else:
                    # call checker from inport since they are
                    # the limiting factor
                    if self.checkTypeAgainstPort(port):
                        matching_ports.append(port)

        return matching_ports

    def incomingDataTypeMatches(self):
        indata = self.getUpstreamData()
        if indata is not None:
            return self.checkDataType(indata)
        else:
            return False

    def checkUpstreamPortType(self):
        uport = self.getUpstreamPort()
        if uport.data is not None:
            return self.checkDataType(uport.data)
        else:
            return self.checkTypeAgainstPort(uport)

    def type(self):  # generic object type
        return InPort.Type

    def porttype(self):
        return InPort.PortType

    def getUpstreamData(self):
        # first check if there is any data
        if len(self.edgeList) > 0:
            return self.edgeList[0].sourcePort().data
        else:
            return None

    def getUpstreamPort(self):
        # first check if there is any data
        if len(self.edgeList) > 0:
            return self.edgeList[0].sourcePort()
        else:
            return None

    def getUpstreamNode(self):
        '''Return node ref in a list.
        '''
        c = []
        if self.getUpstreamPort():
            c.append(self.getUpstreamPort().getNode())
        return c

    def setREQUIRED(self):
        self._obligation = REQUIRED
        log.debug("set REQUIRED")
        return self

    def setOPTIONAL(self):
        self._obligation = OPTIONAL
        log.debug("set OPTIONAL")
        return self

    def isOPTIONAL(self):
        return self._obligation == OPTIONAL

    def isREQUIRED(self):
        return self._obligation == REQUIRED


class OutPort(Port):
    '''Defines the specific behavior for connecting to outports i.e. how to 
    check for downstream data types for scaling downstream ports on the canvas
    to highlight potentially valid connections.
    '''

    PortType = OutPortTYPE

    def __init__(self, nodeWidget, CanvasBackend, title, portNum, intype=None, dtype=None, ndim=None, obligation=None, menuWidget=None):
        super(OutPort, self).__init__(nodeWidget, CanvasBackend,
                                      title, portNum, intype, dtype, ndim, menuWidget)

        self.data_changed = True  # don't start in warning state

    def setDataCalled(self, called=True):
        self.data_changed = called

    def dataHasChanged(self):
        '''Used for setting port color and signaling downstream events.
        '''
        return self.data_changed

    def dataIsNone(self):
        return (self.data is None)

    def findMatchingInPorts(self, ports=None):
        if ports == None: ports = self.findOppositePorts()
        matching_ports = []

        if len(ports):
            # check data if available
            if not self.dataIsNone():
                for port in ports:
                    # skip ports on the same node
                    if port.node == self.node:
                        continue
                    if not len(port.edges()):  # dont consider ports with connections
                        if port.checkDataType(self.data):
                            matching_ports.append(port)

            # if not, just check against port spec
            else:
                for port in ports:
                    # skip ports on the same node
                    if port.node == self.node:
                        continue
                    if not len(port.edges()):  # dont consider ports with connections
                        # call checker from inport since they are
                        # the limiting factor
                        if port.checkTypeAgainstPort(self):
                            matching_ports.append(port)

        return matching_ports

    def type(self):
        return OutPort.Type

    def porttype(self):
        return OutPort.PortType

    # return a read-only ptr
    @property
    def data(self):
        return self._data

    def freeDataQuietly(self):
        '''Quietly free (remove ref) the data causing no new events.
        All connected downstream nodes must run before this is freed.
        '''
        self._data = None

    def getDataString(self):
        # PORTAUTH
        return self._GPIType.edgeTip(self._data)

    def setWidgetData(self):  # widget-ports
        val = self.menuWidget.get_val()
        # This comparison could be an expensive operation
        # not sure if ids are checked first.
        if self._data != val:
            if self.setData(val):  # check val against port type
                return True
        return False  # data didn't change

    def setData(self, out):
        # PORTAUTH
        # enforce port type
        if self.checkDataType(out):
            self._data = self._GPIType.setDataAttr(out)
            self.setDataCalled()
            return True  # SUCCESS

        elif out is None:
            #log.warn("setData(): OutPort unchanged.")
            self._data = None
            #self.setDataCalled()
            #return True  # SUCCESS

        else:
            log.warn("setData(\'"+stw(self.portTitle)+"\',...): OutPort type doesn't match data, unchanged.")

        self.setDataCalled(False)
        return False

    def setDownstreamEvents(self):
        '''Look at downstream Nodes and flag pending_event regardless of obligation.
            -Finds inports connected to THIS outport.
        '''
        for nodeObj in self.getDownstreamNodes():
            # nodeObj[node,portTitle]
            # if self.isWidgetPort():
            #    print "setDownstreamEvents(): Send widget-event down to: "+node.name
            # else:
            #    print "setDownstreamEvents(): Send event down to: "+node.name
            nodeObj[0].setEventStatus({GPI_PORT_EVENT: nodeObj[1]})
