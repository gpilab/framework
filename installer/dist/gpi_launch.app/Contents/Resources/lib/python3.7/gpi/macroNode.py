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


import math
from gpi import QtCore, QtGui, QtWidgets

# gpi
from .defaultTypes import GPITYPE_PASS
from .defines import MacroNodeEdgeType, EdgeNodeType, PortEdgeType, GPI_APPLOOP
from .defines import printMouseEvent, getKeyboardModifiers, OPTIONAL
from .defines import isMacroChildNode
from .layoutWindow import LayoutMaster
from .logger import manager
from .nodeAPI import NodeAPI
from .node import Node, node_font

# start logger for this module
log = manager.getLogger(__name__)


class EdgeNode(QtWidgets.QGraphicsObject, QtWidgets.QGraphicsItem):
    '''The EdgeNode simply forwards port connections.  It can take one OutPort
    connection, and multiple InPort connections. InPort tooltips and
    enforcement are concatenated and forwarded.
    '''

    Type = EdgeNodeType

    def __init__(self, portNum, parentItem):
        super(EdgeNode, self).__init__()

        self.setParentItem(parentItem)

        # position
        self.portNum = portNum

        # attached ports
        self.portList = []

    def type(self):
        return self.Type


class MacroAPI(NodeAPI):
    '''A class that has default operations that stub-out the NodeAPI.
    '''

    def initUI(self):
        pass

        # self._layoutWindow = canvasGraph.LayoutMaster(self.node.graph, 0)
        # self.layout.addWidget(self._layoutWindow, 0, 0)

    def execType(self):
        return GPI_APPLOOP

    def validate(self):
        '''Copy all inputs to outputs.
        '''
        return 0

    def compute(self):
        '''Copy all inputs to outputs.
        '''
        for i in range(self.node._numPorts):
            self.setData('out' + str(i + 1), self.getData('in' + str(i + 1)))
        return 0


class PortEdge(Node):
    '''The PortEdge holds EdgeNodes for the MacroNode (they are the two node
    like pieces that bound the macro and the single collapsed macro
    representation).
    '''

    Type = PortEdgeType

    def __init__(self, macroParent, graph, menu=None, nodeIF=None, nodeIFscroll=None, role=None):
        super(PortEdge, self).__init__(graph, nodeMenuClass=menu, nodeCatItem=None, nodeIF=nodeIF, nodeIFscroll=nodeIFscroll)

        self._roles = ['Input', 'Output', 'Macro']
        self._role = self._roles[role]
        self.name = self._role
        self._label = ''
        self._title_delimiter = ': '
        self._macro_prefix = '*'

        self._macroParent = macroParent
        self._isMacroNode = False
        if self._macroParent:
            self._isMacroNode = True

        # code name for network loader to ignore
        self._moduleName = '__GPIMacroNode__'

        self._macroEdges = []

        # Ports
        if self._role == 'Macro':
            self._numPorts = 0
        else:
            self._numPorts = 16

        for i in range(self._numPorts):
            self.addInPort('in' + str(i + 1), GPITYPE_PASS, obligation=OPTIONAL)
            self.addOutPort('out' + str(i + 1), GPITYPE_PASS)

        self._nodeIF.setTitle(self.name)

    def menu(self):

        self._macroParent._scrollArea_layoutWindow.show()
        self._macroParent._scrollArea_layoutWindow.raise_()
        # self._macroParent._scrollArea_layoutWindow.activateWindow()

        # self._macroParent._layoutWindow.show()
        # self._macroParent._layoutWindow.raise_()
        self._macroParent._layoutWindow.activateWindow()

    def closeMacroLayout(self):
        if hasattr(self._nodeIF, '_layoutWindow'):  # sibling safe
            log.debug("Macro Node issuing a force close on layout")
            self._nodeIF._layoutWindow.forceClose()
            # return self._nodeIF._layoutWindow.close()
        # return True

    def getSiblingNodes(self):
        return self._macroParent.getNodes()

    def macroParent(self):
        return self._macroParent

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            for edge in self._macroEdges:
                edge.adjust()
        return super(PortEdge, self).itemChange(change, value)

    def type(self):
        return self.Type

    def addMacroEdge(self, edge):
        self._macroEdges.append(edge)
        edge.adjust()

    def mousePressEvent(self, event):
        printMouseEvent(self, event)
        modifiers = getKeyboardModifiers()

        self.update()  # update node color
        modmidbutton_event = (event.button() == QtCore.Qt.LeftButton
                              and modifiers == QtCore.Qt.AltModifier)
        if event.button() == QtCore.Qt.MidButton or modmidbutton_event:
            event.accept()
        elif event.button() == QtCore.Qt.LeftButton:
            event.accept()  # this has to accept to be moved
        elif event.button() == QtCore.Qt.RightButton:
            event.accept()
        else:
            event.ignore()
        super(PortEdge, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        printMouseEvent(self, event)
        modifiers = getKeyboardModifiers()

        self.update()
        modmidbutton_event = (event.button() == QtCore.Qt.LeftButton
                              and modifiers == QtCore.Qt.AltModifier)
        if event.button() == QtCore.Qt.MidButton or modmidbutton_event:
            event.accept()
        elif event.button() == QtCore.Qt.LeftButton:
            event.accept()  # this has to accept to be moved
        elif event.button() == QtCore.Qt.RightButton:
            event.accept()
            # self.menu()
            # self.graph.scene().makeOnlyTheseNodesSelected([self])
        else:
            event.ignore()
        super(PortEdge, self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        event.accept()
        log.debug("double-clicked PortEdge")
        self._macroParent.toggleCollapse()

    def getTitleWidth(self):
        '''Determine how long the module box is.'''
        buf = self.getMacroNodeName()
        fm = QtGui.QFontMetricsF(self.title_font)
        bw = fm.width(buf) + 11.0
        bh = fm.height()
        return (bw, bh)

    def getRoleTitleSize(self):
        buf = self._role
        fm = QtGui.QFontMetricsF(self.title_font)
        bw = fm.width(buf)
        bh = fm.height()
        return (bw, bh)

    def getTitleDelimiterSize(self):
        buf = self._title_delimiter
        fm = QtGui.QFontMetricsF(self.title_font)
        bw = fm.width(buf)
        bh = fm.height()
        return (bw, bh)

    def getNodeWidth(self):
        return max(self.getMaxPortWidth(), self.getTitleWidth()[0])

    def getMacroNodeName(self):
        '''The name is based on the Macro Node's role within the macro
        framework.
        '''
        buf = self._role
        if self._role == 'Input':
            if self._macroParent._label != '':
                buf += self._title_delimiter + self._macroParent._label
        elif self._role == 'Output':
            if self._macroParent._label != '':
                buf += self._title_delimiter + self._macroParent._label
        elif self._role == 'Macro':
            if self._macroParent._label != '':
                buf = self._macro_prefix + self._macroParent._label

        return buf

    def paint(self, painter, option, widget):  # NODE

        w = self.getNodeWidth()
        # h = self.getTitleWidth()[1]

        # draw shadow
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.darkGray)
        painter.drawRoundedRect(-8, -8, w, 20, 3, 3)

        # choose module color
        gradient = QtGui.QRadialGradient(-10, -10, 40)

        # update the face node based on the state of internal nodes.
        if self._role == 'Macro':
            if self._macroParent.isProcessing():
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.gray).lighter(70))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.darkGray).lighter(70))
            elif (option.state & QtWidgets.QStyle.State_Sunken) or (self._macroParent.inComputeErrorState()):
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.red).lighter(150))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.red).lighter(170))
            elif self._macroParent.inValidateErrorState():
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.yellow).lighter(190))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.yellow).lighter(170))
            elif self._macroParent.inInitUIErrorState():
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.red).lighter(150))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.yellow).lighter(170))
            else:
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.gray).lighter(150))
                gradient.setColorAt(
                    1, QtGui.QColor(QtCore.Qt.darkGray).lighter(150))

        # let the src and sink nodes update themselves normally
        else:
            conf = self.getCurState()
            if self._computeState is conf:
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.gray).lighter(70))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.darkGray).lighter(70))
            elif (option.state & QtWidgets.QStyle.State_Sunken) or (self._computeErrorState is conf):
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.red).lighter(150))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.red).lighter(170))
            elif self._validateError is conf:
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.yellow).lighter(190))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.yellow).lighter(170))
            else:
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.gray).lighter(150))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.darkGray).lighter(150))

        # draw module box (apply color)
        painter.setBrush(QtGui.QBrush(gradient))
        if self.beingHovered or self.isSelected():
            #painter.setPen(QtGui.QPen(QtCore.Qt.red, 1))
            fade = QtGui.QColor(QtCore.Qt.red)
            fade.setAlpha(100)
            painter.setPen(QtGui.QPen(fade, 2))
        else:
            #painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
            fade = QtGui.QColor(QtCore.Qt.black)
            fade.setAlpha(50)
            painter.setPen(QtGui.QPen(fade,0))

        painter.drawRoundedRect(-10, -10, w, 20, 3, 3)

        # title
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
        painter.setFont(self.title_font)

        buf = self.getMacroNodeName()

        # paint the node title
        painter.drawText(-5, -9, w, 20, (QtCore.Qt.AlignLeft |
                         QtCore.Qt.AlignVCenter), str(buf))


class MacroNodeEdge(QtWidgets.QGraphicsObject, QtWidgets.QGraphicsItem):
    """Provides the connection graphic and logic for nodes.
    -No enforcement, just methods to retrieve connected nodes.
    """
    Type = MacroNodeEdgeType
    Pi = math.pi
    TwoPi = 2.0 * Pi

    def __init__(self, source, dest):
        super(MacroNodeEdge, self).__init__()

        self.setZValue(0)

        self.source = source  # PortEdge(pos, self)
        self.dest = dest  # PortEdge(QtCore.QPointF(0, 30)+pos, self)

        self.arrowSize = 20.0
        self.penWidth = 10.0
        self.sourcePoint = QtCore.QPointF()
        self.destPoint = QtCore.QPointF()

        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)

        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.source.addMacroEdge(self)
        self.dest.addMacroEdge(self)
        self.adjust()

        self.fontHeight = 20

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            # call adjustments or updates to position here
            pass
        return super(MacroNodeEdge, self).itemChange(change, value)

    def type(self):
        return self.Type

    def sourceNode(self):
        return self.source

    def setSourceNode(self, node):
        self.source = node
        self.adjust()

    def destNode(self):
        return self.dest

    def setDestNode(self, node):
        self.dest = node
        self.adjust()

    def adjust(self):
        if not self.source or not self.dest:
            return

        # line = QtCore.QLineF(self.mapFromItem(self.source, 0, 0)+self.source.line().p1(),
        # self.mapFromItem(self.dest, 0, 0)+self.dest.line().p1())
        line = QtCore.QLineF(self.mapFromItem(self.source, 0, 0),
                             self.mapFromItem(self.dest, 0, 0))

        self.prepareGeometryChange()

        self.sourcePoint = line.p1()
        self.destPoint = line.p2()

    def boundingRect(self):
        if not self.source or not self.dest:
            return QtCore.QRectF()

        extra = (self.penWidth + self.arrowSize) / 2.0
        extra = max(extra, self.fontHeight)

        return QtCore.QRectF(self.sourcePoint,
                             QtCore.QSizeF(
                             self.destPoint.x() - self.sourcePoint.x(),
                             self.destPoint.y() - self.sourcePoint.y())).normalized().adjusted(-extra, -extra, extra, extra)

    def paint(self, painter, option, widget):
        if not self.source or not self.dest:
            return

        # Draw the line itself.
        line = QtCore.QLineF(self.sourcePoint, self.destPoint)

        if line.length() == 0.0:
            return

        painter.setPen(
            QtGui.QPen(QtCore.Qt.gray, self.penWidth, QtCore.Qt.SolidLine,
                       QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        painter.drawLine(line)

        # drawing text
        x = (line.x1() + line.x2()) / 2.0
        y = (line.y1() + line.y2()) / 2.0
        xa = (line.x1() - line.x2())
        ya = (line.y1() - line.y2())
        m = math.sqrt(xa * xa + ya * ya)
        a = math.atan2(ya, xa) * 180.0 / math.pi
        buf = "Macro"
        f = QtGui.QFont(node_font, 20)
        fm = QtGui.QFontMetricsF(f)
        bw = fm.width(buf)
        bw2 = -bw * 0.5
        # bh = fm.height()

        # Draw the arrows if there's enough room.
        angle = math.acos(line.dx() / line.length())
        if line.dy() >= 0:
            angle = self.TwoPi - angle

        sourceArrowP1 = self.sourcePoint + QtCore.QPointF(
            math.sin(angle + self.Pi / 3) * self.arrowSize,
            math.cos(angle + self.Pi / 3) * self.arrowSize)
        sourceArrowP2 = self.sourcePoint + QtCore.QPointF(
            math.sin(angle + self.Pi - self.Pi / 3) * self.arrowSize,
            math.cos(angle + self.Pi - self.Pi / 3) * self.arrowSize)
        destArrowP1 = self.destPoint + QtCore.QPointF(
            math.sin(angle - self.Pi / 3) * self.arrowSize,
            math.cos(angle - self.Pi / 3) * self.arrowSize)
        destArrowP2 = self.destPoint + QtCore.QPointF(
            math.sin(angle - self.Pi + self.Pi / 3) * self.arrowSize,
            math.cos(angle - self.Pi + self.Pi / 3) * self.arrowSize)

        painter.setBrush(QtCore.Qt.gray)
        painter.drawPolygon(
            QtGui.QPolygonF([line.p1(), sourceArrowP1, sourceArrowP2]))
        painter.drawPolygon(
            QtGui.QPolygonF([line.p2(), destArrowP1, destArrowP2]))

        # drawing text
        painter.setFont(f)
        painter.setPen(QtGui.QPen(QtCore.Qt.darkGray, 1))
        painter.save()
        painter.translate(QtCore.QPointF(x, y))
        if m > bw * 1.1:
            if a > 90 or a < -90:
                painter.rotate(a + 180.0)
                painter.drawText(QtCore.QPointF(bw2, -5.0), buf)
            else:
                painter.rotate(a)
                painter.drawText(QtCore.QPointF(bw2, -5.0), buf)
        else:
            painter.drawText(QtCore.QPointF(bw2, -5.0), '')
        painter.restore()


class MacroNode(object):
    '''The MacroNode menu is a stripped down version of the Node class with
    the capability of using a "Layout Window" instead of a NodeMenu.
    '''

    def __init__(self, graph, pos):
        self._graph = graph

        self._id = id(self)

        self._label = ''
        self._scrollArea_layoutWindow = None
        self._layoutWindow = None
        self.newLayoutWindow(config=0)

        self._collapsed = False
        # for load/paste
        self._destined_collapse = False

        # connected node groups
        self._src_cn = []
        self._sink_cn = []
        self._encap_nodes = []
        self._encap_nodepos = []

        self._src = PortEdge(self, graph, MacroAPI, role=0)
        self._src.setPos(pos)

        # self._sink = PortEdge(self, graph, nodeIF=self._src._nodeIF,
        # nodeIFscroll=self._src._nodeIF_scrollArea)
        self._sink = PortEdge(self, graph, MacroAPI, role=1)
        self._sink.setPos(QtCore.QPointF(0, 100) + pos)
        self._sink_pos = QtCore.QPointF(0, 100) + pos

        self._face = PortEdge(self, graph, MacroAPI, role=2)
        self._face.setPos(pos)
        self._face.inportList = []
        self._face.outportList = []

        # save expanded positions
        self._src_exppos = self._src.getPos()
        self._sink_exppos = self._sink.getPos()
        self._face_colpos = self._face.getPos()

        self._macroedge = MacroNodeEdge(self._src, self._sink)

        self._graph.scene().addItem(self._src)
        self._graph.scene().addItem(self._sink)
        self._graph.scene().addItem(self._macroedge)
        self._graph.scene().addItem(self._face)
        self._face.hide()

        self._anim_timeline = None
        self._anim = None

        self._scrollArea_layoutWindow.setWindowTitle('Macro')

    def getSettings(self):
        '''Keep all the settings required to instantiate the macro.
            -position, connectivity are all kept by normal serialization.
            -need collapse, label, layoutWindow.
        '''
        s = {}
        s['id'] = self.getID()
        s['label'] = self._label
        s['collapse'] = self.isCollapsed()
        s['layoutWindow'] = self._layoutWindow.getSettings()

        s['src_settings'] = self._src.getSettings()
        #s['src_pos'] = self._src_exppos
        s['sink_settings'] = self._sink.getSettings()
        #s['sink_pos'] = self._sink_exppos
        s['face_settings'] = self._face.getSettings()
        #s['face_pos'] = self._face_colpos

        x = self._sink_exppos[0] - self._src_exppos[0]
        y = self._sink_exppos[1] - self._src_exppos[1]
        s['rel_jaw_pos'] = [x, y]

        if self.isCollapsed():
            # save relative node positions in dict with id as the key
            # ids can be used at deserializing by lookup.
            npos = {}
            for node, rel in zip(self._encap_nodes, self._encap_nodepos):
                npos[str(node.getID())] = [rel.x(), rel.y()]
            s['nodes_rel_pos'] = npos

        return s

    def getNodeByID(self, buf, nid):
        for item in buf:
            if isinstance(item, Node):
                if item.getID() == nid:
                    return item

    def loadSettings(self, s, nodeList, pos):
        '''load all settings from a description generated by getSettings()
        '''
        self.setID(s['id'])
        self.setLabelWdg(s['label'])
        self.setLabel(s['label'])

        self.newLayoutWindowFromSettings(s['layoutWindow'], nodeList)

        if s['collapse']:
            x = s['face_settings']['pos'][0] + pos[0]
            y = s['face_settings']['pos'][1] + pos[1]
            #x = s['src_pos'][0] + pos[0]
            #y = s['src_pos'][1] + pos[1]
            self._src.setPos(QtCore.QPointF(x, y))

            # need relative jaw pos
            #x = s['sink_settings']['pos'][0] + pos[0]
            #y = s['sink_settings']['pos'][1] + pos[1]
            #self._sink.setPos(QtCore.QPoint(x, y))
            x += s['rel_jaw_pos'][0]
            y += s['rel_jaw_pos'][1]
            self._sink.setPos(QtCore.QPointF(x, y))

            x = s['face_settings']['pos'][0] + pos[0]
            y = s['face_settings']['pos'][1] + pos[1]
            self._face.setPos(QtCore.QPointF(x, y))

            rel = QtCore.QPointF(x, y)
            for nid, epos in list(s['nodes_rel_pos'].items()):
                enode = self.getNodeByID(nodeList, int(nid))
                if enode:
                    enode.setPos(rel + QtCore.QPointF(*epos))
                    log.debug("node found by nid: "+enode.name)
                    log.debug("pos: ")
                    log.debug(str(epos))
                    log.debug(str(rel))
                    log.debug(str(QtCore.QPointF(*epos)))
                    log.debug(str(rel + QtCore.QPointF(*epos)))
                else:
                    log.warn("nid not found: "+str(nid))

        else:
            x = s['src_settings']['pos'][0] + pos[0]
            y = s['src_settings']['pos'][1] + pos[1]
            self._src.setPos(QtCore.QPointF(x, y))

            x = s['sink_settings']['pos'][0] + pos[0]
            y = s['sink_settings']['pos'][1] + pos[1]
            self._sink.setPos(QtCore.QPointF(x, y))

            x = s['src_settings']['pos'][0] + pos[0]
            y = s['src_settings']['pos'][1] + pos[1]
            self._face.setPos(QtCore.QPointF(x, y))

        self._src.setID(s['src_settings']['id'])
        self._sink.setID(s['sink_settings']['id'])
        self._face.setID(s['face_settings']['id'])

        # save expanded positions
        self._src_exppos = self._src.getPos()
        self._sink_exppos = self._sink.getPos()
        self._face_colpos = self._face.getPos()

        # self.setCollapse(s['collapse'])
        self._destined_collapse = s['collapse']

    def setID(self, val=None):
        if val is None:
            self._id = id(self)
        else:
            self._id = val

    def getID(self):
        return self._id

    def resetPortParents(self):
        '''Return the parent status of each port to their respective _src or
        _sink origin nodes.
        '''
        for port in self._src.inportList:
            port.setParentItem(self._src)
            port.resetPos()
            port.show()

        for port in self._sink.outportList:
            port.setParentItem(self._sink)
            port.resetPos()
            port.show()

    def showFacePorts(self):
        '''Set the parent of each borrowed port to be the face node.
        '''
        self._face.inportList = []
        self._face.outportList = []

        for ip, op in zip(self._src.inportList, self._src.outportList):
            if ip.edgeCount() or op.edgeCount():
                ip.setParentItem(self._face)
                ip.setPosByPortNum(len(self._face.inportList))
                self._face.inportList.append(ip)
                ip.show()
            else:
                ip.hide()

        for op, ip in zip(self._sink.outportList, self._sink.inportList):
            if ip.edgeCount() or op.edgeCount():
                op.setParentItem(self._face)
                op.setPosByPortNum(len(self._face.outportList))
                self._face.outportList.append(op)
                op.show()
            else:
                op.hide()

        self._face.update()

    def toggleCollapse(self):
        if self.isCollapsed():
            self.setCollapse(False)
        else:
            self.setCollapse(True)

    def isCollapsed(self):
        return self._collapsed

    def setCollapse(self, val):
        self._collapsed = val
        if self.isCollapsed():
            # only set it if its truly collapsible.
            if not self.collapseMacro():
                self._collapsed = False
        else:
            self.expandMacro()

    def setCollapse_NoAction(self, val):
        '''Just set the flag
        '''
        self._collapsed = val

    def shouldCollapse(self):
        '''for load/save, should this be collapsed?
        '''
        return self._destined_collapse

    def getNodes(self):
        return [self._src, self._sink, self._face]

    def resetIDs(self):
        '''After the node has been loaded and reconnected to its neighbors,
        reset the ID for future copy/paste or load/save uniqueness.
        '''
        self.setID()
        self._src.setID()
        self._sink.setID()
        self._face.setID()

    def deleteMacroEdge(self):
        '''The Macro-edge connecting the Input and Output nodes.
        '''
        if self._macroedge.scene():
            self._graph.scene().removeItem(self._macroedge)

    def closeLayoutWidget(self):
        # self._layoutWindow.close()
        self._scrollArea_layoutWindow.close()

    def readyForDeletion(self):
        self.closeLayoutWidget()
        self.deleteMacroEdge()

        # delete all encapsulated nodes if its collapsed
        if self.isCollapsed():
            for node in self._encap_nodes:
                if node.scene():
                    self._graph.deleteNode(node)

    def newLayoutWindowFromSettings(self, s, nodeList):
        '''Copied from canvasGraph.
        '''

        layoutwindow = LayoutMaster(self._graph, config=s['config'], macro=True, labelWin=True)
        layoutwindow.loadSettings(s, nodeList)
        layoutwindow.setWindowTitle('Macro')
        layoutwindow.wdglabel.textChanged.connect(self.setLabel)

        self._scrollArea_layoutWindow = QtWidgets.QScrollArea()
        self._scrollArea_layoutWindow.setWidget(layoutwindow)
        self._scrollArea_layoutWindow.setWidgetResizable(True)
        self._scrollArea_layoutWindow.setGeometry(50, 50, 300, 1000)

        layoutwindow.setGeometry(50, 50, 400, 300)
        self._layoutWindow = layoutwindow

    def newLayoutWindow(self, config):
        '''Copied from canvasGraph.
        '''

        layoutwindow = LayoutMaster(self._graph, config=config, macro=True, labelWin=True)
        layoutwindow.setWindowTitle('Macro')
        layoutwindow.wdglabel.textChanged.connect(self.setLabel)

        self._scrollArea_layoutWindow = QtWidgets.QScrollArea()
        self._scrollArea_layoutWindow.setWidget(layoutwindow)
        self._scrollArea_layoutWindow.setWidgetResizable(True)
        self._scrollArea_layoutWindow.setGeometry(50, 50, 300, 1000)

        layoutwindow.setGeometry(50, 50, 400, 300)
        self._layoutWindow = layoutwindow

    def setLabel(self, lab):
        '''Set the internal label buffer and update the display names for each
        node and node-menu-window.
        '''
        self._label = str(lab)

        # update the node-menu window title
        if self._label != '':
            self._scrollArea_layoutWindow.setWindowTitle('Macro: ' + self._label)
        else:
            self._scrollArea_layoutWindow.setWindowTitle('Macro')

        self._src.update()
        self._sink.update()
        self._face.update()

    def setLabelWdg(self, lab):
        '''Sets the QLineEdit label directly for re-instantiating purposes.
        '''
        self._layoutWindow.wdglabel.setText(lab)

    def getEncapsulatedNodes(self):
        return self._encap_nodes

    def listEncapsulatedNodes(self):
        '''Searches for all nodes connected to the output of the _src and the
        input of the _sink.
        '''
        all_cn = self._sink_cn + self._src_cn

        enc_nodes = []
        for cn in all_cn:
            if cn[0] != self._src and cn[0] != self._sink:
                enc_nodes.append(cn[0])
            if cn[1] != self._src and cn[1] != self._sink:
                enc_nodes.append(cn[1])

        self._encap_nodes = list(set(enc_nodes))

    def isProcessing(self):
        '''Look at the run status of all nodes in the macro to determine if
        macro is running.
        '''
        for node in self._encap_nodes:
            if node.isProcessingEvent():
                return True
        if self._src.isProcessingEvent():
            return True
        if self._src.isProcessingEvent():
            return True
        return False

    def inComputeErrorState(self):
        '''Look at the run status of all nodes in the macro to determine if
        macro is in error.
        '''
        for node in self._encap_nodes:
            if node.inComputeErrorState():
                return True
        if self._src.inComputeErrorState():
            return True
        if self._src.inComputeErrorState():
            return True
        return False

    def inInitUIErrorState(self):
        '''Look at the run status of all nodes in the macro to determine if
        macro is in error.
        '''
        for node in self._encap_nodes:
            if node.inInitUIErrorState():
                return True
        if self._src.inInitUIErrorState():
            return True
        if self._src.inInitUIErrorState():
            return True
        return False

    def inValidateErrorState(self):
        '''Look at the run status of all nodes in the macro to determine if
        macro is in warning state.
        '''
        for node in self._encap_nodes:
            if node.inValidateErrorState():
                return True
        if self._src.inValidateErrorState():
            return True
        if self._src.inValidateErrorState():
            return True
        return False

    def validateSinkNodes(self):
        '''Get the list of connected nodes for _sink macro nodes.
        Determine if the connections are valid, then list the valid nodes.
        '''
        # get _sink connections
        # throw out input connections (where THIS node is the source).
        src_tmp = self._sink.getConnectionTuples()
        src_cn = [cn for cn in src_tmp if cn[0] != self._sink]
        # store output connections for comparison
        src_out = [cn for cn in src_tmp if cn[0] == self._sink]
        src_ill = src_out[:]

        log.debug("downstream search")
        while True:

            # build a local connection list for all nodes in the next level
            lc = []
            for cn in src_out:

                # sources
                if cn[0] != self._sink:  # don't backtrack
                    for outport in cn[0].outportList:
                        lc += outport.getConnectionTuples()

                # sinks
                for inport in cn[1].inportList:
                    lc += inport.getConnectionTuples()

                # cyclic
                if cn[1] == self._src:
                    log.debug("illegal cn (sink validate):")
                    log.debug("\t"+cn[0].name +"->"+cn[1].name)
                    return 1

            # consolidate connections
            pre_len = len(src_out)
            src_out += lc
            src_out = list(set(src_out))

            # if no new connections were added, then quit
            if len(src_out) == pre_len:
                break

        if manager.isDebug():
            log.debug("before upstream search")
            for cn in src_cn:
                log.debug("\t"+cn[0].name +"->"+cn[1].name)

        while True:

            # build a local connection list for all nodes in the next level
            lc = []
            for cn in src_cn:

                # sources
                if cn[0] != self._src:
                    for outport in cn[0].outportList:
                        lc += outport.getConnectionTuples()
                    for inport in cn[0].inportList:
                        lc += inport.getConnectionTuples()

                # sinks
                if cn[1] != self._sink:
                    for inport in cn[1].inportList:
                        lc += inport.getConnectionTuples()
                    for outport in cn[1].outportList:
                        lc += outport.getConnectionTuples()

                # cyclic
                if cn[1] == self._src:
                    log.debug("illegal cn (sink validate):")
                    log.debug("\t"+cn[0].name +"->"+cn[1].name)
                    return 1

            # consolidate connections
            pre_len = len(src_cn)
            src_cn += lc
            src_cn = list(set(src_cn))

            # if no new connections were added, then quit
            if len(src_cn) == pre_len:
                break

        if manager.isDebug():
            log.debug("after search:")
            for cn in src_cn:
                log.debug("\t"+cn[0].name +"->"+cn[1].name)

        # determine if the macro is valid
        log.debug("illegal macro connections:")
        ill_cnt = 0
        for cn in src_cn:
            if cn in src_ill:
                ill_cnt += 1
                log.debug("\t"+cn[0].name +"->"+cn[1].name)

        # check for any other macro nodes
        for cn in src_cn:
            if isMacroChildNode(cn[0]):
                if cn[0] not in self.getNodes():
                    ill_cnt += 1

            if isMacroChildNode(cn[1]):
                if cn[1] not in self.getNodes():
                    ill_cnt += 1

        self._sink_cn = src_cn

        return ill_cnt

    def validateSrcNodes(self):
        '''Get the list of connected nodes for _src macro nodes.
        Determine if the connections are valid, then list the valid nodes.
        '''

        # get _src connections
        # throw out input connections (where THIS node is the sink).
        src_tmp = self._src.getConnectionTuples()
        src_cn = [cn for cn in src_tmp if cn[1] != self._src]
        # store input connections for comparison
        src_in = [cn for cn in src_tmp if cn[1] == self._src]

        if manager.isDebug():
            log.debug("before search")
            for cn in src_cn:
                log.debug("\t"+cn[0].name +"->"+cn[1].name)

        while True:

            # build a local connection list for all nodes in the next level
            lc = []
            for cn in src_cn:

                # sources
                if len(cn[0].getConnectionTuples()):
                    if cn[0] != self._src:  # don't backtrack
                        lc += cn[0].getConnectionTuples()

                # cyclic
                if cn[0] == self._sink:
                    log.debug("illegal cn (src validate):")
                    log.debug("\t"+cn[0].name +"->"+cn[1].name)
                    return 1

                # sinks
                if cn[1] != self._sink:
                    if len(cn[1].getConnectionTuples()):
                        lc += cn[1].getConnectionTuples()

            # consolidate connections
            pre_len = len(src_cn)
            src_cn += lc
            src_cn = list(set(src_cn))

            # if no new connections were added, then quit
            if len(src_cn) == pre_len:
                break

        if manager.isDebug():
            log.debug("after search:")
            for cn in src_cn:
                log.debug("\t"+cn[0].name +"->"+cn[1].name)

        # determine if the macro is valid
        log.debug("illegal macro connections:")
        ill_cnt = 0
        for cn in src_cn:
            if cn in src_in:
                ill_cnt += 1
                log.debug("\t"+cn[0].name +"->"+cn[1].name)

        # check for any other macro nodes
        for cn in src_cn:
            if isMacroChildNode(cn[0]):
                if cn[0] not in self.getNodes():
                    ill_cnt += 1

            if isMacroChildNode(cn[1]):
                if cn[1] not in self.getNodes():
                    ill_cnt += 1

        self._src_cn = src_cn

        return ill_cnt

    def saveNodePos(self):
        '''Run thru the list of encapsulated nodes and save their original
        relative position to the _src node.
        '''
        self._sink_pos = self._sink.pos() - self._src.pos()

        # save node-pos with parallel list to _encap_nodes
        self._encap_nodepos = []
        for node in self._encap_nodes:
            self._encap_nodepos.append(node.pos() - self._src.pos())

        # save the expanded sibling node positions
        self._src_exppos = self._src.getPos()
        self._sink_exppos = self._sink.getPos()

        return self._encap_nodepos

    def collapseMacro(self):

        if self.validateSrcNodes():
            return False

        if self.validateSinkNodes():
            return False

        self.listEncapsulatedNodes()

        if manager.isDebug():
            log.debug("nodes:")
            for node in self._encap_nodes:
                log.debug(node.name)

        self.saveNodePos()

        self._face.setPos(self._src.pos())

        # initialize animation stuff (close jaw)
        self._anim = QtCore.QParallelAnimationGroup()
        self._anim.finished.connect(self.jawClosed)
        anim = QtCore.QPropertyAnimation(self._sink, b"pos")
        anim.setDuration(300)
        anim.setEndValue(self._src.pos())
        self._anim.addAnimation(anim)

        for node in self._encap_nodes:
            anim = QtCore.QPropertyAnimation(node, b"pos")
            anim.setDuration(300)
            anim.setEndValue(self._src.pos())
            self._anim.addAnimation(anim)

        self._anim.start()

        return True

    def jawClosed(self):
        '''finish the collapse Macro animation by hiding all encapsulated nodes
        -connect all nodes
        '''
        # hide all the nodes and connect their update-signals to the macro
        for node in self._encap_nodes:
            node.hide()
            node._forceUpdate.connect(self.updateNodePainter)
            for edge in node.edges():
                edge.hide()

        self._sink.hide()
        self._src.hide()
        self._macroedge.hide()
        self._face.show()

        self.showFacePorts()

        for port in self._face.getPorts():
            port.updateEdges()

        # make sure the face is selected
        self._face.setSelected(True)
        self._src.setSelected(False)
        self._sink.setSelected(False)

    def updateNodePainter(self):
        '''Call the node updates for each of the bound nodes for re-coloring.
        '''
        if self.isCollapsed():
            self._face.forceUpdate_NodeUI()

    def jawOpen(self):
        '''Once the open animation is finished, disconnect the re-painting
        updater signal.
        '''
        for node in self._encap_nodes:
            node._forceUpdate.disconnect()
            node.setSelected(True)

        # make sure the end nodes are also selected
        self._face.setSelected(False)
        self._src.setSelected(True)
        self._sink.setSelected(True)

    def expandMacro(self):

        # before expansion save the face position for load/paste purposes
        self._face_colpos = self._face.getPos()

        self._src.setPos(self._face.pos())
        self._sink.setPos(self._src.pos())

        self._face.hide()
        self._macroedge.show()
        self._sink.show()
        self._src.show()
        self.resetPortParents()

        for port in self._src.getPorts():
            port.updateEdges()

        for port in self._sink.getPorts():
            port.updateEdges()

        for node in self._encap_nodes:
            node.setPos(self._src.pos())
            node.show()
            for edge in node.edges():
                edge.show()

        # initialize animation (open jaw)
        self._anim = QtCore.QParallelAnimationGroup()
        self._anim.finished.connect(self.jawOpen)
        anim = QtCore.QPropertyAnimation(self._sink, b"pos")
        anim.setDuration(300)
        anim.setEndValue(self._sink_pos + self._src.pos())
        self._anim.addAnimation(anim)

        for node, pos in zip(self._encap_nodes, self._encap_nodepos):
            anim = QtCore.QPropertyAnimation(node, b"pos")
            anim.setDuration(300)
            anim.setEndValue(pos + self._src.pos())
            self._anim.addAnimation(anim)

        self._anim.start()
