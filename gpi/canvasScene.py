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
from .port import InPort, OutPort, Port
from .edge import Edge
from .macroNode import PortEdge
from .node import Node
from .defines import GPI_PORT_EVENT
from .defines import getKeyboardModifiers, printMouseEvent
from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)


class CanvasScene(QtWidgets.QGraphicsScene):
    '''Supports the main canvas widget by drawing shapes for displaying
    interactions between elements on the canvas (e.g. selecting nodes). '''

    def __init__(self, parent=None):
        super(CanvasScene, self).__init__(parent)

        self.graph = parent
        self.line = None
        self.rubberBand = None
        self.origin = QtCore.QPointF()

        # during a port connection this is used to hold
        # a list of matching port types for highlighting
        self.portMatches = []

    def startLineDraw(self, event):
        # highlight all ports that match
        startItems = self.items(event.scenePos())
        if len(startItems):
            if isinstance(startItems[0], OutPort):
                if QtCore.Qt.AltModifier == getKeyboardModifiers():
                    startItems[0].toggleMemSaver()
                    return
                self.portMatches = startItems[0].findMatchingInPorts()
                for port in self.portMatches:
                    port.scaleUp()
                self.graph.viewAndSceneForcedUpdate()

            if isinstance(startItems[0], InPort):
                self.portMatches = startItems[0].findMatchingOutPorts()
                for port in self.portMatches:
                    port.scaleUp()
                self.graph.viewAndSceneForcedUpdate()

        self.line = QtWidgets.QGraphicsLineItem(
            QtCore.QLineF(event.scenePos(), event.scenePos()))
        fade = QtGui.QColor(QtCore.Qt.red)
        fade.setAlpha(150)
        self.line.setPen(QtGui.QPen(fade, 2))
        self.line.setZValue(10)
        self.addItem(self.line)

    def midLineDraw(self, event):

        newLine = QtCore.QLineF(self.line.line().p1(), event.scenePos())
        self.line.setLine(newLine)

        # attach source or sink connection
        #if QtCore.Qt.AltModifier == getKeyboardModifiers():
        #    self.line.setPen(QtGui.QPen(QtCore.Qt.blue, 2))
        #    self.dumpCursorStack()
        #    QtWidgets.QApplication.setOverrideCursor(
        #        QtGui.QCursor(QtCore.Qt.CrossCursor))
        #    return
        #else:
        #    self.line.setPen(QtGui.QPen(QtCore.Qt.red, 2))

        startItems = self.items(event.scenePos())
        if len(startItems) and startItems[0] == self.line:
            startItems.pop(0)

        self.dumpCursorStack()
        QtWidgets.QApplication.setOverrideCursor(
            QtGui.QCursor(QtCore.Qt.ForbiddenCursor))

        if len(startItems):
            if isinstance(startItems[0], Port):
                self.dumpCursorStack()
                QtWidgets.QApplication.setOverrideCursor(
                    QtGui.QCursor(QtCore.Qt.CrossCursor))

    def endLineDraw(self, event):
        self.dumpCursorStack()
        QtWidgets.QApplication.setOverrideCursor(
            QtGui.QCursor(QtCore.Qt.OpenHandCursor))
        QtWidgets.QApplication.restoreOverrideCursor()

        startItems = self.items(self.line.line().p1())

        # if there are no valid start items then mark for removal
        if len(startItems) and startItems[0] == self.line:
            startItems.pop(0)

        # reset any hovering events
        if len(startItems):
            if isinstance(startItems[0], Port):
                startItems[0].hoverLeaveEvent(event)

        # if there are no valid end items then mark for removal
        endItems = self.items(self.line.line().p2())
        if len(endItems) and endItems[0] == self.line:
            endItems.pop(0)

        # remove temporary drag line
        self.removeItem(self.line)
        self.line = None

        # if there are valid start and end items then continue
        if len(startItems) and len(endItems):

            # connect ports
            if isinstance(startItems[0], Port) and isinstance(endItems[0], Port) \
                    and startItems[0] != endItems[0] and type(startItems[0]) != type(endItems[0]):

                # find which is which
                if isinstance(startItems[0], InPort):
                    inport = startItems[0]
                    outport = endItems[0]
                else:
                    inport = endItems[0]
                    outport = startItems[0]

                # check if the ports belong to the same node
                if inport.node == outport.node:
                    log.warn("CanvasScene: inport and outport belong to the same node.")
                    super(CanvasScene, self).mouseReleaseEvent(event)
                    return

                # check the number of connections on the inport
                # if one exists then skip
                if len(inport.edges()) > 0:
                    log.warn("CanvasScene: inport occupied, connection dropped")
                    super(CanvasScene, self).mouseReleaseEvent(event)
                    return

                # This, currently, is the only way edges know
                # which port is actually a source or dest.
                # NOTE: Network description files will have to enforce this.
                newEdge = Edge(outport, inport)
                self.addItem(newEdge)

                # if its cyclic then don't allow the connection
                # -at the same time, calculate the hierarchy
                nodeHierarchy = inport.getNode().graph.calcNodeHierarchy()
                if nodeHierarchy is None:
                    self.removeItem(newEdge)
                    newEdge.detachSelf()
                    # del newEdge
                    log.warn("CanvasScene: cyclic, connection dropped")
                else:
                    # CONNECTION ADDED
                    # Since node hierarchy is recalculated, also
                    # take the time to flag nodes for processing
                    # 1) check for matching spec type
                    if not (inport.checkUpstreamPortType()):
                        self.removeItem(newEdge)
                        newEdge.detachSelf(update=False)
                        # del newEdge
                        log.warn("CanvasScene: data type mismatch, connection dropped")
                    else:
                        # 2) set the downstream node's pending_event
                        inport.getNode().setEventStatus({GPI_PORT_EVENT: inport.portTitle})

                        # trigger a force recalculation
                        inport.getNode().graph.itemMoved()

                        # trigger name update
                        inport.getNode().refreshName()
                        outport.getNode().refreshName()

                        # trigger event queue, if its idle
                        inport.getNode().graph._switchSig.emit('check')

                        if len(self.portMatches):
                            for port in self.portMatches:
                                port.resetScale()
                            self.portMatches = []

                        inport.edges()[0].adjust()
                        for edge in outport.edges():
                            edge.adjust()

            # remove edge by drawing a line across it
            elif isinstance(startItems[0], Edge) and isinstance(startItems[0], Edge) and startItems[0] == endItems[0]:
                # remove from scene
                self.removeItem(startItems[0])
                # remove from ports
                startItems[0].detachSelf()
                # remove from memory
                # del startItems[0]
        # reset the port size changes during port connect.
        if len(self.portMatches):
            for port in self.portMatches:
                port.resetScale()
            self.portMatches = []
        self.line = None

    def dumpCursorStack(self):
        while QtWidgets.QApplication.overrideCursor():
            QtWidgets.QApplication.restoreOverrideCursor()

    def mousePressEvent(self, event):  # CANVAS SCENE
        printMouseEvent(self, event)
        modifiers = getKeyboardModifiers()

        # allow graphics view panning
        if self.graph._panning:
            event.ignore()
            return

        # if its not a port, then don't draw a line
        modmidbutton_event = (event.button() == QtCore.Qt.LeftButton
                              and modifiers == QtCore.Qt.AltModifier)

        if ((event.button() == QtCore.Qt.LeftButton) or (event.button() == QtCore.Qt.MidButton) or modmidbutton_event) \
                and isinstance(self.itemAt(event.scenePos(), QtGui.QTransform()), Port):
            event.accept()
            self.startLineDraw(event)
        # rubber band select
        # elif ((event.button() == QtCore.Qt.MidButton) or modmidbutton_event):
        elif ((event.button() == QtCore.Qt.LeftButton) \
                and not isinstance(self.itemAt(event.scenePos(), QtGui.QTransform()), Node) \
                and not isinstance(self.itemAt(event.scenePos(), QtGui.QTransform()), PortEdge)):
            event.accept()
            self.unselectAllItems()  # reset select before making another
            self.origin = event.scenePos()
            self.rubberBand = QtWidgets.QGraphicsRectItem(
                QtCore.QRectF(self.origin, QtCore.QSizeF()))
            self.rubberBand.setPen(QtGui.QPen(
                QtCore.Qt.gray, 0, QtCore.Qt.SolidLine))
            self.rubberBand.setBrush(QtGui.QBrush(QtCore.Qt.lightGray))
            self.rubberBand.setZValue(0)
            self.addItem(self.rubberBand)
        else:
            QtWidgets.QApplication.restoreOverrideCursor()
            event.ignore()
            super(CanvasScene, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):  # CANVAS SCENE

        # allow graphics view panning
        if self.graph._panning:
            event.ignore()
            return

        if self.line:
            event.accept()
            self.midLineDraw(event)
        elif self.rubberBand:
            event.accept()
            newRect = QtCore.QRectF(self.origin, event.scenePos())
            self.rubberBand.setRect(newRect)
        else:
            event.ignore()
            self.dumpCursorStack()
            super(CanvasScene, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # CANVAS SCENE

        # allow graphics view panning
        if self.graph._panning:
            event.ignore()
            return

        printMouseEvent(self, event)
        if self.line:
            event.accept()
            self.endLineDraw(event)
        elif self.rubberBand:
            event.accept()
            selarea = self.rubberBand.rect()
            self.setSelectedNodes(selarea)
            self.removeItem(self.rubberBand)
            self.rubberBand = None
        else:
            event.ignore()
            self.line = None
            super(CanvasScene, self).mouseReleaseEvent(event)

    def unselectAllItems(self):
        # TODO: add Z level changes here too
        for item in list(self.items()):
            if item.isSelected():
                item.setSelected(False)

    def setSelectedItems(self, box):
        self.unselectAllItems()
        for item in self.items(box):
            item.setSelected(True)

    def setSelectedNodes(self, box):
        self.unselectAllItems()
        for item in self.items(box):
            if isinstance(item, Node):
                item.setSelected(True)

    def makeOnlyTheseNodesSelected(self, nodes):
        # need to distinguish between nodes and other items
        self.unselectAllItems()
        for node in nodes:
            node.setSelected(True)
            node.update()
