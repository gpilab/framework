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


# gpi
import gpi
from gpi import QtCore
from .logger import manager
from .node import Node

# start logger for this module
log = manager.getLogger(__name__)


class GPINodeQueue(QtCore.QObject):
    '''The list of nodes to process based on UI and hierarchy changes.
    '''

    finished = gpi.Signal()

    def __init__(self, parent=None):
        super(GPINodeQueue, self).__init__(parent)
        self._queue = []
        self._paused = False
        self._last_node_started = '-init-str-'

    def __str__(self):
        # stringify the status of the queue
        msg =  "GPINodeQueue object:\n"
        msg += "\tis paused: "+str(self.isPaused())+"\n"
        msg += "\tis empty:  "+str(self.isEmpty())+"\n"
        msg += "\tqueue len: "+str(self.getQueueLen())+"\n"
        msg += "\tlast node:  "+str(self._last_node_started)+"\n"
        return msg

    def setPause(self, val):
        self._paused = val

    def isPaused(self):
        return self._paused

    def isEmpty(self):
        if len(self._queue) > 0:
            return False
        return True

    def put(self, node):
        if isinstance(node, Node):
            self._queue.append(node)

    def hasNode(self, node):
        return any(n is node for n in self._queue)

    def getQueueLen(self):
        return len(self._queue)

    def resetQueue(self):
        self._queue = []

    def setQueue(self, nlist):
        self._queue = nlist

    def removeNode(self, node):
        # removes the first instance of given 'node'
        if node in self._queue:
            ind = self._queue.index(node)
            self._queue.pop(ind)
            log.debug("removeNode(): Node(" + node.name + \
                "): Removed node from queue.")
            return True  # SUCCESS
        else:
            log.debug("removeNode(): Node(" + node.name + \
                "): This node was not found in the queue.")
            return False  # FAILURE

    def _isBlockedByAncestor(self, node):
        """True if any transitive upstream ancestor is still running or is
        still waiting to run.

        Checking only the direct parents is not enough: a parent can be idle
        with no pending event simply because its *own* upstream hasn't
        produced data yet (e.g. Collapse sitting idle while CoilCompression is
        still computing). Starting this node then feeds it stale data from the
        previous run. Cyclic ports are skipped so feedback loops can't
        deadlock the traversal.
        """
        seen = {id(node)}
        stack = [node]
        while stack:
            cur = stack.pop()
            for p in cur.inportList:
                if p.allowsCyclicConn():
                    continue
                uport = p.getUpstreamPort()
                if uport is None:
                    continue
                un = uport.getNode()
                if id(un) in seen:
                    continue
                seen.add(id(un))
                if un.isProcessingEvent() or un.isReady():
                    return True
                stack.append(un)
        return False

    def startNextAvailableNode(self):
        """Start the first queued node whose ancestors are all finished.

        Scans all positions (not just the front) so that independent branches
        can start concurrently while a shared upstream is still running.

        Returns:
            'paused'   — queue is paused
            'started'  — one node was started; caller should call again
            'waiting'  — nodes remain but all have unfinished ancestors
            'finished' — queue is empty (some nodes may still be running)
        """
        if self.isPaused():
            log.debug("startNextAvailableNode(): blocking for pause.")
            return 'paused'

        if not self._queue:
            return 'finished'

        i = 0
        while i < len(self._queue):
            node = self._queue[i]

            if not node.isReady():
                # Stale entry (node was disabled or event was cleared) — discard.
                self._queue.pop(i)
                continue

            if node.isProcessingEvent():
                # Node is already running (e.g. received a new port event from
                # a concurrent upstream while its previous run is still in
                # flight). Keep the event pending and skip for now.
                i += 1
                continue

            if not self._isBlockedByAncestor(node):
                self._queue.pop(i)
                self._last_node_started = node.getName()
                node.setEventStatus(None)
                log.debug("startNextAvailableNode(): node: " + node.getName())
                node.graph._nodes_running += 1
                node.start()
                return 'started'

            i += 1

        if not self._queue:
            return 'finished'
        return 'waiting'

    def startNextNode(self):
        """Serial fallback — kept for compatibility. Prefer startNextAvailableNode."""
        if self.isPaused():
            log.debug("startNextNode(): blocking for pause.")
            return 'paused'

        # find next node in queue
        if len(self._queue) > 0:
            while not self._queue[0].isReady():
                self._queue.pop(0)
                if len(self._queue) == 0:
                    break

        # if queue is done then finalize
        if len(self._queue) == 0:
            log.debug("startNextNode(): node queue empty, finished.")
            self.finished.emit()
            return 'finished'

        # run next node
        node = self._queue.pop(0)
        self._last_node_started = node.getName()
        if node.hasEventPending():
            node.setEventStatus(None)
            log.debug("startNextNode(): node: "+node.getName())
            node.start()
            return 'started'
