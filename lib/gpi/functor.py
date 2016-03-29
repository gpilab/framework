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


import gc
import time
import numpy as np # for 32bit-Pipe hack
import traceback
import multiprocessing
ctx = multiprocessing.get_context('forkserver')
# import logging, pickle, pickletools
# logger = ctx.log_to_stderr()
# logger.setLevel(logging.INFO)

import gpi
from gpi import QtCore
from .dataproxy import DataProxy, ProxyType
from .defines import GPI_PROCESS, GPI_THREAD, GPI_APPLOOP
from .logger import manager
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)

def ExecRunnable(runnable):
    tp = QtCore.QThreadPool.globalInstance()
    #print 'active threads: ', tp.activeThreadCount()
    #print 'expiry timeout: ', tp.expiryTimeout()
    #print 'maxThreadCount: ', tp.maxThreadCount()
    tp.start(runnable)

class GPIRunnable(QtCore.QRunnable):
    def __init__(self, func):
        super(GPIRunnable, self).__init__()
        self.run = func
        self.setAutoDelete(True)

# A template API for each execution type.
class GPIFunctor(QtCore.QObject):
    finished = gpi.Signal()
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

        # For Windows just make them all apploops for now to be safe
        self._execType = self._node.execType()
        if Specs.inWindows() and (self._execType == GPI_PROCESS):
        #if (self._execType == GPI_PROCESS):
            log.info("init(): <<< WINDOWS Detected >>> Forcing GPI_PROCESS -> GPI_THREAD")
            self._execType = GPI_THREAD
            #self._execType = GPI_APPLOOP

        self._label = node.getLabel()
        self._isTerminated = False
        self._compute_start = 0

        self._manager = None
        self._proxy = None
        self._proc = None
        if self._execType == GPI_PROCESS:
            log.debug("init(): set as GPI_PROCESS: "+str(self._title))
            self._manager = multiprocessing.Manager()
            self._proxy = self._manager.list()
            self._proc = PTask(self._func, self._title, self._label, self._proxy)

            # apply data in a thread to make the GUI more responsive
            self._applyData_thread = GPIRunnable(self.applyQueuedData_setData)

        elif self._execType == GPI_THREAD:
            log.debug("init(): set as GPI_THREAD: "+str(self._title))
            self._proc = TTask(self._func, self._title, self._label, self._proxy)
            self._applyData_thread = GPIRunnable(self.setData_basic)

        else:  # default to GPI_APPLOOP
            log.debug("init(): set as GPI_APPLOOP: "+str(self._title))
            self._proc = ATask(self._func, self._title, self._label, self._proxy)
            self._applyData_thread = GPIRunnable(self.setData_basic)

        self._proc.finished.connect(self.computeFinished)
        self._proc.terminated.connect(self.computeTerminated)

    def execType(self):
        return self._execType

    def terminate(self):
        self._isTerminated = True
        self.cleanup()
        self._proc.terminate()
        # self.wait() # so that something is waiting
        self.computeTerminated()

    def cleanup(self):
        # make sure the proxy manager for processes is shutdown.
        if self._manager:
            self._manager.shutdown()

        # try to minimize leftover memory from the segmented array transfers
        # force cleanup of mmap
        #if self._segmentedDataProxy:
        gc.collect()

    def curTime(self):
        return time.time() - self._compute_start

    def start(self):
        self._compute_start = time.time()

        # temporarily trick all widget calls to use GPI_APPLOOP for validate()
        tmp_exec = self._execType
        self._execType = GPI_APPLOOP
        self._validate_retcode = self._validate()
        self._execType = tmp_exec

        # send validate() return code thru same channels
        if self._validate_retcode is None:
            self._validate_retcode = 0

        if self._validate_retcode == 0:
            self._node.updateOutportPosition()
        elif self._validate_retcode < 0:
            log.error("start(): validate() failed.")
            self._node.appendWallTime(time.time() - self._compute_start)
            self.finished.emit()
            return
        elif self._validate_retcode > 0:
            log.warn("start(): validate() finished with a warning.")

        if self._execType == GPI_PROCESS:
            # keep objects on death-row from being copied into processes
            # before they've finally terminated. -otherwise they'll try
            # and terminate within child process and cause a fork error.
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

    # GPI_PROCESS support
    def addToQueue(self, item):
        # add internal calls (port, widget, retcode...)
        # to a queue that is processed after compute()
        self._proc._proxy.append(item)

    def computeTerminated(self):
        self.terminated.emit()

    def computeFinished(self):
        # transfer all setData() calls to a thread
        log.debug("applyQueuedData(): run _applyData_thread")
        ExecRunnable(self._applyData_thread)

        if self._execType == GPI_PROCESS:
            self.applyQueuedData()
        else:
            self._retcode = self._proc._retcode
            if self._retcode == 0:
                self._retcode = self._validate_retcode
            self.finalMatter()

    def applyQueuedData_Failed(self):
        log.critical("applyQueuedData_Failed():Node \'"+str(self._title)+"\'")
        self.finished.emit()

    def finalMatter(self):
        log.debug("computeFinished():Node \'"+str(self._title)+"\': compute time:"+str(time.time() - self._compute_start)+" sec.")
        self._node.appendWallTime(time.time() - self._compute_start)
        self.finished.emit()

    def setData_basic(self):
        outPorts = self._node.getOutPorts()
        for port in outPorts:
            if outPorts[port]['changed']:
                self._node.setData(port, outPorts[port]['data'])

    def applyQueuedData_setData(self):
        for o in self._proxy:
            if o[0] == 'setData':
                try:
                    log.debug("applyQueuedData_setData(): apply object " +
                              str(o[0]) + ', ' + str(o[1]))
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
                    log.error("applyQueuedData() failed. " +
                              str(traceback.format_exc()))
                    #raise
                    self._retcode = -1
                    self._setData_finished.emit()

        # Assemble Segmented Data
        if self._segmentedDataProxy:
            log.warn("Using segmented data proxy...")
            # group all segmented types
            oportData = [ o for o in self._proxy if (o[0] == 'setData') and (type(o[2]) is DataProxy) ]
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

        self._setData_finished.emit()

    def applyQueuedData(self):
        # Replay all external compute() events after execution.
        # This ensures that the target is not being used by another set method.
        self._ap_st_time = time.time()
        if self._isTerminated:
            return
        log.debug("applyQueuedData(): Sending data to main loop...")
        if len(self._proxy) == 0:
            log.debug("applyQueuedData(): no data in output queue. Terminated.")
            self.computeTerminated()
            return

        self._segmentedDataProxy = False
        for o in self._proxy:
            try:
                log.debug("applyQueuedData(): apply object "+str(o[0])+', '+str(o[1]) )
                if o[0] == 'retcode':
                    self._retcode = o[1]
                    if self._retcode == 0:
                        self._retcode = self._validate_retcode # validate is stored locally
                if o[0] == 'modifyWdg':
                    self._node.modifyWdg(o[1], o[2])
                if o[0] == 'setReQueue':
                    self._node.setReQueue(o[1])
                # move to thread
                #if o[0] == 'setData':
                #    # flag any NPY array for threaded xfer
                #    if type(o[2]) is dict:
                #        if o[2].has_key('951413'):
                #            self._segmentedDataProxy = True
                #            continue
                #    self._node.setData(o[1], o[2])
            except:
                log.error("applyQueuedData() failed. "+str(traceback.format_exc()))
                #raise
                self._retcode = -1

    def applyQueuedData_finalMatter(self):

        if self._retcode == -1:
            self.applyQueuedData_Failed()

        elapsed = (time.time() - self._ap_st_time)
        log.info("applyQueuedData(): time (total queue): "+str(elapsed)+" sec")

        # shutdown the proxy manager
        self.cleanup()

        self.applyQueuedData_finished.emit()

# The process-type has to be checked periodically to see if its alive,
# from the spawning process.
class PTask(QtCore.QObject):
    finished = gpi.Signal()
    terminated = gpi.Signal()

    def __init__(self, func, title, label, proxy):
        QtCore.QObject.__init__(self)
        self._title = title
        self._label = label
        self._proxy = proxy
        self._cnt = 0

        # pickletools.dis(pickle.dumps(func))
        self._process = ctx.Process(target=func, args=(title, label, proxy))

        # Since we don't know when the process finishes
        # probe at regular intervals.
        # -it would be nicer to have the process check-in with the GPI
        #  main proc when its done.
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.checkProcess)
        self._timer.start(10)  # 10msec update

    def start(self):
        self._process.start()

    # def run(self):
    #     # This try/except is only good for catching compute() exceptions
    #     # not run() terminations.
    #     try:
    #         self._proxy.append(['retcode', self._func()])
    #     except:
    #         log.error('PROCESS: \''+str(self._title)+'\':\''+str(self._label)+'\' compute() failed.\n'+str(traceback.format_exc()))
    #         #raise
    #         self._proxy.append(['retcode', -1])

    def terminate(self):
        self._timer.stop()
        self._process.terminate()
        # super().terminate()

    def wait(self):
        self._process.join()
        # self.join()

    def isRunning(self):
        return self._process.is_alive()
        # return self.is_alive()

    def retcodeExists(self):
        for o in self._proxy:
            if o[0] == 'retcode':
                return True
        return False

    def checkProcess(self):
        if self.isRunning():
            return
        # else if its not alive:
        self._timer.stop()
        if self.retcodeExists():
            # we assume its termination was deliberate.
            self.finished.emit()
        else:
            self.terminated.emit()

# The thread-type emits a signal when its finished:
# gpi.Signal.finished()
# gpi.Signal.terminated()


class TTask(QtCore.QThread):
    def __init__(self, func, title, label, proxy):
        super(TTask, self).__init__()
        self._func = func
        self._title = title
        self._label = label
        self._proxy = proxy
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
            #raise
            self._retcode = -1

# The apploop-type blocks until finished, obviating the need for signals
# or timer checks


class ATask(QtCore.QObject):
    finished = gpi.Signal()
    terminated = gpi.Signal()

    def __init__(self, func, title, label, proxy):
        super(ATask, self).__init__()
        self._func = func
        self._title = title
        self._label = label
        self._proxy = proxy
        self._cnt = 0

    def run(self):
        # This try/except is only good for catching compute() exceptions
        # not run() terminations.
        try:
            self._retcode = self._func()
        except:
            log.error('APPLOOP: \''+str(self._title)+'\':\''+str(self._label)+'\' compute() failed.\n'+str(traceback.format_exc()))
            #raise
            self._retcode = -1

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
