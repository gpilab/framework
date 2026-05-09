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


import gc
import time
import numpy as np # for 32bit-Pipe hack
import traceback
import multiprocessing
import platform

import gpi
from gpi import QtCore
from .dataproxy import DataProxy, ProxyType
from .defines import GPI_PROCESS, GPI_THREAD, GPI_APPLOOP
from .logger import manager
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)

# Python 3.8 - need to explicitly declare fork for MacOS
if platform.system() == 'Windows':
    multiprocessing_context = multiprocessing.get_context('spawn')
else:
    multiprocessing_context = multiprocessing.get_context('fork')

class ReturnCodes(object):

    # Return codes from the functor have specific meaning to the node internals.
    InitUIError = 2
    ValidateError = 1
    Success = 0
    ComputeError = -1

    def isComputeError(self, ret):
        return ret == self.ComputeError
    def isValidateError(self, ret):
        return ret == self.ValidateError
    def isInitUIError(self, ret):
        return ret == self.InitUIError

    # Return codes from the nodeAPI (i.e. compute(), validate() and initUI())
    # are either success or failure for each function.
    def isSuccess(self, ret):
        return (ret is None) or (ret == 0)
    def isError(self, ret):
        return (ret is not None) and (ret != 0)

Return = ReturnCodes() # make a global copy

def ExecRunnable(runnable):
    tp = QtCore.QThreadPool.globalInstance()
    tp.start(runnable)

class GPIRunnable(QtCore.QRunnable):
    def __init__(self, func):
        super(GPIRunnable, self).__init__()
        self.run = func
        self.setAutoDelete(True)


class _ProcWatcher(QtCore.QThread):
    """Blocks on process.join() in a background thread, then signals completion.

    This replaces the QTimer-based polling in the old PTask, giving instant
    notification (within OS scheduling) instead of up to 10 ms of timer lag.
    """
    _proc_exited = gpi.Signal()

    def __init__(self, proc, parent=None):
        super(_ProcWatcher, self).__init__(parent)
        self._proc = proc

    def run(self):
        self._proc.join()
        self._proc_exited.emit()


class GPIFunctor(QtCore.QObject):
    '''A common parent API for each execution type (i.e. ATask, PTask, TTask).
    Handles the data communications to and from each task type. '''

    finished = gpi.Signal(int)
    terminated = gpi.Signal()
    applyQueuedData_finished = gpi.Signal()
    _setData_finished = gpi.Signal()

    def __init__(self, node, parent=None):
        super(GPIFunctor, self).__init__(parent)
        self._node = node
        self._title = node.name
        self._func = node.getModuleCompute()
        self._validate = node.getModuleValidate()
        self._retcode = None
        self._validate_retcode = None

        # for applying data when a GPI_PROCESS is finished
        # this is done in a thread to keep the GUI responsive
        self._applyData_thread = None
        self._setData_finished.connect(self.applyQueuedData_finalMatter)
        self.applyQueuedData_finished.connect(self.finalMatter)
        self._ap_st_time = 0

        # flag for segmented types that need reconstitution on this side
        self._segmentedDataProxy = False

        # GPI_PROCESS is not available on Windows because NodeAPI holds QObject
        # references that cannot be pickled through the spawn IPC channel.
        self._execType = node._nodeIF.execType()
        if Specs.inWindows() and (self._execType == GPI_PROCESS):
            log.info("init(): <<< WINDOWS Detected >>> Forcing GPI_PROCESS -> GPI_THREAD")
            self._execType = GPI_THREAD

        self._label = node._nodeIF.getLabel()
        self._isTerminated = False
        self._compute_start = 0

        # Filled once after the worker process exits; shared by applyQueuedData
        # and applyQueuedData_setData so we only drain the Queue once.
        self._drained_items = []

        self._queue = None
        self._proc = None
        if self._execType == GPI_PROCESS:
            log.debug("init(): set as GPI_PROCESS: "+str(self._title))
            self._queue = multiprocessing_context.Queue()
            self._proc = PTask(self._func, self._title, self._label, self._queue)

            # apply data in a thread to make the GUI more responsive
            self._applyData_thread = GPIRunnable(self.applyQueuedData_setData)

        elif self._execType == GPI_THREAD:
            log.debug("init(): set as GPI_THREAD: "+str(self._title))
            self._proc = TTask(self._func, self._title, self._label)

        else:  # default to GPI_APPLOOP
            log.debug("init(): set as GPI_APPLOOP: "+str(self._title))
            self._proc = ATask(self._func, self._title, self._label)

        self._proc.finished.connect(self.computeFinished)


    def execType(self):
        return self._execType

    def terminate(self):
        self._isTerminated = True
        self.cleanup()
        self._proc.terminate()
        self.computeTerminated()

    def cleanup(self):
        if self._queue is not None:
            try:
                self._queue.close()
                self._queue.join_thread()
            except Exception:
                pass

        gc.collect()

    def curTime(self):
        return time.time() - self._compute_start

    def start(self):
        self._compute_start = time.time()

        # VALIDATE
        # temporarily trick all widget calls to use GPI_APPLOOP for validate()
        tmp_exec = self._execType
        self._execType = GPI_APPLOOP
        try:
            self._validate_retcode = self._validate()
        except:
            self._validate_retcode = 1 # validate error
        self._execType = tmp_exec

        # send validate() return code thru same channels
        if self._validate_retcode != 0 and self._validate_retcode is not None:
            self._node.appendWallTime(time.time() - self._compute_start)
            self.finished.emit(1) # validate error
            return

        # COMPUTE
        if self._execType == GPI_PROCESS:
            log.debug("start(): buffer process parms")
            self._node._nodeIF.bufferParmSettings()

            # keep objects on death-row from being copied into processes
            # before they've finally terminated.
            log.debug('start(): garbage collect before spawning GPI_PROCESS')
            gc.collect()

        log.debug("start(): call task.start()")
        self._proc.start()

    def wait(self):
        self._proc.wait()

    def isRunning(self):
        return self._proc.isRunning()

    def returnCode(self):
        return self._retcode

    # GPI_PROCESS support — called from the worker process via nodeAPI
    def addToQueue(self, item):
        self._queue.put(item)

    def _drain_queue(self):
        """Drain the IPC queue after the worker process has exited.

        Reads until the 'retcode' sentinel is found. Because the worker has
        already been joined, all items are already in the pipe buffer and
        every get() returns immediately.
        """
        items = []
        try:
            while True:
                item = self._queue.get(timeout=10.0)
                items.append(item)
                if item[0] == 'retcode':
                    break
        except Exception as e:
            log.error("_drain_queue(): failed: " + str(e))
        self._drained_items = items

    def computeTerminated(self):
        self.terminated.emit()

    def computeFinished(self):
        if self._execType == GPI_PROCESS:
            self._drain_queue()
            self.applyQueuedData()

        else:
            self._retcode = 0 # success
            if Return.isError(self._proc._retcode):
                self._retcode = Return.ComputeError
            self.finalMatter()

    def finalMatter(self):
        log.info("computeFinished():Node \'"+str(self._title)+"\': compute time:"+str(time.time() - self._compute_start)+" sec.")
        self._node.appendWallTime(time.time() - self._compute_start)
        self.finished.emit(self._retcode) # success

    def applyQueuedData_setData(self):

        for o in self._drained_items:
            try:
                log.debug("applyQueuedData_setData(): apply object "+str(o[0])+', '+str(o[1]))
                if o[0] == 'setData':
                    # DataProxy is used for complex data types like numpy
                    if type(o[2]) is DataProxy:

                        # segmented types must be gathered before reassembly
                        if o[2].isSegmented():
                            log.debug("seg proxy is True")
                            self._segmentedDataProxy = True
                        else:
                            log.debug("o[2].getData()")
                            self._node.setData(o[1], o[2].getData())

                    # all other simple types get set directly
                    else:
                        log.debug("direct setData()")
                        self._node.setData(o[1], o[2])
            except:
                log.error("applyQueuedData() failed. "+str(traceback.format_exc()))
                self._retcode = Return.ComputeError
                self._setData_finished.emit()

        # Assemble Segmented Data
        if self._segmentedDataProxy:
            log.warn("Using segmented data proxy...")
            # group all segmented types
            oportData = [ o for o in self._drained_items if (o[0] == 'setData') and (type(o[2]) is DataProxy) ]
            # take only those that are segmented
            oportData = [ o for o in oportData if o[2].isSegmented() ]
            # consolidate all outports with large data
            largeports = set([ o[1] for o in oportData ])

            for port in largeports:
                log.info("applyQueuedData(): ------ APPENDING SEGMENTED PROXY OBJECTS")

                # gather port segs
                curport = [o for o in oportData if o[1] == port]

                # gather all DataProxy segs
                segs = [ o[2] for o in curport ]
                buf = DataProxy().getDataFromSegments(segs)

                # if the pieces fail to assemble move on
                if buf is None:
                    log.warn("applyQueuedData(): segmented proxy object failed to assemble, skipping...")
                    continue

                self._node.setData(port, buf)

        # run self.applyQueuedData_finalMatter()
        self._setData_finished.emit()

    def applyQueuedData(self):
        # Replay all external compute() events after execution.
        self._ap_st_time = time.time()
        if self._isTerminated:
            return
        log.debug("applyQueuedData(): processing result queue...")
        if len(self._drained_items) == 0:
            log.debug("applyQueuedData(): no data in output queue. Terminated.")
            self.computeTerminated()
            return

        self._segmentedDataProxy = False
        for o in self._drained_items:
            try:
                log.debug("applyQueuedData(): apply object "+str(o[0])+', '+str(o[1]) )
                if o[0] == 'retcode':
                    self._retcode = o[1]
                    if Return.isError(self._retcode):
                        self._retcode = Return.ComputeError
                    else:
                        self._retcode = 0 # squash Nones
                if o[0] == 'modifyWdg':
                    self._node.modifyWdg(o[1], o[2])
                if o[0] == 'setReQueue':
                    self._node.setReQueue(o[1])
            except:
                log.error("applyQueuedData() failed. "+str(traceback.format_exc()))
                self._retcode = Return.ComputeError

        # transfer all setData() calls to a thread
        log.debug("applyQueuedData(): run _applyData_thread")
        ExecRunnable(self._applyData_thread)

    def applyQueuedData_finalMatter(self):

        if Return.isComputeError(self._retcode):
            self.finished.emit(self._retcode)

        elapsed = (time.time() - self._ap_st_time)
        log.info("applyQueuedData(): time (total queue): "+str(elapsed)+" sec")

        # close the queue
        self.cleanup()

        # start self.finalMatter
        self.applyQueuedData_finished.emit()


class PTask(multiprocessing_context.Process, QtCore.QObject):
    '''A forked process node task. A Queue is used to communicate results back.

    Completion is detected by a _ProcWatcher QThread that blocks on join(),
    giving instant notification instead of the old QTimer-based polling.
    '''

    finished = gpi.Signal()
    terminated = gpi.Signal()

    def __init__(self, func, title, label, queue):
        multiprocessing_context.Process.__init__(self)
        QtCore.QObject.__init__(self)
        self._func = func
        self._title = title
        self._label = label
        self._queue = queue

        # Set by the worker process in its finally block; readable by the parent
        # after join() returns to distinguish normal exit from a crash/SIGKILL.
        self._completed = multiprocessing_context.Event()

        self._watcher = _ProcWatcher(self)
        self._watcher._proc_exited.connect(self._on_process_exited)

    def run(self):
        try:
            self._queue.put(['retcode', self._func()])
        except:
            log.error('PROCESS: \''+str(self._title)+'\':\''+str(self._label)+'\' compute() failed.\n'+str(traceback.format_exc()))
            self._queue.put(['retcode', Return.ComputeError])
        finally:
            self._completed.set()

    def start(self):
        multiprocessing_context.Process.start(self)
        self._watcher.start()

    def _on_process_exited(self):
        if self._completed.is_set():
            self.finished.emit()
        else:
            self.terminated.emit()

    def terminate(self):
        self._watcher.quit()
        multiprocessing_context.Process.terminate(self)

    def wait(self):
        self.join()

    def isRunning(self):
        return self.is_alive()


class TTask(QtCore.QThread):
    '''A QThread based node runner.  Data is communicated directly.

        NOTE: The thread-type emits a signal when its finished:
            gpi.Signal.finished()
            gpi.Signal.terminated()
    '''

    def __init__(self, func, title, label, proxy=None):
        super(TTask, self).__init__()
        self._func = func
        self._title = title
        self._label = label
        self._retcode = None

        # allow thread to terminate immediately
        # NOTE: doesn't seem to work
        self.setTerminationEnabled(True)

    def terminate(self):
        # Threads don't die as well as processes right now,
        # so just let them run off in the background.
        log.warn("WARNING: Terminated QThread-Node is backgrounded as a zombie.")
        self.exit()  # terminate when finished

    def run(self):
        # This try/except is only good for catching compute() exceptions
        # not run() terminations.
        try:
            self._retcode = self._func()
            log.info("TTask _func() finished")
        except:
            log.error('THREAD: \''+str(self._title)+'\':\''+str(self._label)+'\' compute() failed.\n'+str(traceback.format_exc()))
            self._retcode = Return.ComputeError


class ATask(QtCore.QObject):
    '''App-Loop or Main-Loop executed task.  This will block GUI updates.  Data
    is communicated directly.

        NOTE: The apploop-type blocks until finished, obviating the need for
        signals or timer checks
    '''

    finished = gpi.Signal()
    terminated = gpi.Signal()

    def __init__(self, func, title, label, proxy=None):
        super(ATask, self).__init__()
        self._func = func
        self._title = title
        self._label = label
        self._retcode = None
        self._cnt = 0

    def run(self):
        # This try/except is only good for catching compute() exceptions
        # not run() terminations.
        try:
            self._retcode = self._func()
        except:
            log.error('APPLOOP: \''+str(self._title)+'\':\''+str(self._label)+'\' compute() failed.\n'+str(traceback.format_exc()))
            self._retcode = Return.ComputeError

    def terminate(self):
        pass  # can't happen b/c blocking mainloop

    def wait(self):
        pass  # can't happen b/c blocking mainloop

    def isRunning(self):
        pass  # can't happen b/c blocking mainloop

    def quit(self):
        pass

    def start(self):
        self.run()
        self.finished.emit()
