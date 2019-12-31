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
#
#    The code in this file was modifed/derived from the elasticnodes.py
#    example with the license:
#############################################################################
##
## Copyright (C) 2010 Riverbank Computing Limited.
## Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is part of the examples of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##
#############################################################################

import math
from gpi import QtCore, QtGui, QtWidgets

# gpi
from .defines import EdgeTYPE, GPI_PORT_EVENT
from .logger import manager
from .port import InPort, OutPort

# start logger for this module
log = manager.getLogger(__name__)


class EdgeTracer(QtWidgets.QGraphicsLineItem):
    '''When an edge is deleted it will be replaced with this static object for
    a few seconds and then remove itself.
    '''
    def __init__(self, graph, destPort, sourcePort):
        super(EdgeTracer, self).__init__()

        # show a faux copy of the delete menu
        menu = QtWidgets.QMenu()
        menu.addAction("Delete")

        # position of pipe end based on port type
        bindout_y = 5
        bindin_y = -1
        p1 = self.mapFromItem(sourcePort, 3.5, bindin_y)
        p2 = self.mapFromItem(destPort, 3.5, bindout_y)

        pos = graph.mapToGlobal(graph.mapFromScene((p1-p2)/2+p2))

        # render the menu without executing it
        try:
            # PyQt4
            menupixmap = QtGui.QPixmap().grabWidget(menu)
        except AttributeError:
            menupixmap = menu.grab()  # QtGui.QPixmap().grabWidget(menu)

        # round edges
        #mask = menupixmap.createMaskFromColor(QtGui.QColor(255, 255, 255), QtCore.Qt.MaskOutColor)
        #p = QtGui.QPainter(menupixmap)
        #p.setRenderHint(QtGui.QPainter.Antialiasing)
        #p.drawRoundedRect(0,0,menupixmap.width(),menupixmap.height(), 5,5)
        #p.drawPixmap(menupixmap.rect(), mask, mask.rect())
        #p.end()

        # display the menu image (as a dummy menu as its being built)
        # TODO: this could probably be moved to the FauxMenu
        self._tracer = QtWidgets.QLabel()
        self._tracer.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self._tracer.move(pos)
        self._tracer.setPixmap(menupixmap)
        self._tracer.show()
        self._tracer.raise_()

        # draw a faux selected line
        line = QtCore.QLineF(p1,p2)
        self.setPen(QtGui.QPen(QtGui.QColor(QtCore.Qt.red), 2, QtCore.Qt.DashLine,
                                      QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        self.setLine(line)
        self.setZValue(0)

        # cleanup both menu item and line by removing from scene (parent).
        self._timer = QtCore.QTimer()
        self._timer.singleShot(300, lambda: graph.scene().removeItem(self))


class Edge(QtWidgets.QGraphicsLineItem):
    """Provides the connection graphic and logic for nodes.
    -No enforcement, just methods to retrieve connected nodes.
    """
    Type = EdgeTYPE

    def __init__(self, sourcePort, destPort):
        super(Edge, self).__init__()

        self.sourcePoint = QtCore.QPointF()
        self.destPoint = QtCore.QPointF()

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)

        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.source = sourcePort
        self.dest = destPort
        self.source.addEdge(self)
        self.dest.addEdge(self)
        self.adjust()
        self.setZValue(1)

        self.setAcceptHoverEvents(True)
        self._beingHovered = False

    def connectedPortIsHovered(self):
        if self.source.BeingHovered() or self.dest.BeingHovered():
            self.setZValue(100)
            return True
        else:
            self.setZValue(1)
            return False

    def hoverEnterEvent(self, event):
        self._beingHovered = True
        self.setZValue(100)
        self.update()

    def hoverLeaveEvent(self, event):
        self._beingHovered = False
        self.setZValue(1)
        self.update()

    def type(self):
        return Edge.Type

    def sourcePort(self):
        if isinstance(self.source, InPort):
            log.critical("Edge: WARNING: sourcePort() is somehow an InPort instance! (Src: \'"+str(self.source.getName())+"\', Dst: \'"+str(self.dest.getName())+"\')")
        return self.source

    def isCyclicConnection(self):
        return self.sourcePort().allowsCyclicConn() or self.destPort().allowsCyclicConn()

    def getSourceCoords(self):
        c = {}
        c['nodeID'] = self.sourcePort().getNodeID()
        c['portID'] = self.sourcePort().getID()
        c['portName'] = self.sourcePort().portTitle
        c['portNum'] = self.sourcePort().portNum
        return c

    def getDestCoords(self):
        c = {}
        c['nodeID'] = self.destPort().getNodeID()
        c['portID'] = self.destPort().getID()
        c['portName'] = self.destPort().portTitle
        c['portNum'] = self.destPort().portNum
        return c

    def getCoords(self):  # EDGE SETTINGS
        c = {}
        c['src'] = self.getSourceCoords()
        c['dest'] = self.getDestCoords()
        return c

    def sourceNode(self):
        return self.source.getNode()

    def setSourcePort(self, port):
        self.source = port
        self.adjust()

    def destPort(self):
        if isinstance(self.dest, OutPort):
            log.critical("Edge: WARNING: destPort() is somehow an InPort instance!")
        return self.dest

    def destNode(self):
        return self.dest.getNode()

    def setDestPort(self, port):
        self.dest = port
        self.adjust()

    def detachSelf(self, update=True, tracer=False):  # EDGE
        '''update: triggers a processing event for OPTIONAL node obligation'''
        self.source.detachEdge(self)
        self.dest.detachEdge(self)

        # add tracer
        if tracer:
            self.dest.getNode().graph.scene().addItem(EdgeTracer(self.dest.getNode().graph, self.source, self.dest))

        if update:
            self.dest.getNode().graph.calcNodeHierarchy()
            self.dest.getNode().setEventStatus({GPI_PORT_EVENT: self.dest.portTitle})
            if self.dest.getNode().graph.inIdleState():
                self.dest.getNode().graph._switchSig.emit('check')

            self.dest.getNode().graph.viewAndSceneForcedUpdate()

    def adjust(self):
        if not self.source or not self.dest:
            return

        # position of pipe end based on port type
        bindout_y = 5
        bindin_y = 0
        if isinstance(self.source, InPort):
            line = QtCore.QLineF(self.mapFromItem(self.source, 3.5, bindin_y),
                                 self.mapFromItem(self.dest, 3.5, bindout_y))
        else:
            line = QtCore.QLineF(self.mapFromItem(self.source, 3.5, bindout_y),
                                 self.mapFromItem(self.dest, 3.5, bindin_y))

        self.prepareGeometryChange()

        self.sourcePoint = line.p1()
        self.destPoint = line.p2()

    def boundingRect(self):
        if not self.source or not self.dest:
            return QtCore.QRectF()

        penWidth = 2.0

        # extra padding for edge text
        #if self._beingHovered:
        #    extra = (penWidth + 10.0) / 2.0
        #else:
        extra = (penWidth + 30.0) / 2.0

        # http://lists.trolltech.com/qt-interest/2000-08/thread00439-0.html
        # bound = QRect(QPoint(min(p0.x(),p1.x(),p2.x(),p3.x()),
        #             min(p0.y(),p1.y(),p2.y(),p3.y())),
        #        QPoint(max(p0.x(),p1.x(),p2.x(),p3.x()),
        #             mxa(p0.y(),p1.y(),p2.y(),p3.y())));

        return QtCore.QRectF(self.sourcePoint,
                             QtCore.QSizeF(
                             self.destPoint.x() - self.sourcePoint.x(),
                             self.destPoint.y(
                             ) - self.sourcePoint.y(
                             ))).normalized().adjusted(-extra,
                                                       -extra, extra, extra)

    def shape(self):
        # hitbox for selecting
        path = super(Edge, self).shape()
        delta = QtCore.QPointF(3,3)  # padding to make it thicker
        line = QtGui.QPolygonF([self.sourcePoint+delta, self.destPoint+delta,
            self.destPoint-delta, self.sourcePoint-delta])
        path.addPolygon(line)
        return path

    def paint(self, painter, option, widget):  # EDGE
        if not self.source or not self.dest:
            return

        # Draw the line itself.
        line = QtCore.QLineF(self.sourcePoint, self.destPoint)

        if line.length() == 0.0:
            return

        if self.isSelected() or self._beingHovered or self.connectedPortIsHovered():
            fade = QtGui.QColor(QtCore.Qt.red)
            fade.setAlpha(200)
            #painter.setPen(QtGui.QPen(QtCore.Qt.red, 1, QtCore.Qt.DashLine,
            painter.setPen(QtGui.QPen(fade, 2, QtCore.Qt.SolidLine,
                                      QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        elif self.isCyclicConnection():
            painter.setPen(QtGui.QPen(QtCore.Qt.red, 2, QtCore.Qt.SolidLine,
                                      QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        else:
            fade = QtGui.QColor(QtCore.Qt.black)
            fade.setAlpha(150)
            #painter.setPen(QtGui.QPen(QtCore.Qt.black, 2, QtCore.Qt.SolidLine,
            painter.setPen(QtGui.QPen(fade, 2, QtCore.Qt.SolidLine,
                                      QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

        painter.drawLine(line)
        x = (line.x1()+line.x2())/2.0
        y = (line.y1()+line.y2())/2.0
        xa = (line.x1()-line.x2())
        ya = (line.y1()-line.y2())
        m = math.sqrt(xa*xa + ya*ya)
        a = math.atan2(ya, xa)*180.0/math.pi
        buf = self.source.getDataString()
        if self._beingHovered:
            f = QtGui.QFont("Times New Roman", 8)
        else:
            f = QtGui.QFont("Times New Roman", 6)
        fm = QtGui.QFontMetricsF(f)
        bw = fm.width(buf)
        bw2 = -bw*0.5
        #bh = fm.height()

        # bezier curves
        if False:
            sa = (a+90.)*0.5
            path = QtGui.QPainterPath(line.p1())
            path.cubicTo(x-sa, y-sa, x+sa, y+sa, line.x2(), line.y2())
            painter.drawPath(path)

        # bezier curves, change direction on the angle
        if False:
            sa = (a+90.)*0.5
            if a > 90 or a < -90:
                path = QtGui.QPainterPath(line.p1())
                path.cubicTo(x-sa, y-sa, x+sa, y+sa, line.x2(), line.y2())
                painter.drawPath(path)
            else:
                path = QtGui.QPainterPath(line.p1())
                path.cubicTo(x+sa, y+sa, x-sa, y-sa, line.x2(), line.y2())
                painter.drawPath(path)

        painter.setFont(f)
        if self._beingHovered:
            painter.setPen(QtGui.QPen(QtCore.Qt.red, 1))
        else:
            painter.setPen(QtGui.QPen(QtCore.Qt.darkGray, 1))

        painter.save()
        painter.translate(QtCore.QPointF(x, y))
        if m > bw*1.1 or self._beingHovered:
            if a > 90 or a < -90:
                painter.rotate(a+180.0)
                painter.drawText(QtCore.QPointF(bw2, -2.0), buf)
            else:
                painter.rotate(a)
                painter.drawText(QtCore.QPointF(bw2, -2.0), buf)
        else:
            painter.drawText(QtCore.QPointF(bw2, -2.0), '')
        painter.restore()
