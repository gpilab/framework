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

import gc
import os
import sys
import copy
import math
import time
import random


# gpi
import gpi
from gpi import QtCore, QtGui, QtWidgets
from .associate import Bindings, isGPIAssociatedFile, isGPIAssociatedExt
from .canvasScene import CanvasScene
from .cmd import Commands
from .defines import GPI_REQUEUE_EVENT, GPI_INIT_EVENT, GPI_WIDGET_EVENT
from .defines import getKeyboardModifiers, printMouseEvent, stw
from .defines import isMacroChildNode
from .defines import GetHumanReadable_bytes, GPI_APPLOOP, GetHumanReadable_time
from .defines import isGPINetworkFile, isGPIModFile
from .edge import Edge
from .layoutWindow import LayoutMaster
from .library import Library, NodeCatalogItem
from .macroNode import MacroNode
from .network import Network
from .node import Node
from .nodeQueue import GPINodeQueue
from .port import Port, InPort
from .stateMachine import GPI_FSM, GPIState
from . import topsort

from .logger import manager

# start logger for this module
log = manager.getLogger(__name__)

class GraphWidget(QtWidgets.QGraphicsView):
    '''Provides the main canvas widget and background painting as well as the
    execution model for the canvas.'''

    changed = gpi.Signal(QtCore.QMimeData)
    _switchSig = gpi.Signal(str)
    _switchSig_info = gpi.Signal(dict)
    _curState = gpi.Signal(dict)

    def __init__(self, title, parent):
        super(GraphWidget, self).__init__()

        # a link to the main window
        self.parent = parent
        self._title = title
        self._macroModule = False

        self.hotkeys = {}
        
        # canvas info
        self._starttime = 0
        self._walltime = 0  # time between idle states

        # node animation
        self._node_anim_timeline = None
        self._node_anims = []

        self._layoutwindowList = []

        self._proc = None  # reference point for threads

        self.timerId = 0
        self.nodeEvent_timerId = self.startTimer(1000)  # update time (msec)
        self.chargeRepON = False  # start off this way

        scene = CanvasScene(self)
        scene.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        ncscale = 4  # Network Canvas Size Scale
        scene.setSceneRect(
            -200 * ncscale, -200 * ncscale, 400 * ncscale, 400 * ncscale)
        self.setScene(scene)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheNone)  # required for repainting background
        self.setViewportUpdateMode(
            QtWidgets.QGraphicsView.BoundingRectViewportUpdate)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        self.setInteractive(True)

        self.scale(2.0, 2.0)
        self.setMinimumSize(400, 400)
        self.setDragMode(self.ScrollHandDrag)
        self._panning = False

        self.setAcceptDrops(True)
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self.gridRes = 5  # pts
        self.nodeQueue = GPINodeQueue()
        self.extWidgets = dict()

        # timed painter update
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.viewAndSceneForcedUpdate)
        # self._timer.start(1000) # 10msec update

        # TODO: this probably should go to the MainCanvas
        self._library = Library(self)
        #self._library.scanGPIModulesIn_SysPath(recursion_depth=2)
        #self._library.generateLibMenus()

        self._event_pos = QtCore.QPoint(0, 0)

        self._network = Network(self)

        self._pause_quiet = False

        self.initStateMachine()

    def rescanLibrary(self):
        self._library.scanForNewNodes()

    def getLibrary(self):
        return self._library

    def getEventPos(self):
        return self._event_pos

    def getEventPos_randomDev(self, rad=None):
        if rad:
            radius = rad
        else:
            radius = 10.0  # pts
        x = self._event_pos.x() + random.random() * radius
        y = self._event_pos.y() + random.random() * radius
        pos = QtCore.QPoint(x, y)
        pos = self.mapToScene(pos)
        return pos

    def title(self):
        return self._title

    def initStateMachine(self):  # GRAPH
        # Set up intial state graph.
        self._machine = GPI_FSM('GRAPH')
        self._switchSig.connect(self._machine.next)
        self._switchSig_info.connect(self._machine.next)

        # node states
        self._undefinedStateSig = {'title':self.title(), 'msg':'Undefined State (how did you get here?)'}
        self._initState = GPIState('init', self.initRun, self._machine, efunc=self.initWalltime)
        self._idleState = GPIState('idle', self.idleRun, self._machine, efunc=self.initWalltime)
        self._idleStateSig = {'title':self.title(), 'msg':'Idle'}
        self._checkEventsState = GPIState('checkEvents', self.checkEventsRun, self._machine)
        self._checkEventsStateSig = {'title':self.title(), 'msg':'Checking Events'}
        #self._deleteNodeState = GPIState('deleteNode', self.deleteNodeRun,
        #        self._machine)
        #self._addNodeState = GPIState('addNode', self.addNodeRun,
        #        self._machine)
        self._processingState = GPIState('processing', self.processingRun,
                self._machine)
        self._processingStateSig = {'title':self.title(), 'msg':'Processing'}
        self._pausedState = GPIState('paused', self.pausedRun, self._machine, efunc=self.pausedLeave)
        self._pausedStateSig = {'title':self.title(), 'msg':'Paused'}

        # make state graph
        # init
        self._initState.addTransition('init_check', self._checkEventsState)
        self._initState.addTransition('init_finished', self._idleState)
        self._initState.addTransition('pause', self._pausedState)
        #self._initState.exited.connect(self.initWalltime)

        # idle
        self._idleState.addTransition('check', self._checkEventsState)
        #self._idleState.addTransition('delete', self._deleteNodeState)
        #self._idleState.addTransition('deleteAll', self._deleteNodeState)
        #self._idleState.addTransition('load', self._addNodeState)
        self._idleState.addTransition('pause', self._pausedState)
        #self._idleState.exited.connect(self.initWalltime)

        # checkEvents
        self._checkEventsState.addTransition('process', self._processingState)
        self._checkEventsState.addTransition('requeue', self._checkEventsState)
        #self._checkEventsState.addTransition('delete', self._deleteNodeState)
        #self._checkEventsState.addTransition('deleteAll',
        #                                     self._deleteNodeState)
        self._checkEventsState.addTransition('ignore', self._idleState)
        #self._checkEventsState.addTransition('load', self._addNodeState)
        self._checkEventsState.addTransition('pause', self._pausedState)

        # deleteNode
        #self._deleteNodeState.addTransition('check', self._checkEventsState)
        #self._deleteNodeState.addTransition('process', self._processingState)

        # addNode
        #self._addNodeState.addTransition('check', self._checkEventsState)
        #self._addNodeState.addTransition('afterload', self._processingState)

        # processing
        #self._processingState.addTransition('delete', self._deleteNodeState)
        #self._processingState.addTransition('deleteAll', self._deleteNodeState)
        self._processingState.addTransition('pause', self._pausedState)
        self._processingState.addTransition('check', self._checkEventsState)
        self._processingState.addTransition('next', self._processingState)
        #self._processingState.addTransition('load', self._addNodeState)

        # pause
        self._pausedState.addTransition('unpause', self._checkEventsState)

        #self._machine.start(self._idleState)
        self._machine.start(self._initState)

    def walltime(self):
        return self._walltime

    def clearWalltime(self):
        if 'walltime' in self._idleStateSig:
            self._idleStateSig.pop('walltime')

    def initWalltime(self, sig):
        # sig is a dummy so that it can be an onExit state transition
        self._starttime = time.time()

    def calcWalltime(self):
        self._walltime = time.time() - self._starttime

    def walltime_disp(self):
        return GetHumanReadable_time(self.walltime(), precision=1)

    def initRun(self, sig):
        # run any initialization stuff here
        # since the 'check state' can't run yet, the canvas is virtually paused.

        if Commands.pendingCount():

            # load networks
            if Commands.netCount():
                for path in Commands.nets():

                    pos = self.getEventPos_randomDev(rad=50)
                    pos = QtCore.QPoint(pos.x(), pos.y())

                    s = {'sig': 'load', 'subsig': 'net', 'path':
                            path, 'pos': pos}
                    self.addNodeRun(s)

            # load nodes
            if Commands.modCount():
                for path in Commands.mods():

                    pos = self.getEventPos_randomDev(rad=50)
                    pos = QtCore.QPoint(pos.x(), pos.y())

                    s = {'sig': 'load', 'subsig': 'mod',
                            'path': path, 'pos': pos, 'from': 'cmd.Commands'}
                    self.addNodeRun(s)

            # load associated files
            if Commands.fileCount():
                for path in Commands.files():

                    pos = self.getEventPos_randomDev(rad=50)
                    pos = QtCore.QPoint(pos.x(), pos.y())

                    bpath, file_ext = os.path.splitext(path)
                    s = {'sig': 'load', 'subsig': file_ext, 'path': path, 'pos': pos}
                    self.addNodeRun(s)

            # NOTE: macro-nodes that need to close, re-select themselves
            #   -so this call doesn't work on them
            self.scene().unselectAllItems()

            # once all networks are loaded, process node arguments

            # String-Node Args
            if Commands.stringNodeArgCount():
                for lab in Commands.stringNodeLabels():
                    node = self.findNodeByNameAndLabel('String', lab)
                    if node:
                        # get the string arg
                        arg = Commands.stringNodeArg(lab)

                        # set 'string' widget value
                        node._nodeIF.modifyWidget_direct('string', val=arg)
                        node.setEventStatus({GPI_WIDGET_EVENT: 'string'})
                    else:
                        log.warn('String node label: \''+str(lab)+'\' not found, skipping.')

            self._switchSig.emit('init_check')

        else:
            self._switchSig.emit('init_finished')

    def totalPortMem(self):
        bytes_held = 0
        for node in self.getAllNodes():
            bytes_held += node.portMem()
        return bytes_held

    def totalPortMem_disp(self, bytes_held):
        return 'Total Port MEM: '+GetHumanReadable_bytes(bytes_held)

    # Function executed upon state change:
    def idleRun(self, sig):

        # get walltime and put it here
        self.calcWalltime()
        if self.walltime() > 0:
            self._idleStateSig['walltime'] = self.walltime_disp()
        else:
            self.clearWalltime()

        self._curState.emit(self._idleStateSig)
        self.printCurState()
        self.viewAndSceneForcedUpdate()

        # idle is a good time to force collection
        log.debug('pausedRun(): garbage collect')
        gc.collect()

        # if GPI was started without GUI, then assume the network has finished and exit
        if Commands.noGUI() or Commands.scriptMode():
            self.deleteAllNodeMMAPs()
            log.dialog('Canvas Wall Time: '+str(self.walltime_disp()) + ', exiting.')
            sys.exit(0)

    def pausedRun(self, sig):
        self._curState.emit(self._pausedStateSig)  # update statusbar
        self.printCurState()

        # don't draw yellow bkgnd
        if 'subsig' in sig:
            self._pause_quiet = True

        self.viewAndSceneForcedUpdate()

        # pause is a good time to force collection
        log.debug('pausedRun(): garbage collect')
        gc.collect()

        # if GPI was started without GUI, then assume the network has finished and exit
        if Commands.noGUI() or Commands.scriptMode():
            self.deleteAllNodeMMAPs()
            log.dialog('The canvas fell into a paused state, exiting.')
            sys.exit(1)

    def pausedLeave(self, sig):
        # always reset quiet flag
        self._pause_quiet = False

    def checkEventsRun(self, sig):
        self._curState.emit(self._checkEventsStateSig)
        self.printCurState()

        # Currently Running nodes
        if self.aNodeIsProcessing():
            self._switchSig.emit('process')
            return

        # EVENTS
        # check for event status BEFORE triggering highest compute
        for node in self.getAllNodes():
            if node.isReady():
                # Re/-initialize queue and start processing.
                # This was called because 'a' node has an event status.
                self.nodeQueue.setQueue(self.getLinearNodeHierarchy())
                self._switchSig.emit('process')
                return

        # REQUEUE EVENTS
        # if queue is done then check for re-queue nodes
        if self.nodeQueue.isEmpty():
            log.debug("checkEventsRun(): check for requeue nodes.")
            nodes = self.getAllNodes()
            cnt = 0
            for node in nodes:
                if node._nodeIF:  # protect against deleted object
                    if node._nodeIF.reQueueIsSet() and \
                            not node.inDisabledState():
                        node.setEventStatus({GPI_REQUEUE_EVENT: None})
                        cnt += 1
            if cnt:  # if any nodes got reset then start loop
                self._switchSig.emit('requeue')
                return

        # NO EVENTS
        # else: no events or requeue events were found
        self._switchSig.emit('ignore')

    def newNode_byClosestMatch(self, name, wdg_port_names, pos, mapit=False):
        # Search the library for all nodes with the same name, then do a
        # sub-search based on a list of wdg names.
        item = self._library.findNode_byClosestMatch(name, wdg_port_names)
        if item:
            item.reload()
            log.debug('\tfound')
            return self.newNode_byNodeCatalogItem(item, pos, mapit)
        else:
            log.debug('\tfailed to find node')

    def newNode_byKey(self, key, pos, mapit=False):
        # search the library for a node with given name
        item = self._library.findNode_byKey(key)
        if item:
            item.reload()
            log.debug('\tfound')
            return self.newNode_byNodeCatalogItem(item, pos, mapit)
        else:
            log.debug('\tfailed to find node')

    def newNode_byName(self, name, pos, mapit=False):
        # search the library for a node with given name
        item = self._library.findNode_byName(name)
        if item:
            item.reload()
            log.debug('\tfound')
            return self.newNode_byNodeCatalogItem(item, pos, mapit)
        else:
            log.debug('\tfailed to find node')

    def newNode_byPath(self, path, pos, mapit=False):
        # just try to make a node item, if it loaded then its valid.
        item = NodeCatalogItem(path)
        item.load()
        if item.valid():
            log.debug('\tsuccess')
            return self.newNode_byNodeCatalogItem(item, pos, mapit)
        else:
            log.debug('\titem cannot be loaded')

    def newNode_byNodeCatalogItem(self, item, pos, mapit=False):
        '''Add a new node to the canvas from a NodeCatalogItem description.
        Return a handle to the new canvas item.
            pos: QtCore.QPoint()
        '''
        if item is None:
            return None

        # Update user modifications (if any).
        item.reload()

        # If the user has made changes that cause the node to be non-loadable
        # then return None
        if not item.valid():
            return None

        newnode = Node(self, nodeCatItem=item)

        # force all execType(s) to be GPI_APPLOOP
        if False:  # letting them all be processes seems to be the safest for now
        #if Commands.noGUI():
            # Thread seems safer, APPLOOP was causing recursion errors.
            # Probably due to signals piling up.

            # GPI_APPLOOP & iter_test.net causes: recursion error
            et = lambda :GPI_APPLOOP

            # GPI_THREAD & beta_spiral.net causes: 64119 Bus error: 10
            #et = lambda :GPI_THREAD

            newnode.execType = et
            newnode._nodeIF.execType = et

        newnode.refreshName()
        self.scene().addItem(newnode)
        if mapit:
            mpos = self.mapToScene(pos)
        else:
            mpos = pos
        newnode.setPos(mpos.x(), mpos.y())
        return newnode

    # TODO: since addNodeRun was removed from the state-machine it now needs
    # a real function interface instead of passing a dict to parameterize
    def addNodeRun(self, sig):  # state: 'addNode', 'Run' method
        self.printCurState()

        node = None

        if type(sig['subsig']) == NodeCatalogItem:
            log.debug('addNode by item')
            item = sig['subsig']

            # get the position of menu invocation
            radius = 10.0  # pts
            if "pos" not in sig.keys():
                x = self._event_pos.x() + random.random() * radius
                y = self._event_pos.y() + random.random() * radius
                pos = QtCore.QPoint(x, y)
            else:
                pos = sig['pos']

            # instantiate node on canvas
            if "mapit" not in sig.keys():
                mapit = True
            else:
                mapit = sig['mapit']
            node = self.newNode_byNodeCatalogItem(item, pos, mapit)
            if node:
                self.scene().makeOnlyTheseNodesSelected([node])
                node.setEventStatus({GPI_INIT_EVENT: None})
                self.ensureVisible(node)

        elif sig['subsig'] == 'mod':
            log.debug('addNode by path')
            path = sig['path']
            pos = sig['pos']

            # instantiate node on canvas
            node = self.newNode_byPath(path, pos, mapit=True)
            if node:
                self.scene().makeOnlyTheseNodesSelected([node])
                node.setEventStatus({GPI_INIT_EVENT: None})
                self.ensureVisible(node)

        # 3-4 pieces of info for file associations
        #   node-name (and possibly key), file ext, string widget to push to
        elif isGPIAssociatedExt(sig['subsig']):

            # get binding for this file extension
            # all extensions should be case-insensitive
            item = Bindings.get(sig['subsig'].lower())

            # assume the item is holding a full key
            node = self.newNode_byKey(item.node, sig['pos'], mapit=True)
            if node is None:
                node = self.newNode_byName(item.node, sig['pos'], mapit=True)
            if node is None:
                log.error('\''+str(item.node)+'\' could not be located for \''+str(item.ext)+'\'')
            else:
                node._nodeIF.modifyWidget_direct(item.wdg, val=sig['path'])
                self.scene().unselectAllItems()
                node.setSelected(True)
                node.setEventStatus({GPI_WIDGET_EVENT: item.wdg})
                self.ensureVisible(node)

        elif sig['subsig'] == 'net':

            if 'pos' in sig:
                net = self._network.loadNetworkFromFile(sig['path'])
                if net:
                    self.deserializeCanvas(net, sig['pos'])
            else:
                net = self._network.loadNetworkFromFile(sig['path'])
                if net:
                    self.deserializeCanvas(net, self.getEventPos_randomDev())

        elif sig['subsig'] == 'dialog':
            if 'pos' in sig:
                net = self._network.loadNetworkFromFileDialog()
                if net:
                    self.deserializeCanvas(net, sig['pos'])
            else:
                net = self._network.loadNetworkFromFileDialog()
                if net:
                    self.deserializeCanvas(net, self.getEventPos_randomDev())

        elif sig['subsig'] == 'paste':
            if self.parent._copybuffer:
                self.deserializeGraphData(self.parent._copybuffer, pos=sig['pos'])

        elif sig['subsig'] == 'keypaste':
            if self.parent._copybuffer and 'copy_connections' in sig.keys():
                self.deserializeGraphData(self.parent._copybuffer, offset=True, randoffset=True, copy_connections=sig['copy_connections'])
            else:
                self.deserializeGraphData(self.parent._copybuffer, offset=True, randoffset=True)

        elif sig['subsig'] == 'reload':
            if self.parent._copybuffer:
                self.deserializeGraphData(self.parent._copybuffer, reloadnode=True)

        if self.inIdleState():# or self.inCheckEventsState():
            self._switchSig.emit('check')

        return node

    def deleteNodeRun(self, sig):
        self.printCurState()
        if sig == 'delete':  # delete selected
            self.deleteSelectedNodes()
        elif sig == 'deleteAll':  # clear all
            self.deleteAllNodes()

        # back to processing or check for new events
        #if self.nodeQueue.isEmpty():
        #    self._switchSig.emit('check')
        #else:
        #    self._switchSig.emit('process')

        if self.inIdleState():
            self._switchSig.emit('check')

    def aNodeIsProcessing(self):
        for node in self.getAllNodes():
            if node.isProcessingEvent():
                return True
        return False

    def processingRun(self, sig):
        self._curState.emit(self._processingStateSig)
        self.printCurState()

        if not self.aNodeIsProcessing():
            queueState = self.nodeQueue.startNextNode()
            if queueState == 'paused':
                self._switchSig.emit('paused')
            elif queueState == 'finished':
                self._switchSig.emit('check')

        self.viewAndSceneForcedUpdate()

    # State Checking:
    def getCurState(self):
        return self._machine.curState

    def getCurStateName(self):
        '''return state names in a list of strings'''
        return self._machine.curStateName

    def getCurStateSig(self):
        if self.inIdleState():
            return self._idleStateSig
        elif self.inPausedState():
            return self._pausedStateSig
        elif self.inCheckEventsState():
            return self._checkEventsStateSig
        elif self.inProcessingState():
            return self._processingStateSig
        else:
            return self._undefinedStateSig

    def printCurState(self):
        log.debug("GRAPH State(s): "+self.getCurStateName())

    def inIdleState(self):  # GRAPH
        return self._idleState is self.getCurState()

    def inPausedState(self):  # GRAPH
        return self._pausedState is self.getCurState()

    def inCheckEventsState(self):
        return self._checkEventsState is self.getCurState()

    def inProcessingState(self):
        return self._processingState is self.getCurState()

    def printNodeState(self):
        allItems = self.getAllNodes()
        for node in allItems:
            print("________________________")
            node.printCurState()
            print(("node: " + str(node.name)))
            print(("inDisabledState: " + str(node.inDisabledState())))
            print(("hasEventPending: " + str(node.hasEventPending())))
            print(("_nodeIF.reQueueIsSet: " + str(node._nodeIF.reQueueIsSet())))
            print("________________________")

    def setPauseState(self, val):
        old_val = self.nodeQueue.isPaused()
        self.nodeQueue.setPause(val)
        if val != old_val:  # state changed
            if not val:  # unpaused
                # after pause drop old event queue
                self.nodeQueue.resetQueue()
                self._switchSig.emit('check')

    def isPaused(self):
        return self.nodeQueue.isPaused()

    def scrollContentsBy(self, x, y):
        super(GraphWidget, self).scrollContentsBy(x, y)
        y = self.geometry().height() / 2
        x = self.geometry().width() / 2
        self._event_pos = QtCore.QPoint(x, y)

    def newLayoutWindowFromSettings(self, s, nodeList):

        # config has to be set at construction b/c layouts cannot yet be
        # deleted.
        layoutwindow = LayoutMaster(self, config=s['config'])
        layoutwindow.loadSettings(s, nodeList)
        layoutwindow.setWindowTitle(self._title+".Layout Window "+str(len(self._layoutwindowList)+1))

        #scrollArea = QtWidgets.QScrollArea()
        #scrollArea.setWidget(layoutwindow)
        #scrollArea.setWidgetResizable(True)
        #scrollArea.setGeometry(50, 50, 300, 1000)
        #self._layoutwindowList.append(scrollArea)

        self._layoutwindowList.append(layoutwindow)
        layoutwindow.setGeometry(50, 50, 400, 300)

        #scrollArea.show()
        #scrollArea.raise_()

        layoutwindow.show()
        layoutwindow.raise_()

    def newLayoutWindow(self, config):

        layoutwindow = LayoutMaster(self, config=config)
        layoutwindow.setWindowTitle(self._title+".Layout Window "+str(len(self._layoutwindowList)+1))

        #scrollArea = QtWidgets.QScrollArea()
        #scrollArea.setWidget(layoutwindow)
        #scrollArea.setWidgetResizable(True)
        #scrollArea.setGeometry(50, 50, 300, 1000)
        #self._layoutwindowList.append(scrollArea)

        self._layoutwindowList.append(layoutwindow)
        layoutwindow.setGeometry(50, 50, 400, 300)

        #scrollArea.show()
        #scrollArea.raise_()

        layoutwindow.show()
        layoutwindow.raise_()

    def serializeLayoutWindows(self):
        '''Save each layout dict.
        '''
        s = []
        for layout in self._layoutwindowList:
            # layout is None for past closed windows.
            # this keeps numbering correct
            if layout is not None:
                s.append(layout.getSettings())
        return s


    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('text/uri-list'):
            event.acceptProposedAction()
        self.changed.emit(event.mimeData())

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('text/uri-list'):
            event.acceptProposedAction()

    def dropEvent(self, event):

        if event.mimeData().hasFormat('application/gpi-widget'):
            mime = event.mimeData()
            itemData = mime.data('application/gpi-widget')
            dataStream = QtCore.QDataStream(
                itemData, QtCore.QIODevice.ReadOnly)

            text = QtCore.QByteArray()
            offset = QtCore.QPoint()
            dataStream >> text >> offset

            log.debug("canvasGraph(): Mime data:")
            log.debug(str(text))
            log.debug(str(offset))
            return

        elif event.mimeData().hasFormat('text/uri-list'):
            mimeData = event.mimeData()

            log.debug(str(mimeData))
            paths = [str(x.path()) for x in mimeData.urls()]
            log.debug(paths)

            # if multiple drops, then add random offsets to pos
            if len(paths) == 1:
                poses = [event.pos()]
            else:
                poses = []
                for path in paths:
                    m = 50
                    rand = QtCore.QPoint(random.random()*m, random.random()*m)
                    poses.append(event.pos() + rand)

            # process each dropped path
            for path, pos in zip(paths, poses):

                log.debug('Dropped uri: '+str(path))

                # node definitions
                if isGPIModFile(path):

                    # add the node to the library (and menu) if possible
                    item = NodeCatalogItem(path)
                    ret = self._library.addNode(item)
                    if ret > 0:
                        log.dialog('Added dropped node to the library.')
                        self._library.regenerateLibMenus()
                    elif ret == 0:
                        log.dialog('Dropped Node is already in the library.')
                    else:
                        log.error('Dropped Node is Invalid.')
                        return

                    # add the node to the canvas
                    s = {'sig': 'load', 'subsig': 'mod',
                            'path': path, 'pos': pos, 'from': 'Dropped uri'}
                    self.addNodeRun(s)

                # file associations
                elif isGPIAssociatedFile(path):
                    bpath, file_ext = os.path.splitext(path)
                    s = {'sig': 'load', 'subsig': file_ext, 'path': path, 'pos': pos}
                    self.addNodeRun(s)

                # network files
                elif isGPINetworkFile(path):
                    s = {'sig': 'load', 'subsig': 'net', 'path':
                            path, 'pos': self.mapToScene(pos)}
                    self.addNodeRun(s)

                # not a recognized file
                else:
                    log.warn("dropEvent(): Filetype not recognized by GPI.")
                    return

            # shows rejected animation if not called
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        event.accept()

    def itemMoved(self):

        # only start this timer if the menu option for CR is set
        if self.chargeRepON:
            if not self.timerId:
                self.timerId = self.startTimer(30)  # update time (msec)

                # add timeout
                # give object a few seconds to unwrap
                # self.stimer = QtCore.QTimer()
                # self.stimer.singleShot(10000, self.send_killTimer)

    def deleteNode(self, node):

        if isinstance(node, Node):
            #if (node.execType() is GPI_THREAD) and node.isProcessingEvent():
            #    print "Thread is in progress, cancel delete ("+node.name+")"
            #    return
            if isMacroChildNode(node):
                node.macroParent().readyForDeletion()
                for n in node.getSiblingNodes():
                    self.nodeQueue.removeNode(n)
                    n.readyForDeletion()
                    if n.scene():
                        self.scene().removeItem(n)
            elif node:
                node.readyForDeletion()
                if node.scene():
                    self.scene().removeItem(node)

        # keep random objects from being copied to other processes
        log.debug('deleteNode(): garbage collect')
        gc.collect()

        # try to check check for changes after a deletion
        if self.inProcessingState():
            self._switchSig.emit('check')

    def deleteSelectedNodes(self):
        '''For a list of nodes, its safer to disable all of them and remove
        them from the queue directly
        '''
        selnodes = self.getSelectedNodes()
        for node in selnodes:
            node.setDeleteFlag(True)
            node.setDisabledState(True)
            self.nodeQueue.removeNode(node)
        for node in selnodes:
            self.deleteNode(node)

    def deleteAllNodes(self):
        '''For a list of nodes, its safer to disable all of them and remove
        them from the queue directly
        '''
        selnodes = self.getAllNodes()
        for node in selnodes:
            node.setDeleteFlag(True)
            node.setDisabledState(True)
            self.nodeQueue.removeNode(node)
        for node in selnodes:
            self.deleteNode(node)

    def deleteAllNodeMMAPs(self):
        '''For a list of nodes, its safer to disable all of them and remove
        them from the queue directly
        '''
        selnodes = self.getAllNodes()
        for node in selnodes:
            node.removeMMAPs()

    def getAllMacroNodes(self):
        '''Find all nodes that belong to macro-framework, then store them in a
        dictionary based on macro-object-id.
        '''
        macros = {}
        mnodes = []
        for node in self.getAllNodes():
            if isMacroChildNode(node):
                macros[str(node.macroParent().getID())] = node.getSiblingNodes()
                mnodes.append(node.macroParent())

        # take encapsulated nodes if the macro is collapsed
        enodes = []
        for node in mnodes:
            if node.isCollapsed():
                enodes += node.getEncapsulatedNodes()
        enodes = list(set(enodes))

        return macros, enodes

    def getSelectedMacroNodes(self):
        '''Find all nodes that belong to macro-framework, if ANY of the child
        nodes are selected then the node is selected:
            -if its expanded, then only IT is selected (and any other selected
            nodes)
            -if its collapsed, then it AND all encapsulated nodes are selected.
        '''
        macros = {}
        mnodes = []
        for node in self.getSelectedNodes():
            if isMacroChildNode(node):
                macros[str(node.macroParent().getID())] = node.getSiblingNodes()
                mnodes.append(node.macroParent())

        # take encapsulated nodes if the macro is collapsed
        enodes = []
        for node in mnodes:
            if node.isCollapsed():
                enodes += node.getEncapsulatedNodes()
        enodes = list(set(enodes))

        return macros, enodes

    def getAllNodes(self):
        allitems = list(self.scene().items())[:]  # copy in case of user interrupt
        nodes = [item for item in allitems if isinstance(item, Node)]
        return(nodes)

    def getAllMacros(self):
        '''Get the MacroNode object class handle.
        '''
        allitems = list(self.scene().items())[:]  # copy in case of user interrupt
        nodes = [item for item in allitems if isinstance(item, MacroNode)]
        return(nodes)

    def findNodeByNameAndLabel(self, name, lab):
        # return the first occurrence of a Node with the given name and label
        for node in self.getAllNodes():
            if node.getNodeLabel() == lab:  # most exclusive
                if node.getNameFromItem() == name:
                    return node

    def getAllPorts(self):
        allitems = list(self.scene().items())[:]  # copy in case of user interrupt
        ports = [item for item in allitems if isinstance(item, Port)]
        return(ports)

    def getSelectedNodes(self):
        sceneItems = list(self.scene().items())[:]  # copy in case of user interrupt
        sceneItems = [
            i for i in sceneItems if i.isSelected() and isinstance(i, Node)]
        return sceneItems

    def getEmptyConnectionNodes(self, nodes):
        empty = []
        for node in nodes:
            connections = node.getOutputConnections()
            if (not any(connections)): empty.append(node)
        return empty

    def findWidgetByID(self, nodeList, wdgid):
        '''traverses all node's parmLists for the given id.
        '''
        wdgid = int(wdgid)
        for node in nodeList:
            for parm in node._nodeIF.parmList:
                if parm.get_id() == wdgid:
                    return parm

    # kill timer for items moving under charge repulsion
    def send_killTimer(self):
        self.killTimer(self.timerId)
        self.timerId = 0
        self.chargeRepON = False

    def getLinearNodeHierarchy(self):
        return self.getLinearNodeHierarchy_fromList(self.getAllNodes())

    def getLinearNodeHierarchy_fromList(self, nodeList):
        return sorted(nodeList, key=lambda y: y.getHierarchalLevel())

    def viewAndSceneForcedUpdate(self):
        '''All calls to this updater are to patch over a bug that
        presents when a network has iterated too many times.
        -The root problem needs to be found (perhaps pyqt vs. qt ownership).

        -This is also required to immediately render the pause event.
        '''
        log.debug("viewAndSceneForcedUpdate called")
        ##self.updateMicroFocus()
        ##self.updateGeometry()
        ##self.repaint()

        # don't bother updating if there is no gui
        if Commands.noGUI():
            return

        self.update()
        self.scene().update()

        ##QtWidgets.QApplication.processEvents() # allow gui to update

    def calcNodeHierarchy(self):
        # tells each node which level it is
        # and returns a list based on that level

        nodeList = self.getAllNodes()

        # concatenate all connections (even if list is redundant)
        c = []
        for node in nodeList:
            if len(node.getNonCyclicConnectionTuples()):
                c += node.getNonCyclicConnectionTuples()
            #if len(node.getConnectionTuples()):
            #    c += node.getConnectionTuples()
            else:
                # island nodes have top priority
                node.resetHierarchalLevel()
                node.refreshName()

        sortedNodes = topsort.topsort(c)

        # signal that the connection is cyclic
        if sortedNodes is None:
            return None

        # set node hierarchy
        # -each node knows its current level
        cnt = 0
        for node in sortedNodes:
            node.setHierarchalLevel(cnt)
            cnt += 1

        return sortedNodes

    def roundPosToGrid(self, pos):
        x = int(pos[0] / self.gridRes) * self.gridRes
        y = int(pos[1] / self.gridRes) * self.gridRes
        return(x, y)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = getKeyboardModifiers()

        # copy/paste/delete
        if key == QtCore.Qt.Key_C and modifiers == QtCore.Qt.ControlModifier:
            self.copyNodesToBuffer()
        elif key == QtCore.Qt.Key_V and modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            # try to paste fairly close to where the nodes were copied
            if self.parent._copybuffer:
                s = {'sig': 'load', 'subsig': 'keypaste', 'copy_connections':True}
                self.addNodeRun(s)
            else:
                log.warn("Nothing in buffer to paste.")
        elif key == QtCore.Qt.Key_V and modifiers == QtCore.Qt.ControlModifier:
            # try to paste fairly close to where the nodes were copied
            if self.parent._copybuffer:
                s = {'sig': 'load', 'subsig': 'keypaste'}
                self.addNodeRun(s)
            else:
                log.warn("Nothing in buffer to paste.")
        elif key == QtCore.Qt.Key_Delete or key == QtCore.Qt.Key_Backspace:
            #self._switchSig.emit('delete')  # change state
            self.deleteNodeRun('delete')

        # load/save network
        elif key == QtCore.Qt.Key_L and modifiers == QtCore.Qt.ControlModifier:
            s = {'sig': 'load', 'subsig': 'dialog'}
            self.addNodeRun(s)
            #self._switchSig_info.emit(s)

        elif key == QtCore.Qt.Key_S and modifiers == QtCore.Qt.ControlModifier:
            self._network.saveNetworkFromFileDialog(self.serializeCanvas())

        # move nodes across canvas
        elif key == QtCore.Qt.Key_Up:
            for node in self.getSelectedNodes():
                pos = node.getPos()
                x, y = self.roundPosToGrid(pos)
                node.moveBy(0, y - pos[1] - 5)
        elif key == QtCore.Qt.Key_Down:
            for node in self.getSelectedNodes():
                pos = node.getPos()
                x, y = self.roundPosToGrid(pos)
                node.moveBy(0, y - pos[1] + 5)
        elif key == QtCore.Qt.Key_Left:
            for node in self.getSelectedNodes():
                pos = node.getPos()
                x, y = self.roundPosToGrid(pos)
                node.moveBy(x - pos[0] - 5, 0)
        elif key == QtCore.Qt.Key_Right:
            for node in self.getSelectedNodes():
                pos = node.getPos()
                x, y = self.roundPosToGrid(pos)
                node.moveBy(x - pos[0] + 5, 0)

        # tab nodes (in execution order)
        elif key == QtCore.Qt.Key_Tab:
            snodes = self.getSelectedNodes()
            if len(snodes):  # just skip if no nodes are selected
                snode = snodes[0]
                nodes = self.getLinearNodeHierarchy()
                for i in range(len(nodes)):
                    if nodes[i] == snode:
                        if i < len(nodes) - 1:
                            self.scene().makeOnlyTheseNodesSelected(
                                [nodes[i + 1]])
                        else:
                            self.scene().makeOnlyTheseNodesSelected([nodes[0]])
                        self.scene().update()
                        return
            else:  # no nodes selected so pick one
                nodes = self.getLinearNodeHierarchy()
                self.scene().makeOnlyTheseNodesSelected([nodes[0]])
                self.scene().update()

        # raise node menu(s)
        #elif key == QtCore.Qt.Key_Space:
        #    nodes = self.getSelectedNodes()
        #    if len(nodes):
        #        for node in nodes:
        #            node.menu()

        elif key == QtCore.Qt.Key_Plus:
            self.scaleView(1.2)
        elif key == QtCore.Qt.Key_Minus:
            self.scaleView(1 / 1.2)
        elif key == QtCore.Qt.Key_Enter:
            pass
       
        # mix up nodes
        elif key == QtCore.Qt.Key_M and modifiers == QtCore.Qt.ControlModifier:
            for item in list(self.scene().items()):
                if isinstance(item, Node):
                    item.setPos(-150 + QtCore.qrand() %
                                300, -150 + QtCore.qrand() % 300)

        # organize nodes
        elif key == QtCore.Qt.Key_O and modifiers == QtCore.Qt.ControlModifier:
            self.organizeSelectedNodes()

        # pause
        elif key == QtCore.Qt.Key_P and modifiers == QtCore.Qt.ControlModifier:
            self.pauseToggle()

        # select all nodes
        elif key == QtCore.Qt.Key_A and modifiers == QtCore.Qt.ControlModifier:
            self.scene().makeOnlyTheseNodesSelected(self.getAllNodes())

        # pause -for stationary leftys
        elif key == QtCore.Qt.Key_Space:
            self.pauseToggle()

        # charge repulsion toggle
        elif key == QtCore.Qt.Key_R and int(event.modifiers()) == (QtCore.Qt.ControlModifier + QtCore.Qt.ShiftModifier):
            if self.chargeRepON is True:
                self.chargeRepON = False
            else:
                self.chargeRepON = True
                self.itemMoved()
            log.dialog("toggle chargeRepON:" + str(self.chargeRepON))

        # reload node
        elif key == QtCore.Qt.Key_R and modifiers == QtCore.Qt.ControlModifier:
            self.reload_node()

        # resize canvas window for podcast
        elif key == QtCore.Qt.Key_W and modifiers == QtCore.Qt.ControlModifier:
            log.dialog("resize window")
            self.parent.resize(1024, 768)

        # Test Key
        elif key == QtCore.Qt.Key_T:
            pass
            # log.dialog("Test Key Pressed")
            #print self.getAllPorts()
            #print self.getAllMacroNodes()
            #print self.serializeGraphData()
            # print((self.getAllNodes()))
            # print((self.getAllMacroNodes()))

        # close all node windows
        elif key == QtCore.Qt.Key_X and modifiers == QtCore.Qt.ControlModifier:
            self.closeAllNodeMenus()

        else:
            super(GraphWidget, self).keyPressEvent(event)

    def addNodeByName(self, name, pos=QtCore.QPoint(50, 35)):
        item = self._library.findNode_byName(name)
        s = {'subsig': item, 'pos': pos, 'mapit': False}
        node = self.addNodeRun(s)
        return node

    def addHotkey(self, key, node):
        hotkey = QtWidgets.QShortcut(QtGui.QKeySequence(key), self)
        hotkey.activated.connect(lambda: self.shortcut(node))
        self.hotkeys[key] = hotkey
        return hotkey


    def addShortcuts(self, shortcuts):
        for shortcut in shortcuts:
            shortcut = shortcut.split(":")
            if len(shortcut) == 2:
                self.addHotkey(shortcut[0], shortcut[1])


    def updateShortcuts(self, shortcuts):
        for key in self.hotkeys.keys():
            hotkey = self.hotkeys[key]
            hotkey.setParent(None)
        self.hotkeys = {}
        self.addShortcuts(shortcuts)
        
    def shortcut(self, name):
        # get selected nodes
        selected_nodes = self.getSelectedNodes()

        # add node and get its input ports
        node = self.addNodeByName(name, self.mousePos)
        inports = node.inportList

        # check for viable outports of the selected nodes
        viable_outports = [[] for _ in range(len(inports))]
        for s_node in selected_nodes:
            outports = s_node.outportList
            for i, inport in enumerate(inports):
                matching_ports = inport.findMatchingOutPorts(outports)
                viable_outports[i].append(matching_ports)
        
        # connect the viable outputs to the node inputs
        connected = []
        for i, ports in enumerate(viable_outports):
            inport = inports[i]

            # get ports in order, use a port from each node first
            max_l = [len(x) for x in ports]
            if len(max_l):
                max_length = max(max_l)
                temp = []
                for i in range(max_length):
                    for l in ports:
                        if i < len(l): temp.append(l[i])
                ports = [temp]

            # connect ports
            for outports in ports:
                outports = list(filter(lambda port: port not in connected, outports))
                if len(outports) and inport not in connected:
                    outport = outports[0]
                    if outport in connected: continue # skip if the outport is already connected
                    newEdge = Edge(outport, inport)
                    self.scene().addItem(newEdge)
                    connected.append(outport)
                
                    nodeHierarchy = inport.getNode().graph.calcNodeHierarchy()
                    if nodeHierarchy is None:
                        self.scene().removeItem(newEdge)
                        newEdge.detachSelf()
                        # del newEdge
                        log.warn("CanvasScene: cyclic, connection dropped")
                    else:
                        # CONNECTION ADDED
                        # Since node hierarchy is recalculated, also
                        # take the time to flag nodes for processing
                        # 1) check for matching spec type
                        if not (inport.checkUpstreamPortType()):
                            self.scene().removeItem(newEdge)
                            newEdge.detachSelf(update=False)
                            # del newEdge
                            log.warn("CanvasScene: data type mismatch, connection dropped")
                        else:
                            # 2) set the downstream node's pending_event
                            GPI_PORT_EVENT = '_PORT_EVENT_'
                            inport.getNode().setEventStatus({GPI_PORT_EVENT: inport.portTitle})

                            # trigger a force recalculation
                            inport.getNode().graph.itemMoved()

                            # trigger name update
                            inport.getNode().refreshName()
                            outport.getNode().refreshName()

                            # trigger event queue, if its idle
                            inport.getNode().graph._switchSig.emit('check')

                            if len(self.scene().portMatches):
                                for port in self.scene().portMatches:
                                    port.resetScale()
                                self.scene().portMatches = []

                            inport.edges()[0].adjust()
                            for edge in outport.edges():
                                edge.adjust()

                    connected.append(inport)

    def connectPorts(self, outport, inport):
        newEdge = Edge(outport, inport)
        self.scene().addItem(newEdge)
    
        nodeHierarchy = inport.getNode().graph.calcNodeHierarchy()
        if nodeHierarchy is None:
            self.scene().removeItem(newEdge)
            newEdge.detachSelf()
            # del newEdge
            log.warn("CanvasScene: cyclic, connection dropped")
        else:
            # CONNECTION ADDED
            # Since node hierarchy is recalculated, also
            # take the time to flag nodes for processing
            # 1) check for matching spec type
            if not (inport.checkUpstreamPortType()):
                self.scene().removeItem(newEdge)
                newEdge.detachSelf(update=False)
                # del newEdge
                log.warn("CanvasScene: data type mismatch, connection dropped")
            else:
                # 2) set the downstream node's pending_event
                GPI_PORT_EVENT = '_PORT_EVENT_'
                inport.getNode().setEventStatus({GPI_PORT_EVENT: inport.portTitle})

                # trigger a force recalculation
                inport.getNode().graph.itemMoved()

                # trigger name update
                inport.getNode().refreshName()
                outport.getNode().refreshName()

                # trigger event queue, if its idle
                inport.getNode().graph._switchSig.emit('check')

                if len(self.scene().portMatches):
                    for port in self.scene().portMatches:
                        port.resetScale()
                    self.scene().portMatches = []

                inport.edges()[0].adjust()
                for edge in outport.edges():
                    edge.adjust()
        return edge


    def reload_node(self):
        '''Reload, instantiate, and reconnect the selected node.
                -Only allow one node.
        '''
        nodes = self.getSelectedNodes()

        if len(nodes) == 0:
            return

        # pause the canvas during this process
        alreadyPaused = self.inPausedState()
        if not alreadyPaused:
            self.pauseToggle(quiet=True)

        # copy
        self.copyNodesToBuffer()

        # delete node
        for node in nodes:
            self.deleteNode(node)

        # paste
        if self.parent._copybuffer:
            s = {'sig': 'load', 'subsig': 'reload'}
            self.addNodeRun(s)

        # unpause if the user hadn't already done so.
        if not alreadyPaused:
            self.pauseToggle()


    def closeAllNodeMenus(self):
        for node in self.getAllNodes():
            node.closemenu()

    def organizeSelectedNodes(self):
        nodes = self.getSelectedNodes()
        if len(nodes):
            snodes = self.getLinearNodeHierarchy_fromList(nodes)
            topnode = snodes[0]
            x = topnode.scenePos().x()
            y = topnode.scenePos().y()

            self._node_anim_group = QtCore.QParallelAnimationGroup()
            for node in snodes:
                anim = QtCore.QPropertyAnimation(node, b"pos")
                anim.setDuration(100)
                anim.setStartValue(QtCore.QPointF(x, topnode.scenePos().y()))
                anim.setEndValue(QtCore.QPointF(x, y))
                self._node_anim_group.addAnimation(anim)
                y += node.getNodeHeight() + 15.0

            self._node_anim_group.start()

    def chargeRepTimer(self, event):
        if self.chargeRepON is False:
            return

        nodes = self.getAllNodes()

        # don't let a single unattached node be affected by force
        nodes = [item for item in nodes if len(item.edges()) > 0]

        for node in nodes:
            node.calculateForces()

        itemsMoved = False
        for node in nodes:
            if node.advance():
                itemsMoved = True

        if not itemsMoved:
            self.killTimer(self.timerId)
            self.timerId = 0

    def timerEvent(self, event):
        # if event.timerId() == self.nodeEvent_timerId:
        #    print "timer: global node timer"
        # always update charge rep events
        self.chargeRepTimer(event)

    def wheelEvent(self, event):
        try:
            # PyQt4
            self.scaleView(math.pow(2.0, event.delta() / 300.0))
        except AttributeError:
            # PyQt5
            angle = event.angleDelta().y() / 8
            self.scaleView(math.pow(2.0, angle / 80.0))

    def drawBackground(self, painter, rect):
        # Shadow.
        sceneRect = self.sceneRect()
        rightShadow = QtCore.QRectF(sceneRect.right(), sceneRect.top() + 5, 5,
                                    sceneRect.height())
        bottomShadow = QtCore.QRectF(sceneRect.left() + 5, sceneRect.bottom(),
                                     sceneRect.width(), 5)
        if rightShadow.intersects(rect) or rightShadow.contains(rect):
            painter.fillRect(rightShadow, QtCore.Qt.darkGray)
        if bottomShadow.intersects(rect) or bottomShadow.contains(rect):
            painter.fillRect(bottomShadow, QtCore.Qt.darkGray)

        # Fill.
        gradient = QtGui.QLinearGradient(sceneRect.topLeft(),
                                         sceneRect.bottomRight())

        if self.inPausedState() and not self._pause_quiet:
            gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.yellow).lighter(190))
            gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.yellow).lighter(170))
        else:
            #gradient.setColorAt(0, QtCore.Qt.white)
            #gradient.setColorAt(1, QtCore.Qt.lightGray)
            gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.gray).lighter(180))
            gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.gray).lighter(150))

        painter.fillRect(rect.intersected(sceneRect), QtGui.QBrush(gradient))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(sceneRect)

        # Text.
        textRect = QtCore.QRectF(sceneRect.left() + 4, sceneRect.top() + 4,
                                 sceneRect.width() - 4, sceneRect.height() - 4)
        message = "Network Canvas"

        font = painter.font()
        font.setBold(True)
        font.setPointSize(14)
        painter.setFont(font)
        painter.setPen(QtCore.Qt.lightGray)
        painter.drawText(textRect.translated(2, 2), message)
        painter.setPen(QtCore.Qt.black)
        painter.drawText(textRect, message)

        # Mark.
        ## centered
        #mark_font = QtGui.QFont(u"gill sans", 100)
        #fm = QtGui.QFontMetricsF(mark_font)
        #message = "PHILIPS"
        #bw = fm.width(message) * 1.12

        ## bw is the width at 100pt font
        #w = self.viewport().rect().width()
        #f = (100*w)/bw/2
        #mark_font = QtGui.QFont(u"gill sans", int(f))

        #mark_font = QtGui.QFont(u"gill sans", 50)
        #fm = QtGui.QFontMetricsF(mark_font)
        #bw = fm.width(message) * 1.12

        #bh = fm.height()
        # centered
        #textRect = QtCore.QRectF(self.mapToScene(self.viewport().rect().center()).x()-bw/2, self.mapToScene(self.viewport().rect().center()).y()-bh/2, bw, bh)
        #textRect = QtCore.QRectF(self.mapToScene(self.viewport().rect().bottomRight()).x()-bw-8, self.mapToScene(self.viewport().rect().bottomRight()).y()-bh-2, bw, bh)


        #mark_font.setBold(True)
        #mark_font.setPointSize(14)
        #painter.setFont(mark_font)
        #c = QtGui.QColor(QtCore.Qt.gray).lighter(130)
        #c.setAlphaF(0.5)
        #painter.setPen(c)
        #painter.drawText(textRect.translated(2, 2), message)
        #c = QtGui.QColor(QtCore.Qt.gray).lighter(150)
        #c.setAlphaF(0.5)
        #painter.setPen(c)
        #painter.setPen(QtCore.Qt.black)
        #painter.drawText(textRect, message)

    def scaleView(self, scaleFactor):
        try:
            # PyQt4
            factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(
                QtCore.QRectF(0, 0, 1, 1)).width()
        except AttributeError:
            # PyQt5 doesn't have a matrix() attribute
            factor = scaleFactor

        if factor < 0.07 or factor > 100:
            return

        self.scale(scaleFactor, scaleFactor)

    # def mouseDoubleClickEvent(self, event):
    #    event.accept()
    #    print "double-clicked canvas"

    def mousePressEvent(self, event):  # GRAPHICS VIEW
        printMouseEvent(self, event)
        modifiers = getKeyboardModifiers()

        self.viewAndSceneForcedUpdate()

        if self._panning:
            return

        QtWidgets.QGraphicsView.mousePressEvent(self, event)
        if event.isAccepted():
            return

        if event.button() == QtCore.Qt.MidButton:
            event.accept()
            self._panning = True
            # trick graphics view into thinking it has a left click for panning
            leftbutton_event = QtGui.QMouseEvent(
                event.type(), event.pos(), event.globalPos(),
                QtCore.Qt.LeftButton, event.buttons(), modifiers)
            leftbutton_event.accept()
            super(GraphWidget, self).mousePressEvent(leftbutton_event)
            return

        # propagate to other view items (nodes)
        if event.button() == QtCore.Qt.RightButton:
            event.accept()
            # if self.scene().itemAt(event.scenePos()):
            #    self.scene().unselectAllItems()
            #    self.scene().itemAt(event.scenePos()).setSelected(True)
            pointedItem = self.itemAt(event.pos())
            if not isinstance(pointedItem, InPort):
                self.rightButtonMenu(event)

        elif event.button() == QtCore.Qt.LeftButton:
            event.accept()
            # self.scene().unselectAllItems()
        else:
            event.ignore()
            QtWidgets.QGraphicsView.mousePressEvent(self, event)
            super(GraphWidget, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning or self.scene().rubberBand or self.scene().line:
            self.viewAndSceneForcedUpdate()
        self.mousePos = self.mapToScene(QtCore.QPoint(event.x(), event.y()))
        super(GraphWidget, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # GRAPHICS VIEW
        printMouseEvent(self, event)
        modifiers = getKeyboardModifiers()

        self.viewAndSceneForcedUpdate()

        if self._panning:
            event.accept()
            leftbutton_event = QtGui.QMouseEvent(
                event.type(), event.pos(), event.globalPos(),
                QtCore.Qt.LeftButton, event.buttons(), modifiers)
            leftbutton_event.accept()
            super(GraphWidget, self).mouseReleaseEvent(leftbutton_event)
            self._panning = False
            return

        # delete edge via input port
        if event.button() == QtCore.Qt.RightButton:
            pointedItem = self.itemAt(event.pos())
            if isinstance(pointedItem, InPort):
                edge = pointedItem.edge()
                if edge:
                    self.scene().removeItem(edge)
                    # remove from ports
                    edge.detachSelf(tracer=True)
                    event.accept()

        # propagate to other view items (nodes)
        QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
        if event.isAccepted():
            return

        if event.button() == QtCore.Qt.RightButton:
            pointedItem = self.itemAt(event.pos())
            if isinstance(pointedItem, InPort):
                event.accept()

        elif event.button() == QtCore.Qt.LeftButton:
            event.accept()
        # elif event.button() == QtCore.Qt.MidButton:
        #    event.accept()
        else:
            event.ignore()
            QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
            super(GraphWidget, self).mouseReleaseEvent(event)

    def rightButtonMenu(self, event):
        # MOUSE MENU
        pointedItem = self.itemAt(event.pos())
        if isinstance(pointedItem, Edge):
            event.accept()
            pointedItem.setSelected(True)
            pointedItem.update()
            menu = QtWidgets.QMenu(self)
            deleteEdgeAction = menu.addAction("Delete")
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == deleteEdgeAction:
                # remove from scene
                self.scene().removeItem(pointedItem)
                # remove from ports
                pointedItem.detachSelf()
                # remove from memory
                # del pointedItem
            else:
                pointedItem.setSelected(False)
                pointedItem.update()
        else:
            event.accept()

            # save position before any choice is made
            self._event_pos = event.pos()

            # main menu
            menu = QtWidgets.QMenu(self.parent)

            # search
            qle = QtWidgets.QLineEdit()
            qle.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
            qle.setPlaceholderText('  Search')
            qle.textChanged.connect(lambda txt: self._library.searchMenu(txt, qle, menu))
            wac = QtWidgets.QWidgetAction(menu)
            msg = 'Search for nodes and networks in the library.'
            wac.hovered.connect(lambda who=msg: self.setStatusTip(who))
            wac.setDefaultWidget(qle)
            menu.addAction(wac)
            menu.addSeparator()

            # favorites at the top, then full library
            #if 'Favorites' in self._library.libMenus():
            #    menu.addMenu(self._library.libMenus()['Favorites'])

            # add a text label
            #menu.addSeparator()
            #menu.addAction(u'\u25BC'+u' Libraries')

            menu.addSeparator()

            for libmenu in self._library.libMenu():
                ma = menu.addMenu(libmenu) # previously generated
                msg = 'Select nodes from the \''+str(ma.text())+'\' library.'
                ma.hovered.connect(lambda who=msg: self.setStatusTip(who))

            pasteAct = QtWidgets.QAction("&Paste", self, shortcut="Ctrl+V",
                            statusTip="Paste node(s) from the copybuffer.")

            copyAct = QtWidgets.QAction("Copy", self, shortcut="Ctrl+C",
                            statusTip="Copy node(s) to the copybuffer.")

            saveAct = QtWidgets.QAction("Save Network", self, shortcut="Ctrl+S",
                            statusTip="Save network to a file.")

            loadAct = QtWidgets.QAction("Load Network", self, shortcut="Ctrl+L",
                            statusTip="Load network from a file (also drag'n drop).")

            layoutMenu = QtWidgets.QMenu('New Layout')
            layoutMenu.addAction(QtWidgets.QAction("Vertical", self,
                            statusTip="Opens a vertically expanding layout window for widgets.",
                            triggered = lambda: self.newLayoutWindow(config=0)))
            layoutMenu.addAction(QtWidgets.QAction("Horizontal", self,
                            statusTip="Opens a horizontally expanding layout window for widgets.",
                            triggered = lambda: self.newLayoutWindow(config=1)))
            layoutMenu.addAction(QtWidgets.QAction("Mixed", self,
                            statusTip="Opens a fixed & mixed layout window for widgets.",
                            triggered = lambda: self.newLayoutWindow(config=2)))
            layoutMenu.addAction(QtWidgets.QAction("Expanding", self,
                            statusTip="Opens an expanding mixed layout window for widgets.",
                            triggered = lambda: self.newLayoutWindow(config=3)))

            quitAct = QtWidgets.QAction("Quit", self,
                            statusTip="Quit GPI without saving.")

            clearAct = QtWidgets.QAction("Clear Canvas", self,
                            statusTip="Delete all nodes on the canvas.")

            pauseAct = QtWidgets.QAction("Pause", self, shortcut="Ctrl+P", checkable = True, triggered=lambda: self.pauseToggle(quiet=False),
                            statusTip="Pause the execution queue on this canvas.")
            if self.inPausedState():
                pauseAct.setChecked(True)
            else:
                pauseAct.setChecked(False)

            macroAct = QtWidgets.QAction("Macro Node", self, checkable = True, triggered = lambda: self.newMacroNode(event.pos()),
                            statusTip="Instantiate Macro Node Objects.")
            if self.isMacroModule():
                macroAct.setChecked(True)
            else:
                macroAct.setChecked(False)

            # basic editor actions
            menu.addSeparator()
            menu.addAction(copyAct)
            menu.addAction(pasteAct)
            menu.addSeparator()
            menu.addAction(saveAct)
            menu.addAction(loadAct)
            menu.addSeparator()
            menu.addAction(pauseAct)
            menu.addSeparator()
            menu.addAction(clearAct)
            menu.addAction(macroAct)
            menu.addMenu(layoutMenu)
            #menu.addSeparator()
            
            # trigger a search menu close when the main menu is hovered
            menu.hovered.connect(lambda: self._library.removeSearchPopup())

            #quitAction = menu.addAction(quitAct)
            action = menu.exec_(self.mapToGlobal(event.pos()))

            self._library.removeSearchPopup()

            if action == copyAct:
                self.copyNodesToBuffer()

            if action == pasteAct:
                # mouse-menu paste
                s = {'sig': 'load', 'subsig': 'paste', 'pos': self.mapToScene(event.pos())}
                self.addNodeRun(s)

            if action == clearAct:  # DELETE
                #self._switchSig.emit('deleteAll')  # change state

                reply = QtWidgets.QMessageBox.question(self, 'Message',
                            "Delete all modules on this canvas?", QtWidgets.QMessageBox.Yes |
                                QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

                if reply == QtWidgets.QMessageBox.Yes:
                    self.deleteNodeRun('deleteAll')

            if action == loadAct:
                s = {'sig': 'load', 'subsig': 'dialog',
                     'pos': self.mapToScene(event.pos())}
                self.addNodeRun(s)
                #self._switchSig_info.emit(s)

            if action == saveAct:
                self._network.saveNetworkFromFileDialog(self.serializeCanvas())

            if action == quitAct:
                pass
                # pausing might make quitting more graceful
                #self._switchSig.emit('pause')
                #self.closeGraph(event)
                #QtWidgets.qApp.quit()

            self.parent.statusBar().clearMessage()

    def setStatusTip(self, msg):
        self.parent.statusBar().showMessage(msg)

    def newMacroNode(self, pos):
        log.debug("drop new macro")
        log.debug(str(pos))
        if isinstance(pos, QtCore.QPointF):
            pos = QtCore.QPoint(pos.x(), pos.y())
        newnode = MacroNode(self, QtCore.QPointF(self.mapToScene(pos)))

        #self.scene().addItem(newnode)
        return newnode


    def showMacroTools(self):
        '''Show the src, sink, and macro layout window.
        '''
        self.macroModuleToggle()

        if self.isMacroModule():
            log.debug("show macro tools")
        else:
            reply = QtWidgets.QMessageBox.question(self, 'Message',
                    "Turn off macro settings for this canvas?\n\nAny src/sink " + \
                    "connections and macro-layouts will be removed.",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.Yes:
                log.debug("hide macro tools")
            else:
                log.debug("cancel hide")
                self.setMacroModule(True)

    def isMacroModule(self):
        return self._macroModule

    def setMacroModule(self, val):
        self._macroModule = val

    def macroModuleToggle(self):
        if self._macroModule:
            self._macroModule = False
        else:
            self._macroModule = True

    def closeEvent(self, event):
        self.closeGraphNoDialog()
        event.accept()

    def closeGraphWithDialog(self):
        reply = QtWidgets.QMessageBox.question(self, 'Message',
                    "Close canvas without saving?", QtWidgets.QMessageBox.Yes |
                        QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self.closeGraphNoDialog()
            return True
        return False

    def closeGraphNoDialog(self):
        '''This is the close procedure for a canvas.
        '''
        self._switchSig.emit('pause')
        self.deleteNodeRun('deleteAll')
        for lm in self._layoutwindowList:
            if lm:  # some may have already been closed
                lm.close()

    def pauseToggle(self, quiet=False):
        '''toggle the pause state for attached buttons.
        '''
        if self.inPausedState():
            self._switchSig.emit('unpause')
        else:
            if quiet:
                self._switchSig_info.emit({'sig':'pause', 'subsig':'quiet'})
            else:
                self._switchSig.emit('pause')

    def copyNodesToBuffer(self):
        self.parent._copybuffer = self.serializeGraphData(selectedOnly=True)

    # NETWORK SERIALIZATION

    def deserializeGraphData(self, graph_settings, layoutSettings=[], pos=None, offset=False, randoffset=False, reloadnode=False, copy_connections=False):
        log.info("num nodes: " + str(len(graph_settings['nodes'])))

        # determine network center randomly to avoid overlap
        rx = 0
        ry = 0
        if offset:
            # this places modules at a slight offset to their orig-pos.
            # used for keystroke copy/paste
            # -keep original position and add this offset
            radius = 5.0  # pts
            rx += radius * 6.0
            ry += radius * 6.0

        if randoffset:
            # if a network is loaded by menu more than once, this small
            # perturbation makes it easy to distinguish between multiple
            # instances
            radius = 5.0  # pts
            rx += random.random() * radius
            ry += random.random() * radius

        if pos:
            # if the position is supplied then the graph should be
            # instantiated relative to it.
            graph_settings = self.subtractAvgPosFromSettings(graph_settings)
            rx += pos.x()
            ry += pos.y()

        # temporarily buffer nodes in case this network is going to be merged
        buf = []
        macro_buf = []
        skipped_mods = []
        new_nodes = []

        # for reloading nodes use the existing nodes on the canvas so that
        # the IDs match for connecting edges.
        if reloadnode:
            buf += self.getAllNodes()

        # place all nodes on the canvas
        for s in graph_settings['nodes']:

            log.debug("add node: " + str(s['name']))

            # try to import the node module by name
            if s['name'] == '__GPIMacroNode__':
                continue

            # instantiate node
            cpos = QtCore.QPoint(s['pos'][0] + rx, s['pos'][1] + ry)

            # first always try to get the node by library
            node = self.newNode_byKey(s['key'], cpos)
            if node is None:
                log.warn('Failed to find node \''+stw(s['name']) + '\' by scope.')

                # get a list of widget and port names together
                wdg_port_names = []
                for parm in s['widget_settings']['parms']:
                    wdg_port_names.append(parm['name'])
                for port in s['ports']:
                    wdg_port_names.append(port['porttitle'])

                # find from libarary and instantiate on the canvas
                node = self.newNode_byClosestMatch(s['name'], wdg_port_names, cpos)

            # final failure to resolve node
            if node is None:
                log.error('Node \''+stw(s['name']) + '\' failed to load, skipping.')
                skipped_mods.append(str(s['name']))
                continue

            new_nodes.append(node)
            node.setDisabledState(True)  # put in disabled state
            node.setID(s['id'])
            buf.append(node)

            # set other node attributes
            if 'walltime' in s:
                try:  # deprecate this try statement
                    node.appendWallTime(float(s['walltime']))
                except:
                    log.error(stw(node.getModuleName()) + ' has no walltime but walltime was saved as NoneType, skipping...')

            node.loadNodeIFSettings(s['widget_settings'])

            if copy_connections:
                for connection in s['connections']:
                    self.connectPorts(connection[0], node.inportList[connection[1]])

        # place all macro nodes on the canvas and load settings
        #   -done after node instantiation so that widgets can be copied over
        log.debug("Load MacroNodes:")
        log.debug(str(graph_settings['macroNodes']))
        for s in graph_settings['macroNodes']:
            mnode = MacroNode(self, QtCore.QPointF(rx, ry))
            mnode.loadSettings(s, buf, (rx, ry))
            macro_buf.append(mnode)

            for node in mnode.getNodes():
                buf.append(node)

        # once all nodes have been placed,
        # start making connections
        for s in graph_settings['nodes']:

            # remake the connections
            for port in s['ports']:
                for c in port['connections']:
                    # make a new edge given src and dest
                    # get the nodes
                    src = self.getNodeByID(buf, c['src']['nodeID'])
                    dst = self.getNodeByID(buf, c['dest']['nodeID'])

                    if src and dst:
                        # get the ports
                        #outport = src.getPortByNumOrTitle(c['src']['portName'])
                        #inport = dst.getPortByNumOrTitle(c['dest']['portName'])
                        outport = src.getOutPort(c['src']['portName'])
                        inport = dst.getInPort(c['dest']['portName'])

                        # each connection is stored twice (memory of each node)
                        # only use one for each pair
                        try:
                            log.debug("inport title: "+inport.portTitle)
                            if len(inport.edges()) > 0:
                                log.debug("Inport occupied," \
                                    + " connection dropped.")
                            else:
                                # make the connection
                                newEdge = Edge(outport, inport)
                                self.scene().addItem(newEdge)
                        except:
                            log.warn("Duplicate or connection" \
                                + " not found.  Skip connection.")
                    else:
                        log.warn("Src and Dst not" \
                            + " accurately saved.  Skip connection.")

        self.scene().unselectAllItems()

        # load layouts before the ids get reset.
        for lw in layoutSettings:
            self.newLayoutWindowFromSettings(lw, buf)

        # reset node IDs, and widget IDs
        for node in buf:
            node.setID()
            for parm in node.getParmList():
                parm.set_id()

        # reset node IDs, and widget IDs select only newly loaded network items
        if reloadnode:
            # for reloading nodes
            for node in new_nodes:
                node.setSelected(True)
                node.setEventStatus({GPI_INIT_EVENT: None})
                node.displayReloaded()
        else:
            # for importing networks
            for node in buf:
                node.setSelected(True)
                node.setEventStatus({GPI_INIT_EVENT: None})

        # reset macro IDs
        for node in macro_buf:
            if node.shouldCollapse():
                node.setCollapse(True)
            node.resetIDs()

        self.calcNodeHierarchy()

        # put nodes back in to idle
        for node in buf:
            node.setDisabledState(False)

        QtWidgets.QApplication.processEvents()  # allow gui to update

        if len(skipped_mods):
            log.error("Failed to load the following modules: ")
            for name in skipped_mods:
                log.error("\t" + name)

        if not reloadnode:
            try:
                # get top most node position-wise
                # and make sure its visible
                topnode = buf[0]
                for node in buf:
                    if node.pos().y() < topnode.pos().y():
                        topnode = node
                self.ensureVisible(topnode)
            except:
                log.warn("Can\'t determine top node, skipping.")

    def getNodeByID(self, buf, nid):
        for item in buf:
            if isinstance(item, Node):
                if item.getID() == nid:
                    return item

    def calcAvgPosFromSettings(self, graph_settings):
        cnt = 0.
        ax = 0.
        ay = 0.

        # macro nodes
        for mnode in graph_settings['macroNodes']:
            node = mnode['src_settings']
            ax += node['pos'][0]
            ay += node['pos'][1]
            cnt += 1.

            node = mnode['sink_settings']
            ax += node['pos'][0]
            ay += node['pos'][1]
            cnt += 1.

            node = mnode['face_settings']
            ax += node['pos'][0]
            ay += node['pos'][1]
            cnt += 1.

        # normal nodes
        for node in graph_settings['nodes']:
            ax += node['pos'][0]
            ay += node['pos'][1]
            cnt += 1.

        ax = ax / cnt
        ay = ay / cnt
        return(ax, ay)

    def subtractAvgPosFromSettings(self, graph_settings):
        ax, ay = self.calcAvgPosFromSettings(graph_settings)
        for s in graph_settings['nodes']:
            if 'connections' in s.keys(): del s['connections']
        newgraphsettings = copy.deepcopy(graph_settings)
        #newgraphsettings = graph_settings

        # macro nodes
        for mnode in newgraphsettings['macroNodes']:
            node = mnode['src_settings']
            node['pos'][0] -= ax
            node['pos'][1] -= ay

            node = mnode['sink_settings']
            node['pos'][0] -= ax
            node['pos'][1] -= ay

            node = mnode['face_settings']
            node['pos'][0] -= ax
            node['pos'][1] -= ay

        for node in newgraphsettings['nodes']:
            node['pos'][0] -= ax
            node['pos'][1] -= ay

        return(newgraphsettings)

    def serializeGraphData(self, selectedOnly=False, minusAvgPos=False):
        # Handles only nodes and macro-nodes.  The 'selectedOnly' option is
        # for copy/paste operation.

        graph_settings = {}
        graph_settings['nodes'] = []
        graph_settings['macroNodes'] = []

        # serialize all nodes and macro nodes
        if selectedOnly:
            nodes = self.getSelectedNodes()
            macroNodes, enodes = self.getSelectedMacroNodes()
            nodes = list(set(nodes + enodes))
        else:
            nodes = self.getAllNodes()
            macroNodes, enodes = self.getAllMacroNodes()
            nodes = list(set(nodes + enodes))

        for node in nodes:
            node_copy = copy.deepcopy(node.getSettings())
            node_copy['connections'] = node.getInputConnections()
            graph_settings['nodes'].append(node_copy)

        for nid, nodes in list(macroNodes.items()):
            graph_settings['macroNodes'].append(nodes[0].macroParent().getSettings())

        if minusAvgPos and (len(graph_settings['nodes']) + len(graph_settings['macroNodes'])):
            graph_settings = self.subtractAvgPosFromSettings(graph_settings)

        return graph_settings

    def serializeCanvas(self):
        network = {}
        network['nodes'] = self.serializeGraphData(minusAvgPos=True)
        network['layouts'] = self.serializeLayoutWindows()
        network['WALLTIME'] = str(self.walltime())  # sec
        network['TOTAL_PMEM'] = str(self.totalPortMem())  # bytes
        return network

    def deserializeCanvas(self, network, pos):
        # convert the loaded file data into the format required by GPI objects
        # and instantiate the network on the canvas.
        nodes = network['nodes']
        layouts = network['layouts']

        if nodes:
            log.info("load nodes.")
        else:
            log.error("network description contains no node information!!!")
            return

        if layouts:
            log.info("network has layouts.")
            self.deserializeGraphData(nodes, layoutSettings=layouts, pos=pos)
        else:
            self.deserializeGraphData(nodes, pos=pos)


