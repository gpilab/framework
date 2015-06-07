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

import gpi
from gpi import QtCore
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

        # for applying data when a GPI_PROCESS is finished
        # this is done in a thread to keep the GUI responsive
        self._applyData_thread = None
        self._setData_finished.connect(self.applyQueuedData_finalMatter)
        self.applyQueuedData_finished.connect(self.finalMatter)
        self._ap_st_time = 0

        self._largeNPYpresent = False

        # For Windows just make them all apploops for now to be safe
        self._execType = node._nodeIF.execType()
        if Specs.inWindows() and (self._execType == GPI_PROCESS):
        #if (self._execType == GPI_PROCESS):
            log.info("init(): <<< WINDOWS Detected >>> Forcing GPI_PROCESS -> GPI_THREAD")
            self._execType = GPI_THREAD
            #self._execType = GPI_APPLOOP

        self._label = node._nodeIF.getLabel()
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

        else:  # default to GPI_APPLOOP
            log.debug("init(): set as GPI_APPLOOP: "+str(self._title))
            self._proc = ATask(self._func, self._title, self._label, self._proxy)

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
        if self._largeNPYpresent:
            gc.collect()

    def curTime(self):
        return time.time() - self._compute_start

    def start(self):
        self._compute_start = time.time()

        # temporarily trick all widget calls to use GPI_APPLOOP for validate()
        tmp_exec = self._execType
        self._execType = GPI_APPLOOP
        self._retcode = self._validate()
        self._execType = tmp_exec

        # send validate() return code thru same channels
        if self._retcode:
            log.error("start(): validate() failed.")
            self._node.appendWallTime(time.time() - self._compute_start)
            self.finished.emit()
            return

        if self._execType == GPI_PROCESS:
            log.debug("start(): buffer process parms")
            self._node._nodeIF.bufferParmSettings()

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
        if self._execType == GPI_PROCESS:
            self.applyQueuedData()

        else:
            self._retcode = self._proc._retcode
            self.finalMatter()

    def applyQueuedData_Failed(self):
        log.critical("applyQueuedData_Failed():Node \'"+str(self._title)+"\'")
        self.finished.emit()

    def finalMatter(self):
        log.debug("computeFinished():Node \'"+str(self._title)+"\': compute time:"+str(time.time() - self._compute_start)+" sec.")
        self._node.appendWallTime(time.time() - self._compute_start)
        self.finished.emit()

    def applyQueuedData_setData(self):

        for o in self._proxy:
            try:
                #if o[0] == 'retcode':
                #    self._retcode = o[1]
                #if o[0] == 'modifyWdg':
                #    self._node.modifyWdg(o[1], o[2])
                #if o[0] == 'setReQueue':
                #    self._node.setReQueue(o[1])
                if o[0] == 'setData':
                    # flag large NPY arrays for reconstruction
                    if type(o[2]) is dict:
                        if o[2].has_key('951413'):
                            #self._largeNPYpresent = True
                            #shd = np.ctypeslib.as_array(o[2]['seg'])
                            #shd = np.frombuffer(o[2]['prox'], dtype=np.float64)
                            shd = np.memmap(o[2]['shdf'], dtype='float64', mode='r', shape=tuple(o[2]['shape']))
                            print 'fname ', o[2]['shdf']
                            print 'shd ', shd
                            print shd.shape
                            #shd.shape = o[2]['shape']
                            self._node.setData(o[1], shd)
                            continue
                    self._node.setData(o[1], o[2])
            except:
                log.error("applyQueuedData() failed. "+str(traceback.format_exc()))
                #raise
                self._retcode = -1
                self._setData_finished.emit()


        #if self._largeNPYpresent:
        if False:
            # consolidate all outport data of type dict
            oportData = [ o for o in self._proxy if (o[0] == 'setData') and (type(o[2]) is dict) ]
            # take only dictionaries with the special key
            oportData = [ o for o in oportData if o[2].has_key('951413') ]
            # consolidate all outports with large NPY arrays
            largeports = set([ o[1] for o in oportData ])

            # for each unique port title, consolidate the NPY segments
            for port in largeports:
                log.info("applyQueuedData(): ------ APPENDING LARGE NPY ARRAY SEGMENTS")

                try:
                    # gather port segs
                    curport = []
                    for o in oportData:
                        if o[1] == port:
                            curport.append(o)

                    # check for all segs
                    if len(curport) == curport[0][2]['totsegs']:

                        #print "\tbefore sort"
                        #for o in curport:
                        #    print "\t\t"+str(o[2]['segnum'])

                        # order the segments
                        curport = sorted(curport, key=lambda seg: seg[2]['segnum'])

                        #print "\tafter sort"
                        #for o in curport:
                        #    print "\t\t"+str(o[2]['segnum'])

                    else:
                        log.critical("applyQueuedData():largeNPY aggregation FAILED for port: "+str(port)+"\n\t-num seg mismatch.")
                        continue

                    # gather array segments and reshape NPY array
                    segs = [ o[2]['seg'] for o in curport ]
                    lrgNPY = np.concatenate(segs)
                    lrgNPY.shape = curport[0][2]['shape']
            
                    self._node.setData(port, lrgNPY)

                except:
                    log.critical("applyQueuedData():largeNPY failed. "+str(traceback.format_exc()))
                    #raise
                    self._retcode = -1

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

        self._largeNPYpresent = False
        for o in self._proxy:
            try:
                if o[0] == 'retcode':
                    self._retcode = o[1]
                if o[0] == 'modifyWdg':
                    self._node.modifyWdg(o[1], o[2])
                if o[0] == 'setReQueue':
                    self._node.setReQueue(o[1])
                # move to thread
                #if o[0] == 'setData':
                #    # flag any NPY array for threaded xfer
                #    if type(o[2]) is dict:
                #        if o[2].has_key('951413'):
                #            self._largeNPYpresent = True
                #            continue
                #    self._node.setData(o[1], o[2])
            except:
                log.error("applyQueuedData() failed. "+str(traceback.format_exc()))
                #raise
                self._retcode = -1

        # transfer all setData() calls to a thread
        ExecRunnable(self._applyData_thread)

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


class PTask(multiprocessing.Process, QtCore.QObject):
    finished = gpi.Signal()
    terminated = gpi.Signal()

    def __init__(self, func, title, label, proxy):
        multiprocessing.Process.__init__(self)
        QtCore.QObject.__init__(self)
        self._func = func
        self._title = title
        self._label = label
        self._proxy = proxy
        self._cnt = 0

        # Since we don't know when the process finishes
        # probe at regular intervals.
        # -it would be nicer to have the process check-in with the GPI
        #  main proc when its done.
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.checkProcess)
        self._timer.start(10)  # 10msec update

    def run(self):
        # This try/except is only good for catching compute() exceptions
        # not run() terminations.
        try:
            self._proxy.append(['retcode', self._func()])
        except:
            log.error('PROCESS: \''+str(self._title)+'\':\''+str(self._label)+'\' compute() failed.\n'+str(traceback.format_exc()))
            #raise
            self._proxy.append(['retcode', -1])

    def terminate(self):
        self._timer.stop()
        super(PTask, self).terminate()

    def wait(self):
        self.join()

    def isRunning(self):
        return self.is_alive()

    def retcodeExists(self):
        for o in self._proxy:
            if o[0] == 'retcode':
                return True
        return False

    def checkProcess(self):
        if self.is_alive():
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
