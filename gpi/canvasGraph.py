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

from __future__ import annotations

import gc
import os
import sys
import copy
import math
import time
import types as _types
import random
import traceback
from typing import Optional


# gpi
import gpi
from gpi import QtCore, QtGui, QtWidgets
from .associate import Bindings, isGPIAssociatedFile, isGPIAssociatedExt
from .canvasScene import CanvasScene
from .cmd import Commands
from .defines import GPI_REQUEUE_EVENT, GPI_INIT_EVENT, GPI_WIDGET_EVENT, GPI_PORT_EVENT
from .defines import getKeyboardModifiers, printMouseEvent, stw
from .defines import isMacroChildNode
from .defines import GetHumanReadable_bytes, GPI_APPLOOP, GetHumanReadable_time
from .defines import isGPINetworkFile, isGPIModFile, InPortTYPE
from .edge import Edge
from .layoutWindow import LayoutMaster
from .library import Library, NodeCatalogItem
from .shortcuts import CanvasShortcuts


class _BrokenNodeCatalogItem(NodeCatalogItem):
    """Stub catalog item for nodes whose source file failed to load.

    Overrides reload() so that newNode_byNodeCatalogItem() cannot wipe the
    dynamically-created stub module by re-running the broken file.
    """
    def reload(self):
        pass  # never re-load from the broken file

    def valid(self):
        return self.mod is not None
from .macroNode import MacroNode
from .network import Network
from .node import Node
from .nodeQueue import GPINodeQueue
from .port import Port, InPort
from .stateMachine import GPI_FSM, GPIState
from . import topsort
from .config import Config
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
        self._cs = CanvasShortcuts()  # configurable canvas key bindings

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
        self._nodes_running = 0   # in-flight counter; O(1) alternative to aNodeIsProcessing()
        self.extWidgets = dict()

        # Repaint throttle — collapses many back-to-back update requests into
        # one paint per 16ms frame (~60fps cap). Single-shot so it only fires
        # when there is actually something pending.
        self._repaint_pending = False
        self._repaint_timer = QtCore.QTimer(self)
        self._repaint_timer.setSingleShot(True)
        self._repaint_timer.setInterval(16)
        self._repaint_timer.timeout.connect(self._doRepaint)

        # TODO: this probably should go to the MainCanvas
        self._library = Library(self)
        #self._library.scanGPIModulesIn_SysPath(recursion_depth=2)
        #self._library.generateLibMenus()

        self._event_pos = QtCore.QPoint(0, 0)

        self._network = Network(self)

        self._pause_quiet = False

        # fast O(1) node lookup — maintained in sync with scene add/remove
        self._nodes = []

        # snapshot-based undo/redo (serialized graph dicts)
        self._undo_stack = []
        self._redo_stack = []
        self._undo_max = 20
        self._undo_in_progress = False

        # hierarchy cache — invalidated when topology changes
        self._hierarchy_valid = False
        self._hierarchy_cache = None
        self._linear_cache = None   # sorted-by-level list; rebuilt by calcNodeHierarchy

        self._initSearchBar()
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
        pos = QtCore.QPoint(int(x), int(y))
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
                self._machine, efunc=self.processingLeave)
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
                    pos = QtCore.QPoint(int(pos.x()), int(pos.y()))

                    s = {'sig': 'load', 'subsig': 'net', 'path':
                            path, 'pos': pos}
                    self.addNodeRun(s)

            # load nodes
            if Commands.modCount():
                for path in Commands.mods():

                    pos = self.getEventPos_randomDev(rad=50)
                    pos = QtCore.QPoint(int(pos.x()), int(pos.y()))

                    s = {'sig': 'load', 'subsig': 'mod',
                            'path': path, 'pos': pos, 'from': 'cmd.Commands'}
                    self.addNodeRun(s)

            # load associated files
            if Commands.fileCount():
                for path in Commands.files():

                    pos = self.getEventPos_randomDev(rad=50)
                    pos = QtCore.QPoint(int(pos.x()), int(pos.y()))

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
        self._nodes.append(newnode)
        self._markHierarchyDirty()
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
                pos = QtCore.QPoint(int(x), int(y))
            else:
                pos = sig['pos']

            # instantiate node on canvas
            if "mapit" not in sig.keys():
                mapit = True
            else:
                mapit = sig['mapit']
            self._pushUndoCheckpoint()
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
            self._pushUndoCheckpoint()
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
                self._pushUndoCheckpoint()
                self.deserializeGraphData(self.parent._copybuffer, pos=sig['pos'])

        elif sig['subsig'] == 'keypaste':
            if self.parent._copybuffer and 'copy_connections' in sig.keys():
                self._pushUndoCheckpoint()
                self.deserializeGraphData(self.parent._copybuffer, offset=True, randoffset=True, copy_connections=sig['copy_connections'])
            else:
                self._pushUndoCheckpoint()
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
        return self._nodes_running > 0

    def processingLeave(self, sig):
        """Called when exiting processing state."""
        self.viewAndSceneForcedUpdate()

    def processingRun(self, sig):
        self._curState.emit(self._processingStateSig)
        self.printCurState()

        # Start all nodes that are ready and have no running upstreams.
        # Looping allows independent branches to launch concurrently in one pass.
        while True:
            queueState = self.nodeQueue.startNextAvailableNode()
            if queueState == 'started':
                continue  # immediately try to start another independent node
            elif queueState == 'waiting':
                break  # nodes remain but their upstreams are still running
            elif queueState == 'paused':
                self._switchSig.emit('pause')
                break
            else:  # 'finished'
                # Queue drained; only advance to check-events once every
                # in-flight node has also completed.
                if not self.aNodeIsProcessing():
                    self._switchSig.emit('check')
                elif not self.nodeQueue.isEmpty():
                    # debounceUISignals() already inserted the unblocked
                    # downstream nodes directly — no full rebuild needed.
                    continue   # re-enter dispatch loop to start them
                break

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
        y = self.geometry().height() // 2
        x = self.geometry().width() // 2
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
            paths = [x.toLocalFile() for x in mimeData.urls()]
            log.debug(paths)

            # if multiple drops, then add random offsets to pos
            if len(paths) == 1:
                poses = [event.pos()]
            else:
                poses = []
                for path in paths:
                    m = 50
                    rand = QtCore.QPoint(int(random.random()*m), int(random.random()*m))
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
            was_processing = node.isProcessingEvent()
            if isMacroChildNode(node):
                node.macroParent().readyForDeletion()
                for n in node.getSiblingNodes():
                    self.nodeQueue.removeNode(n)
                    n.readyForDeletion()
                    if n.scene():
                        self.scene().removeItem(n)
                    if n in self._nodes:
                        self._nodes.remove(n)
            elif node:
                node.readyForDeletion()
                if node.scene():
                    self.scene().removeItem(node)
                if node in self._nodes:
                    self._nodes.remove(node)
            self._markHierarchyDirty()
            if was_processing and self._nodes_running > 0:
                self._nodes_running -= 1

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
        if selnodes:
            self._pushUndoCheckpoint()
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

    def getAllNodes(self) -> list:
        return list(self._nodes)

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

    def getSelectedNodes(self) -> list:
        return [n for n in self._nodes if n.isSelected()]

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
        if self._linear_cache is not None:
            return list(self._linear_cache)   # return copy; caller may mutate
        return self.getLinearNodeHierarchy_fromList(self.getAllNodes())

    def getLinearNodeHierarchy_fromList(self, nodeList):
        return sorted(nodeList, key=lambda y: y.getHierarchalLevel())

    def requestRepaint(self):
        '''Schedule a repaint on the next 16ms tick. Multiple calls within
        the same tick are collapsed into a single paint — zero redundancy.
        '''
        if not self._repaint_pending:
            self._repaint_pending = True
            self._repaint_timer.start()

    def _doRepaint(self):
        '''Actual paint — called by the single-shot timer, at most ~60fps.'''
        self._repaint_pending = False
        if Commands.noGUI():
            return
        self.update()
        self.scene().update()

    def viewAndSceneForcedUpdate(self):
        '''Schedule a batched repaint. All back-to-back calls within 16ms
        are collapsed into one paint — replaces the old immediate update().
        '''
        log.debug("viewAndSceneForcedUpdate called")
        self.requestRepaint()

    def _markHierarchyDirty(self) -> None:
        self._hierarchy_valid = False
        self._hierarchy_cache = None
        self._linear_cache = None

    def calcNodeHierarchy(self) -> Optional[list]:
        if self._hierarchy_valid:
            return self._hierarchy_cache

        nodeList = self.getAllNodes()

        c = []
        for node in nodeList:
            if len(node.getNonCyclicConnectionTuples()):
                c += node.getNonCyclicConnectionTuples()
            else:
                node.resetHierarchalLevel()
                node.refreshName()

        sortedNodes = topsort.topsort(c)

        if sortedNodes is None:
            return None

        cnt = 0
        for node in sortedNodes:
            node.setHierarchalLevel(cnt)
            cnt += 1

        self._hierarchy_cache = sortedNodes
        self._hierarchy_valid = True
        # Cache sorted-by-level list covering all nodes (including disconnected)
        self._linear_cache = sorted(self._nodes, key=lambda n: n.getHierarchalLevel())
        return sortedNodes

    def roundPosToGrid(self, pos):
        x = int(pos[0] / self.gridRes) * self.gridRes
        y = int(pos[1] / self.gridRes) * self.gridRes
        return(x, y)

    def setCanvasShortcuts(self, cs):
        """Replace the CanvasShortcuts instance (called by mainWindow on load)."""
        self._cs = cs

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = getKeyboardModifiers()
        cs = self._cs

        if cs.matches('copy', key, modifiers):
            self.copyNodesToBuffer()

        elif cs.matches('paste_connect', key, modifiers):
            if self.parent._copybuffer:
                self.addNodeRun({'sig': 'load', 'subsig': 'keypaste', 'copy_connections': True})
            else:
                log.warn("Nothing in buffer to paste.")

        elif cs.matches('paste', key, modifiers):
            if self.parent._copybuffer:
                self.addNodeRun({'sig': 'load', 'subsig': 'keypaste'})
            else:
                log.warn("Nothing in buffer to paste.")

        elif cs.matches('delete', key, modifiers) or key == QtCore.Qt.Key_Backspace:
            self.deleteNodeRun('delete')

        elif cs.matches('undo', key, modifiers):
            self.undoAction()

        elif cs.matches('redo', key, modifiers):
            self.redoAction()

        elif cs.matches('find', key, modifiers):
            if self._search_bar.isVisible():
                self._closeSearch()
            else:
                self._search_bar.show()
                self._repositionSearchBar()
                self._search_edit.setFocus()
                self._search_edit.selectAll()

        elif cs.matches('load', key, modifiers):
            self.addNodeRun({'sig': 'load', 'subsig': 'dialog'})

        elif cs.matches('save', key, modifiers):
            self._network.saveNetworkFromFileDialog(self.serializeCanvas())

        elif cs.matches('select_all', key, modifiers):
            self.scene().makeOnlyTheseNodesSelected(self.getAllNodes())

        elif cs.matches('reload', key, modifiers):
            self.reload_node()

        elif cs.matches('organize', key, modifiers):
            self.organizeSelectedNodes()

        elif cs.matches('pause', key, modifiers) or key == QtCore.Qt.Key_Space:
            self.pauseToggle()

        elif cs.matches('close_menus', key, modifiers):
            self.closeAllNodeMenus()

        elif cs.matches('zoom_in', key, modifiers):
            self.scaleView(1.2)

        elif cs.matches('zoom_out', key, modifiers):
            self.scaleView(1 / 1.2)

        # ── Non-configurable / debug bindings ─────────────────────────────────
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

        elif key == QtCore.Qt.Key_Tab:
            snodes = self.getSelectedNodes()
            if len(snodes):
                snode = snodes[0]
                nodes = self.getLinearNodeHierarchy()
                for i in range(len(nodes)):
                    if nodes[i] == snode:
                        if i < len(nodes) - 1:
                            self.scene().makeOnlyTheseNodesSelected([nodes[i + 1]])
                        else:
                            self.scene().makeOnlyTheseNodesSelected([nodes[0]])
                        self.requestRepaint()
                        return
            else:
                nodes = self.getLinearNodeHierarchy()
                self.scene().makeOnlyTheseNodesSelected([nodes[0]])
                self.requestRepaint()

        elif key == QtCore.Qt.Key_M and modifiers == QtCore.Qt.ControlModifier:
            if "Ctrl+M" not in self.hotkeys:
                for item in list(self.scene().items()):
                    if isinstance(item, Node):
                        item.setPos(-150 + random.randint(0, 299),
                                    -150 + random.randint(0, 299))

        elif key == QtCore.Qt.Key_R and modifiers == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if "Ctrl+Shift+R" not in self.hotkeys:
                self.chargeRepON = not self.chargeRepON
                if self.chargeRepON:
                    self.itemMoved()
                log.dialog("toggle chargeRepON:" + str(self.chargeRepON))

        elif key == QtCore.Qt.Key_W and modifiers == QtCore.Qt.ControlModifier:
            self.parent.resize(1024, 768)

        else:
            super(GraphWidget, self).keyPressEvent(event)

    def addNodeByName(self, name, pos=QtCore.QPoint(50, 35)):
        # Try exact name first, then key (full path like "gpi_core.display.ImageDisplay").
        item = self._library.findNode_byName(name) or self._library.findNode_byKey(name)
        if item is None:
            log.warn("addNodeByName: '{}' not found in library.".format(name))
            return None
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
        if node is None:
            log.dialog("Node '{}' not found — check the name in Modify Shortcuts.".format(name))
            return
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
                    self._markHierarchyDirty()
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
        self._markHierarchyDirty()
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
        self.parent._copybuffer = self.serializeGraphData(
            selectedOnly=True, preserve_external_connections=True)

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
        from collections import defaultdict, deque
        nodes = self.getSelectedNodes()
        if not nodes:
            return

        horizontal_flow = (Config.APPEARANCE_STYLE != 'Classic'
                           and Config.LAYOUT_DIRECTION == 'Horizontal')

        # Preserve center of mass so the graph stays roughly in place.
        orig_cx = sum(n.scenePos().x() for n in nodes) / len(nodes)
        orig_cy = sum(n.scenePos().y() for n in nodes) / len(nodes)

        node_set = set(nodes)

        def sel_children(n):
            out = []
            for port in n.outportList:
                for edge in port.edgeList:
                    c = edge.dest.getNode()
                    if c in node_set and c is not n:
                        out.append(c)
            return out

        def sel_parents(n):
            out = []
            for port in n.inportList:
                for edge in port.edgeList:
                    p = edge.source.getNode()
                    if p in node_set and p is not n:
                        out.append(p)
            return out

        # ── Split into connected components (undirected BFS) ───────────────
        visited = set()
        components = []
        isolated = []
        for start in nodes:
            if start in visited:
                continue
            nbrs = set(sel_children(start)) | set(sel_parents(start))
            if not nbrs:
                isolated.append(start)
                visited.add(start)
                continue
            comp = []
            q = deque([start])
            visited.add(start)
            while q:
                n = q.popleft()
                comp.append(n)
                for nb in set(sel_children(n)) | set(sel_parents(n)):
                    if nb not in visited:
                        visited.add(nb)
                        q.append(nb)
            components.append(comp)

        # ── Node size helpers ──────────────────────────────────────────────
        def node_flow_size(n):
            return n.getNodeWidth_V() if horizontal_flow else n.getNodeHeight()

        def node_cross_size(n):
            if horizontal_flow:
                return n.getNodeHeight_V()
            return n.getNodeWidth() + n.getProgressWidth() + n.getExtraWidth()

        FLOW_GAP  = 20   # gap between depth levels
        CROSS_GAP = 15   # gap between nodes at the same depth
        COMP_SEP  = 60   # gap between disconnected subgraphs

        # ── Lay out one connected component → {node: (x, y)} ──────────────
        def layout_component(comp):
            comp_set = set(comp)

            # BFS depth from source nodes (in-degree 0 inside component)
            in_deg = {n: sum(1 for p in sel_parents(n) if p in comp_set)
                      for n in comp}
            depth = {}
            q = deque()
            for n in comp:
                if in_deg[n] == 0:
                    depth[n] = 0
                    q.append(n)
            while q:
                n = q.popleft()
                for c in sel_children(n):
                    if c not in comp_set:
                        continue
                    depth[c] = max(depth.get(c, 0), depth[n] + 1)
                    in_deg[c] -= 1
                    if in_deg[c] == 0:
                        q.append(c)
            for n in comp:
                depth.setdefault(n, 0)  # cycles fall back to level 0

            # Push leaf nodes right: if a leaf's parent also directly feeds a
            # deeper node, the leaf gets aligned to that deeper node's depth so
            # it sits parallel to it rather than one column earlier.
            def is_leaf(n):
                return not any(edge.dest.getNode() in comp_set
                               for port in n.outportList
                               for edge in port.edgeList)

            for n in comp:
                if not is_leaf(n):
                    continue
                for parent in sel_parents(n):
                    sibling_max = max(
                        (depth[s]
                         for port in parent.outportList
                         for edge in port.edgeList
                         for s in (edge.dest.getNode(),)
                         if s in comp_set and s is not n),
                        default=depth[n]
                    )
                    depth[n] = max(depth[n], sibling_max)

            levels = defaultdict(list)
            for n in comp:
                levels[depth[n]].append(n)

            # For nodes with no cross-positioned parents (depth-0 sources), find the
            # inport index this chain connects to at the first downstream convergence
            # node (in-degree > 1).  That gives a stable, position-independent order
            # that reflects the graph's own port numbering.
            def _convergence_inport_hint(source):
                seen = {source}
                q2 = deque([source])
                while q2:
                    n = q2.popleft()
                    for port in n.outportList:
                        for edge in port.edgeList:
                            child = edge.dest.getNode()
                            if child not in comp_set:
                                continue
                            if sum(1 for p in sel_parents(child)
                                   if p in comp_set) > 1:
                                return edge.dest.portNum
                            if child not in seen:
                                seen.add(child)
                                q2.append(child)
                return None

            cross_pos = {}
            for d in sorted(levels.keys()):
                level = levels[d]
                def _pk(n):
                    pcs = [cross_pos[p] for p in sel_parents(n) if p in cross_pos]
                    if pcs:
                        return sum(pcs) / len(pcs)
                    hint = _convergence_inport_hint(n)
                    if hint is not None:
                        return float(hint)
                    return n.scenePos().y() if horizontal_flow else n.scenePos().x()
                level.sort(key=_pk)
                # Centre this level around the mean of each node's ideal cross
                # position (parent-cross average).  Without this, a level with a
                # single node (e.g. FFTW alone at depth 2) snaps to Y=0 — the
                # midpoint of the whole layout — instead of staying aligned with
                # its parent chain.
                ideals = [_pk(n) for n in level]
                level_center = sum(ideals) / len(ideals)
                sizes = [node_cross_size(n) for n in level]
                total = sum(sizes) + CROSS_GAP * max(0, len(level) - 1)
                cursor = level_center - total / 2.0
                for i, n in enumerate(level):
                    cross_pos[n] = cursor + sizes[i] / 2.0
                    cursor += sizes[i] + CROSS_GAP

            # Flow positions: one depth level per row/column, top-aligned at 0
            flow_pos = {}
            cursor = 0.0
            for d in sorted(levels.keys()):
                level = levels[d]
                for n in level:
                    flow_pos[n] = cursor
                cursor += max(node_flow_size(n) for n in level) + FLOW_GAP

            return {n: (flow_pos[n], cross_pos[n]) if horizontal_flow
                       else (cross_pos[n], flow_pos[n])
                    for n in comp}

        # ── Compute layouts for all components ─────────────────────────────
        comp_layouts = [layout_component(c) for c in components]

        def bbox(layout):
            xs = [p[0] for p in layout.values()]
            ys = [p[1] for p in layout.values()]
            return min(xs), min(ys), max(xs), max(ys)

        # ── Place components side-by-side perpendicular to flow ────────────
        all_positions = {}

        if horizontal_flow:
            # flow = x, cross = y → stack components vertically
            cross_cursor = 0.0
            for comp, layout in zip(components, comp_layouts):
                minx, miny, maxx, maxy = bbox(layout)
                for n, (x, y) in layout.items():
                    all_positions[n] = (x - minx, y - miny + cross_cursor)
                cross_cursor += (maxy - miny) + COMP_SEP
            total_cross = cross_cursor - COMP_SEP
            for n in list(all_positions):
                x, y = all_positions[n]
                all_positions[n] = (x, y - total_cross / 2.0)
        else:
            # flow = y, cross = x → place components horizontally
            cross_cursor = 0.0
            for comp, layout in zip(components, comp_layouts):
                minx, miny, maxx, maxy = bbox(layout)
                for n, (x, y) in layout.items():
                    all_positions[n] = (x - minx + cross_cursor, y - miny)
                cross_cursor += (maxx - minx) + COMP_SEP
            total_cross = cross_cursor - COMP_SEP
            for n in list(all_positions):
                x, y = all_positions[n]
                all_positions[n] = (x - total_cross / 2.0, y)

        # ── Isolated nodes: stacked at the far end of the layout ───────────
        if isolated:
            if all_positions:
                if horizontal_flow:
                    anchor = (max(x for x, y in all_positions.values()) + COMP_SEP, 0.0)
                else:
                    anchor = (0.0, max(y for x, y in all_positions.values()) + COMP_SEP)
            else:
                anchor = (0.0, 0.0)
            for n in isolated:
                all_positions[n] = anchor  # intentionally stacked

        # ── Re-centre around original centre of mass ───────────────────────
        new_cx = sum(x for x, y in all_positions.values()) / len(all_positions)
        new_cy = sum(y for x, y in all_positions.values()) / len(all_positions)
        dx = orig_cx - new_cx
        dy = orig_cy - new_cy

        # ── Animate ────────────────────────────────────────────────────────
        self._node_anim_group = QtCore.QParallelAnimationGroup()
        for node, (x, y) in all_positions.items():
            anim = QtCore.QPropertyAnimation(node, b"pos")
            anim.setDuration(300)
            anim.setStartValue(node.scenePos())
            anim.setEndValue(QtCore.QPointF(x + dx, y + dy))
            self._node_anim_group.addAnimation(anim)
        self._node_anim_group.start()

    def refreshLayout(self):
        """Reposition all ports and edges after a layout-direction change."""
        for node in self.getAllNodes():
            node.prepareGeometryChange()
            for port in node.inportList + node.outportList:
                port.prepareGeometryChange()
                port.resetPos()
            node.update()
        for item in self.scene().items():
            if isinstance(item, Edge):
                item.adjust()
                item.update()

    def _autoOrganizeAll(self):
        """Select all nodes and auto-organize by topology. Dark theme only."""
        if Config.APPEARANCE_STYLE == 'Classic':
            return
        nodes = self.getAllNodes()
        if not nodes:
            return
        self.scene().makeOnlyTheseNodesSelected(nodes)
        self.organizeSelectedNodes()

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
        angle = event.angleDelta().y() / 8
        self.scaleView(math.pow(2.0, angle / 80.0))

    def drawBackground(self, painter, rect):
        sceneRect = self.sceneRect()

        if Config.APPEARANCE_STYLE == 'Classic':
            # ── Classic: original light gradient ─────────────────────────────
            rightShadow  = QtCore.QRectF(sceneRect.right(), sceneRect.top() + 5,
                                         5, sceneRect.height())
            bottomShadow = QtCore.QRectF(sceneRect.left() + 5, sceneRect.bottom(),
                                         sceneRect.width(), 5)
            if rightShadow.intersects(rect)  or rightShadow.contains(rect):
                painter.fillRect(rightShadow, QtCore.Qt.darkGray)
            if bottomShadow.intersects(rect) or bottomShadow.contains(rect):
                painter.fillRect(bottomShadow, QtCore.Qt.darkGray)
            gradient = QtGui.QLinearGradient(sceneRect.topLeft(), sceneRect.bottomRight())
            if self.inPausedState() and not self._pause_quiet:
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.yellow).lighter(190))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.yellow).lighter(170))
            else:
                gradient.setColorAt(0, QtGui.QColor(QtCore.Qt.gray).lighter(180))
                gradient.setColorAt(1, QtGui.QColor(QtCore.Qt.gray).lighter(150))
            painter.fillRect(rect.intersected(sceneRect), QtGui.QBrush(gradient))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(sceneRect)
            textRect = QtCore.QRectF(sceneRect.left() + 4, sceneRect.top() + 4,
                                     sceneRect.width() - 4, sceneRect.height() - 4)
            font = painter.font()
            font.setBold(True)
            font.setPointSize(14)
            painter.setFont(font)
            painter.setPen(QtCore.Qt.lightGray)
            painter.drawText(textRect.translated(2, 2), "Network Canvas")
            painter.setPen(QtCore.Qt.black)
            painter.drawText(textRect, "Network Canvas")
            return

        # ── Dark: dot grid ────────────────────────────────────────────────────
        visible = rect.intersected(sceneRect)
        paused = self.inPausedState() and not self._pause_quiet
        bg = QtGui.QColor('#2e2900') if paused else QtGui.QColor('#1a1a1a')
        painter.fillRect(visible, bg)

        grid = 20
        dot_color = '#4a4500' if paused else '#333333'
        painter.setPen(QtGui.QPen(QtGui.QColor(dot_color), 1.8,
                                  QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
        x0 = int(visible.left()  / grid) * grid
        y0 = int(visible.top()   / grid) * grid
        x1 = int(visible.right() / grid + 1) * grid
        y1 = int(visible.bottom()/ grid + 1) * grid
        pts = QtGui.QPolygonF()
        x = x0
        while x <= x1:
            y = y0
            while y <= y1:
                pts.append(QtCore.QPointF(x, y))
                y += grid
            x += grid
        if not pts.isEmpty():
            painter.drawPoints(pts)

        painter.setPen(QtGui.QPen(QtGui.QColor('#2e2e2e'), 1))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(sceneRect)
        font = painter.font()
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QtGui.QColor('#2e2e2e'))
        painter.drawText(QtCore.QRectF(sceneRect.left() + 8, sceneRect.bottom() - 24, 200, 20),
                         "Network Canvas")

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
        self.mousePos = self.mapToScene(event.pos())
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
            action = menu.exec(self.mapToGlobal(event.pos()))
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
            action = menu.exec(self.mapToGlobal(event.pos()))

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
            pos = QtCore.QPoint(int(pos.x()), int(pos.y()))
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

    # ── Undo / Redo ──────────────────────────────────────────────────────────

    def _pushUndoCheckpoint(self):
        """Snapshot canvas state before a user action. No-op during restore."""
        if self._undo_in_progress:
            return
        self._undo_stack.append(self.serializeGraphData())
        if len(self._undo_stack) > self._undo_max:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _restoreSnapshot(self, snapshot):
        """Restore canvas from a snapshot using a delta approach.
        Only nodes/edges that actually changed are touched; unchanged nodes keep
        their port data and do not recompute.
        """
        self._undo_in_progress = True
        try:
            # Fall back to full restore when macros are involved — delta logic
            # doesn't handle MacroNode topology yet.
            if snapshot.get('macroNodes') or self.getAllMacros():
                self.deleteAllNodes()
                self.deserializeGraphData(snapshot)
                if self.inIdleState():
                    self._switchSig.emit('check')
                self.viewAndSceneForcedUpdate()
                return

            self._applyDelta(snapshot)
            if self.inIdleState():
                self._switchSig.emit('check')
            self.viewAndSceneForcedUpdate()
        finally:
            self._undo_in_progress = False

    def _applyDelta(self, snapshot):
        """Minimal delta between snapshot and current canvas.

        Nodes with a matching ID in both are kept in place (no recomputation).
        Nodes only in the snapshot are restored; they receive PORT_EVENT from
        any upstream node whose output port already has cached data, or
        GPI_INIT_EVENT when no upstream data is available.
        Nodes only on the current canvas are deleted.
        """
        snap_by_id = {s['id']: s for s in snapshot.get('nodes', [])}
        curr_by_id = {n.getID(): n for n in self.getAllNodes()}
        snap_ids = set(snap_by_id)
        curr_ids = set(curr_by_id)

        ids_to_del = curr_ids - snap_ids
        ids_to_add = snap_ids - curr_ids
        ids_common = snap_ids & curr_ids

        # ── Remove nodes absent from snapshot ────────────────────────────────
        for nid in ids_to_del:
            node = curr_by_id[nid]
            node.setDeleteFlag(True)
            node.setDisabledState(True)
            self.nodeQueue.removeNode(node)
            self.deleteNode(node)

        # ── Reposition kept nodes (no events) ────────────────────────────────
        for nid in ids_common:
            s = snap_by_id[nid]
            curr_by_id[nid].setPos(QtCore.QPointF(s['pos'][0], s['pos'][1]))

        # ── Rebuild live map after deletions ─────────────────────────────────
        live_by_id = {n.getID(): n for n in self.getAllNodes()}

        # ── Build desired connection set from snapshot ────────────────────────
        snap_conns = set()
        for s in snapshot.get('nodes', []):
            for port in s.get('ports', []):
                for c in port.get('connections', []):
                    snap_conns.add((
                        c['src']['nodeID'], c['src']['portName'],
                        c['dest']['nodeID'], c['dest']['portName'],
                    ))

        # ── Current connection set ────────────────────────────────────────────
        curr_conns = set()
        for node in live_by_id.values():
            for inport in node.inportList:
                for edge in list(inport.edges()):
                    curr_conns.add((
                        edge.sourcePort().getNode().getID(),
                        edge.sourcePort().portTitle,
                        inport.getNode().getID(),
                        inport.portTitle,
                    ))

        # ── Drop edges that shouldn't exist ──────────────────────────────────
        for conn in curr_conns - snap_conns:
            src_nid, src_pname, dst_nid, dst_pname = conn
            src_n = live_by_id.get(src_nid)
            dst_n = live_by_id.get(dst_nid)
            if src_n and dst_n:
                outport = src_n.getOutPort(src_pname)
                inport = dst_n.getInPort(dst_pname)
                if outport and inport:
                    for edge in list(inport.edges()):
                        if edge.sourcePort() is outport:
                            self.scene().removeItem(edge)
                            edge.detachSelf(update=True)

        # ── Restore missing nodes ─────────────────────────────────────────────
        new_nodes = []
        for nid in ids_to_add:
            s = snap_by_id[nid]
            cpos = QtCore.QPointF(s['pos'][0], s['pos'][1])
            node = self.newNode_byKey(s.get('key', ''), cpos)
            if node is None:
                wdg_port_names = [p['name'] for p in s.get('widget_settings', {}).get('parms', [])]
                wdg_port_names += [p.get('porttitle', '') for p in s.get('ports', [])]
                node = self.newNode_byClosestMatch(s['name'], wdg_port_names, cpos)
            if node is None:
                log.error("_applyDelta: cannot restore node '{}', skipping.".format(s['name']))
                continue
            node.setDisabledState(True)
            node.setID(s['id'])
            node.loadNodeIFSettings(s['widget_settings'])
            live_by_id[nid] = node
            new_nodes.append(node)

        # ── Wire missing edges ────────────────────────────────────────────────
        new_node_ids = {n.getID() for n in new_nodes}
        kept_nodes_needing_event = []  # kept nodes that receive a newly wired edge
        for conn in snap_conns - curr_conns:
            src_nid, src_pname, dst_nid, dst_pname = conn
            src_n = live_by_id.get(src_nid)
            dst_n = live_by_id.get(dst_nid)
            if src_n and dst_n:
                outport = src_n.getOutPort(src_pname)
                inport = dst_n.getInPort(dst_pname)
                if outport and inport and not inport.edges():
                    newEdge = Edge(outport, inport)
                    self.scene().addItem(newEdge)
                    if dst_nid not in new_node_ids:
                        kept_nodes_needing_event.append((dst_n, inport))

        self._markHierarchyDirty()
        self.calcNodeHierarchy()

        # ── Trigger kept nodes that received new edges ────────────────────────
        # Target the event directly — don't use setDownstreamEvents() because
        # that fans out to every node on the upstream port, not just this one.
        for node, inport in kept_nodes_needing_event:
            node.setEventStatus({GPI_PORT_EVENT: inport.portTitle})

        # ── Enable restored nodes; push upstream data or queue INIT ──────────
        for node in new_nodes:
            if getattr(node, '_load_failed', False):
                continue
            node.setDisabledState(False)
            pushed = False
            for inport in node.inportList:
                uport = inport.getUpstreamPort()
                if uport is not None and uport.data is not None:
                    # Port event targeted at this node only — upstream cached
                    # data is read directly when this node computes.
                    node.setEventStatus({GPI_PORT_EVENT: inport.portTitle})
                    pushed = True
            if not pushed:
                node.setEventStatus({GPI_INIT_EVENT: None})

    def undoAction(self):
        # Block re-entrant calls (processEvents() inside deserializeGraphData
        # can dispatch a second Ctrl+Z before the first restore completes).
        if self._undo_in_progress:
            return
        if self.aNodeIsProcessing():
            log.dialog("Cannot undo while nodes are processing.")
            return
        if not self._undo_stack:
            log.dialog("Nothing to undo.")
            return
        self._redo_stack.append(self.serializeGraphData())
        self._restoreSnapshot(self._undo_stack.pop())

    def redoAction(self):
        if self._undo_in_progress:
            return
        if self.aNodeIsProcessing():
            log.dialog("Cannot redo while nodes are processing.")
            return
        if not self._redo_stack:
            log.dialog("Nothing to redo.")
            return
        self._undo_stack.append(self.serializeGraphData())
        self._restoreSnapshot(self._redo_stack.pop())

    # ── Canvas Search ─────────────────────────────────────────────────────────

    def _initSearchBar(self):
        bar = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        self._search_edit = QtWidgets.QLineEdit()
        self._search_edit.setPlaceholderText('Search nodes…')
        self._search_edit.setMinimumWidth(180)
        self._search_edit.textChanged.connect(self._onSearchTextChanged)
        self._search_edit.installEventFilter(self)

        self._search_count_lbl = QtWidgets.QLabel()
        self._search_count_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self._search_count_lbl.setMinimumWidth(42)

        close_btn = QtWidgets.QPushButton('✕')
        close_btn.setFixedSize(22, 22)
        close_btn.clicked.connect(self._closeSearch)

        layout.addWidget(self._search_edit)
        layout.addWidget(self._search_count_lbl)
        layout.addWidget(close_btn)

        self._search_bar = bar
        self._search_bar.adjustSize()
        self._search_bar.hide()

        self._search_matches = []
        self._search_idx = 0

    def eventFilter(self, obj, event):
        if obj is self._search_edit:
            if event.type() == QtCore.QEvent.KeyPress:
                key = event.key()
                if key == QtCore.Qt.Key_Escape:
                    self._closeSearch()
                    return True
                if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                    mods = event.modifiers()
                    if mods & QtCore.Qt.ShiftModifier:
                        self._searchPrev()
                    else:
                        self._searchNext()
                    return True
        return super(GraphWidget, self).eventFilter(obj, event)

    def resizeEvent(self, event):
        super(GraphWidget, self).resizeEvent(event)
        self._repositionSearchBar()

    def _repositionSearchBar(self):
        if not hasattr(self, '_search_bar'):
            return
        margin = 8
        self._search_bar.adjustSize()
        sz = self._search_bar.sizeHint()
        self._search_bar.setGeometry(
            self.width() - sz.width() - margin,
            margin,
            sz.width(),
            sz.height(),
        )

    def _onSearchTextChanged(self, text):
        self.scene().unselectAllItems()
        nodes = self.getAllNodes()
        if not text.strip():
            self._search_matches = []
            self._search_idx = 0
            self._search_count_lbl.setText('')
            return
        q = text.lower()
        self._search_matches = [
            n for n in nodes
            if q in n.getNameFromItem().lower()
            or q in (n.getNodeLabel() or '').lower()
        ]
        self._search_idx = 0
        for n in self._search_matches:
            n.setSelected(True)
        total = len(self._search_matches)
        if self._search_matches:
            self.centerOn(self._search_matches[0])
            self._search_count_lbl.setText(f'1/{total}')
        else:
            self._search_count_lbl.setText('0/0')

    def _searchNext(self):
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx + 1) % len(self._search_matches)
        self.centerOn(self._search_matches[self._search_idx])
        total = len(self._search_matches)
        self._search_count_lbl.setText(f'{self._search_idx + 1}/{total}')

    def _searchPrev(self):
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx - 1) % len(self._search_matches)
        self.centerOn(self._search_matches[self._search_idx])
        total = len(self._search_matches)
        self._search_count_lbl.setText(f'{self._search_idx + 1}/{total}')

    def _closeSearch(self):
        self._search_bar.hide()
        self._search_matches = []
        self._search_idx = 0
        self.scene().unselectAllItems()
        self.setFocus()

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
            cpos = QtCore.QPoint(int(s['pos'][0] + rx), int(s['pos'][1] + ry))

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

            # final failure to resolve node — try a broken stub so the
            # canvas still loads and connections are preserved
            if node is None:
                node = self._create_broken_node(s, cpos)
                if node is None:
                    log.error('Node \''+stw(s['name']) + '\' failed to load, skipping.')
                    skipped_mods.append(str(s['name']))
                    continue
                log.warn('Node \''+stw(s['name']) + '\' has errors; loaded as stub. '
                         'Fix the source file and right-click → Reload.')

            new_nodes.append(node)
            node.setDisabledState(True)  # put in disabled state
            node.setID(s['id'])
            buf.append(node)

            # set other node attributes
            if 'walltime' in s:
                try:
                    node.appendWallTime(float(s['walltime']))
                except (TypeError, ValueError):
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
        # Build a name-lookup map for better diagnostics: id -> name
        _id_to_name = {n['id']: n['name'] for n in graph_settings['nodes']}

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
                        except (AttributeError, RuntimeError):
                            log.warn("Duplicate or connection" \
                                + " not found.  Skip connection.")
                    else:
                        src_name = _id_to_name.get(c['src']['nodeID'], '?')
                        dst_name = _id_to_name.get(c['dest']['nodeID'], '?')
                        missing = []
                        if not src:
                            missing.append("src '{}' (id={})".format(
                                src_name, c['src']['nodeID']))
                        if not dst:
                            missing.append("dst '{}' (id={})".format(
                                dst_name, c['dest']['nodeID']))
                        log.warn("Skipping connection {}:{} → {}:{} — "
                                 "node(s) not loaded: {}".format(
                            src_name, c['src']['portName'],
                            dst_name, c['dest']['portName'],
                            ', '.join(missing)))

        if reloadnode:
            for c in graph_settings.get('external_connections', []):
                src = self.getNodeByID(buf, c['src']['nodeID'])
                dst = self.getNodeByID(buf, c['dest']['nodeID'])
                if src and dst:
                    outport = src.getOutPort(c['src']['portName'])
                    inport = dst.getInPort(c['dest']['portName'])
                    if outport and inport and not inport.edges():
                        self.connectPorts(outport, inport)

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
                if not node._load_failed:
                    pushed = False
                    for inport in node.inportList:
                        uport = inport.getUpstreamPort()
                        if uport is not None and uport.data is not None:
                            # Targeted PORT_EVENT avoids fan-out and ensures
                            # reloaded nodes with cached upstream data run once.
                            node.setEventStatus({GPI_PORT_EVENT: inport.portTitle})
                            pushed = True
                    if not pushed:
                        node.setEventStatus({GPI_INIT_EVENT: None})
                    node.displayReloaded()
        else:
            # for importing networks
            for node in buf:
                node.setSelected(True)
                if not node._load_failed:
                    node.setEventStatus({GPI_INIT_EVENT: None})

        # reset macro IDs
        for node in macro_buf:
            if node.shouldCollapse():
                node.setCollapse(True)
            node.resetIDs()

        self.calcNodeHierarchy()

        # put nodes back in to idle (skip broken stubs — they stay disabled)
        for node in buf:
            if not node._load_failed:
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
            except IndexError:
                log.warn("Can't determine top node, skipping.")

    def getNodeByID(self, buf, nid):
        for item in buf:
            if isinstance(item, Node):
                if item.getID() == nid:
                    return item

    def _create_broken_node(self, s, pos):
        """Create a stub placeholder node when a module fails to load.

        The stub has matching port names (all typed PASS) so connections can
        be restored from the network file.  The node is flagged with
        _load_failed=True and painted with a red dashed-border + X overlay.
        """
        from .loader import _last_load_error

        node_name           = s.get('name', 'UnknownNode')
        ports_info          = list(s.get('ports', []))
        error_msg           = _last_load_error or 'Module failed to load'
        real_key            = s.get('key', node_name)
        orig_widget_settings = s.get('widget_settings', {'label': '', 'parms': []})

        def _initUI(self_node):
            for p in ports_info:
                title = p.get('porttitle', '')
                if not title:
                    continue
                if p.get('porttype') == InPortTYPE:
                    self_node.addInPort(title, 'PASS')
                else:
                    self_node.addOutPort(title, 'PASS')
            return 0

        def _compute(self_node):
            return 0

        def _getSettings(self_node):
            # Return the original widget settings so they are preserved when
            # the stub is saved to the copy-buffer and replayed into the real
            # node on right-click → Reload.
            return dict(orig_widget_settings)

        StubClass = type('ExternalNode', (gpi.NodeAPI,), {
            'initUI': _initUI,
            'compute': _compute,
            'getSettings': _getSettings,
        })

        stub_mod = _types.ModuleType(node_name)
        stub_mod.ExternalNode = StubClass

        # Build a minimal catalog item that won't reload from the broken file.
        # Use the REAL library key so that on reload newNode_byKey() finds the
        # (now-fixed) library entry directly instead of falling back to closest-match.
        item = object.__new__(_BrokenNodeCatalogItem)
        item.fullpath      = real_key
        item.editable_path = None
        item.name          = node_name
        item.second        = ''
        item.third         = ''
        item._lib_path     = ''
        item.path          = ''
        item.ext           = ['.py']
        item.pkg_root      = None
        item.isNodeFile    = True
        item.mod           = stub_mod
        item.widgetNames   = []
        item._id           = real_key
        item.thrd_sec      = ''

        try:
            node = self.newNode_byNodeCatalogItem(item, pos)
            if node is not None:
                node.setLoadFailed(error_msg)
            return node
        except Exception:
            log.warn('_create_broken_node() failed: ' + traceback.format_exc())
            return None

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
        """Subtract average position from all node positions for normalization."""
        ax, ay = self.calcAvgPosFromSettings(graph_settings)
        for s in graph_settings['nodes']:
            if 'connections' in s.keys(): del s['connections']
        
        # Use targeted shallow copy instead of deep copy for performance.
        # This copies the outer structure while sharing references to modifiable dicts.
        # The position modifications below will work on the copied structure.
        newgraphsettings = {
            'nodes': [dict(n) for n in graph_settings.get('nodes', [])],
            'macroNodes': [dict(m) for m in graph_settings.get('macroNodes', [])]
        }
        
        # Deep copy nested settings ONLY if they exist (macroNodes contain nested dicts)
        for i, mnode in enumerate(newgraphsettings['macroNodes']):
            if 'src_settings' in mnode:
                newgraphsettings['macroNodes'][i]['src_settings'] = copy.deepcopy(mnode['src_settings'])
            if 'sink_settings' in mnode:
                newgraphsettings['macroNodes'][i]['sink_settings'] = copy.deepcopy(mnode['sink_settings'])
            if 'face_settings' in mnode:
                newgraphsettings['macroNodes'][i]['face_settings'] = copy.deepcopy(mnode['face_settings'])

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

    def serializeGraphData(self, selectedOnly=False, minusAvgPos=False,
                           preserve_external_connections=False):
        # Handles only nodes and macro-nodes.  The 'selectedOnly' option is
        # for copy/paste operation.

        graph_settings = {}
        graph_settings['nodes'] = []
        graph_settings['macroNodes'] = []
        graph_settings['external_connections'] = []

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
            # Shallow copy of node settings dict is sufficient since we immediately
            # replace the connections field. Avoids expensive deep recursion.
            node_copy = dict(node.getSettings())
            node_copy['connections'] = node.getInputConnections()
            graph_settings['nodes'].append(node_copy)

        if selectedOnly:
            # Drop connections to nodes that weren't copied (e.g. an upstream
            # node feeding a copied node but not itself selected). Otherwise
            # paste tries to resolve them and logs spurious "not loaded"
            # warnings for a connection that was never meant to be copied.
            copied_ids = {n['id'] for n in graph_settings['nodes']}
            if preserve_external_connections:
                seen_connections = set()
                for n in graph_settings['nodes']:
                    for port in n.get('ports', []):
                        for c in port['connections']:
                            connection_key = (
                                c['src']['nodeID'], c['src']['portName'],
                                c['dest']['nodeID'], c['dest']['portName'])
                            if (connection_key[0] not in copied_ids or
                                    connection_key[2] not in copied_ids):
                                if connection_key not in seen_connections:
                                    graph_settings['external_connections'].append(c)
                                    seen_connections.add(connection_key)
            for n in graph_settings['nodes']:
                for port in n.get('ports', []):
                    port['connections'] = [
                        c for c in port['connections']
                        if c['src']['nodeID'] in copied_ids and
                        c['dest']['nodeID'] in copied_ids
                    ]

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

        # Auto-organize after load so the topology layout is applied immediately.
        QtCore.QTimer.singleShot(100, self._autoOrganizeAll)


