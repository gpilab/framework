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
import os
import tempfile
import time
import threading
import numpy as np
import traceback
import multiprocessing
from concurrent.futures import ProcessPoolExecutor as _ProcessPoolExecutor

import gpi
from gpi import QtCore
from .dataproxy import DataProxy, ProxyType
from .defines import GPI_PROCESS, GPI_THREAD, GPI_APPLOOP
from .logger import manager
from .sysspecs import Specs

# start logger for this module
log = manager.getLogger(__name__)

# ---------------------------------------------------------------------------
# ProcessPoolExecutor for GPI_PROCESS nodes (all platforms)
# ---------------------------------------------------------------------------

_executor = None

def _worker_count():
    """Return the number of GPI_PROCESS workers to pre-warm.

    Reads GPI_NUM_WORKERS from the environment; falls back to min(4, cpu_count()).
    Set GPI_NUM_WORKERS=1 to serialise all GPI_PROCESS nodes (useful for debugging).
    """
    try:
        n = int(os.environ.get('GPI_NUM_WORKERS', '0'))
        if n > 0:
            return n
    except (ValueError, TypeError):
        pass
    return min(4, multiprocessing.cpu_count())


def _new_executor():
    """Spawn a fresh ProcessPoolExecutor with pre-warmed workers."""
    from concurrent.futures import wait as _wait
    import gpi.spawn_worker as _sw
    n = _worker_count()
    log.info(f"_new_executor(): spawning {n} GPI_PROCESS worker(s) "
             f"(set GPI_NUM_WORKERS env var to override)")
    previous_worker_mode = os.environ.get('GPI_WORKER_MODE')
    os.environ['GPI_WORKER_MODE'] = '1'
    try:
        ex = _ProcessPoolExecutor(
            max_workers=n,
            mp_context=multiprocessing.get_context('spawn'),  # always spawn; fork is unsafe after Qt init
        )
        _wait([ex.submit(_sw._noop) for _ in range(n)])
    finally:
        if previous_worker_mode is None:
            os.environ.pop('GPI_WORKER_MODE', None)
        else:
            os.environ['GPI_WORKER_MODE'] = previous_worker_mode
    return ex


def _get_executor():
    """Return the global executor, (re)creating it if needed or broken."""
    global _executor
    if _executor is None:
        _executor = _new_executor()
    return _executor


def _reset_executor():
    """Discard a broken executor so the next call to _get_executor() rebuilds it."""
    global _executor
    old = _executor
    _executor = None
    if old is not None:
        try:
            old.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass


def _shutdown_executor():
    """Stop all GPI_PROCESS workers during normal application shutdown."""
    global _executor
    executor = _executor
    _executor = None
    if executor is not None:
        try:
            executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass


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
    #print 'active threads: ', tp.activeThreadCount()
    #print 'expiry timeout: ', tp.expiryTimeout()
    #print 'maxThreadCount: ', tp.maxThreadCount()
    tp.start(runnable)

class GPIRunnable(QtCore.QRunnable):
    def __init__(self, func):
        super(GPIRunnable, self).__init__()
        self.run = func
        self.setAutoDelete(True)

class GPIFunctor(QtCore.QObject):
    '''A common parent API for each execution type (i.e. ATask, _SpawnPTask, TTask).
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

        self._execType = node._nodeIF.execType()

        self._label = node._nodeIF.getLabel()
        self._isTerminated = False
        self._compute_start = 0

        self._proxy = None
        self._proc = None
        if self._execType == GPI_PROCESS:
            log.debug("init(): set as GPI_PROCESS: "+str(self._title))
            self._proc = _SpawnPTask(node, self._title, self._label)

            # apply data in a thread to make the GUI more responsive
            self._applyData_thread = GPIRunnable(self.applyQueuedData_setData)

        elif self._execType == GPI_THREAD:
            log.debug("init(): set as GPI_THREAD: "+str(self._title))
            self._proc = TTask(self._func, self._title, self._label, self._proxy)

        else:  # default to GPI_APPLOOP
            log.debug("init(): set as GPI_APPLOOP: "+str(self._title))
            self._proc = ATask(self._func, self._title, self._label, self._proxy)

        self._proc.finished.connect(self.computeFinished)
        # _SpawnPTask exposes a terminated signal for worker crashes.
        if self._execType == GPI_PROCESS:
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
        # Sweep stale memmap FDs after each compute to prevent accumulation.
        try:
            from .dataproxy import _fd_manager
            _fd_manager._evict_if_needed()
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
        except Exception:
            log.error('validate() raised an exception:\n' + traceback.format_exc())
            self._validate_retcode = 1 # validate error
        self._execType = tmp_exec

        # None as zero

        # send validate() return code thru same channels
        if self._validate_retcode != 0 and self._validate_retcode is not None:
            self._node.appendWallTime(time.time() - self._compute_start)
            self.finished.emit(1) # validate error
            return

        # COMPUTE
        if self._execType == GPI_PROCESS:
            log.debug("start(): buffer process parms")
            self._node._nodeIF.bufferParmSettings()

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
            self._proxy = self._proc._drained
            self.applyQueuedData()

        else:
            raw = self._proc._retcode
            # Allow compute() to return a non-empty string as a failure message.
            if isinstance(raw, str) and raw:
                log.error(f"compute() '{self._title}': {raw}")
                self._node._nodeIF.setStatus(raw)
                self._retcode = Return.ComputeError
            elif Return.isError(raw):
                self._retcode = Return.ComputeError
            else:
                self._retcode = 0  # success
            self.finalMatter()

    def finalMatter(self):
        log.info("computeFinished():Node \'"+str(self._title)+"\': compute time:"+str(time.time() - self._compute_start)+" sec.")
        self._node.appendWallTime(time.time() - self._compute_start)
        self.finished.emit(self._retcode) # success

    def applyQueuedData_setData(self):

        for o in self._proxy:
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
            except Exception:
                log.error("applyQueuedData() failed. "+str(traceback.format_exc()))
                self._retcode = Return.ComputeError
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

        # run self.applyQueuedData_finalMatter()
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
                    raw = o[1]
                    # Allow compute() to return a non-empty string as a failure message.
                    if isinstance(raw, str) and raw:
                        log.error(f"compute() '{self._title}': {raw}")
                        self._node._nodeIF.setStatus(raw)
                        self._retcode = Return.ComputeError
                    elif Return.isError(raw):
                        self._retcode = Return.ComputeError
                    else:
                        self._retcode = 0  # squash Nones
                if o[0] == 'modifyWdg':
                    self._node.modifyWdg(o[1], o[2])
                if o[0] == 'setReQueue':
                    self._node.setReQueue(o[1])
                if o[0] == 'stdout':
                    # Worker-side print()/traceback output. Relayed here because
                    # a GPI_PROCESS worker is a separate OS process with its own
                    # stdout/stderr — under pythonw.exe (Start Menu shortcut,
                    # no console) that output would otherwise be silently lost.
                    try:
                        print(f"----- worker output ('{self._title}':'{self._label}') -----\n"
                              + o[1], end='' if o[1].endswith('\n') else '\n')
                    except Exception:
                        pass
            except Exception:
                log.error("applyQueuedData() failed. "+str(traceback.format_exc()))
                self._retcode = Return.ComputeError

        # setData() updates QGraphicsItems and may trigger downstream GUI nodes.
        # applyQueuedData() runs on the Qt main thread, so keep that work here.
        log.debug("applyQueuedData(): apply setData() on the main thread")
        self.applyQueuedData_setData()

    def applyQueuedData_finalMatter(self):

        if Return.isComputeError(self._retcode):
            self.finished.emit(self._retcode)

        elapsed = (time.time() - self._ap_st_time)
        log.info("applyQueuedData(): time (total queue): "+str(elapsed)+" sec")

        # shutdown the proxy manager
        self.cleanup()

        # start self.finalMatter
        self.applyQueuedData_finished.emit()


# Keeps strong references to in-flight _FutureWatcher threads.
# Without this, Python GC can destroy a watcher (via _SpawnPTask refcount drop)
# while its run() method is still executing, triggering Qt's
# "QThread: Destroyed while thread is still running" fatal message.
_live_watchers: set = set()


class _FutureWatcher(QtCore.QThread):
    '''Blocks on future.result() in a background QThread, then emits _complete
    with the returned list.  Zero CPU spin while waiting.
    '''
    _complete = gpi.Signal(list)
    _stdout = gpi.Signal(str)

    def __init__(self, future, title='', label='', stdout_path=None):
        super(_FutureWatcher, self).__init__()
        self._future = future
        self._title  = title
        self._label  = label
        self._stdout_path = stdout_path
        self._stdout_offset = 0
        _live_watchers.add(self)             # prevent GC until thread finishes
        self.finished.connect(self._release) # QThread.finished fires after run() returns

    def _release(self):
        '''Called in the main thread after run() completes.  Safe to delete now.'''
        _live_watchers.discard(self)
        self.deleteLater()

    def _cleanup_stdout_after_future(self, path):
        try:
            self._future.result()
        except Exception:
            pass
        try:
            os.unlink(path)
        except OSError:
            pass

    def run(self):
        import os as _os
        import pickle as _pickle
        from concurrent.futures.process import BrokenProcessPool
        try:
            _timeout = int(os.environ.get('GPI_COMPUTE_TIMEOUT', '300'))
        except (ValueError, TypeError):
            _timeout = 300
        start_time = time.time()
        while not self._future.done():
            self._emit_stdout()
            if time.time() - start_time >= _timeout:
                log.error(
                    f"_FutureWatcher: node '{self._title}':'{self._label}' timed out after "
                    f"{_timeout} s — worker is still running in background; consider increasing "
                    "GPI_COMPUTE_TIMEOUT or checking for an infinite loop in compute()"
                )
                if self._stdout_path:
                    threading.Thread(
                        target=self._cleanup_stdout_after_future,
                        args=(self._stdout_path,),
                        daemon=True,
                    ).start()
                self._complete.emit([['retcode', -1]])
                return
            self.msleep(100)
        self._emit_stdout()
        try:
            raw = self._future.result()
        except BrokenProcessPool:
            log.error('_FutureWatcher: worker process crashed; resetting pool:\n'
                      + traceback.format_exc())
            _reset_executor()
            self._complete.emit([['retcode', -1]])
            return
        except TimeoutError:
            log.error(
                f"_FutureWatcher: node '{self._title}':'{self._label}' timed out after "
                f"{_timeout} s — worker is still running in background; consider increasing "
                "GPI_COMPUTE_TIMEOUT or checking for an infinite loop in compute()"
            )
            self._complete.emit([['retcode', -1]])
            return
        except Exception:
            log.error('_FutureWatcher: future raised:\n' + traceback.format_exc())
            self._complete.emit([['retcode', -1]])
            return

        if raw is None:
            self._complete.emit([['retcode', -1]])
            return

        kind, value = raw

        if kind == 'direct':
            try:
                result = _pickle.loads(value)
            except Exception:
                log.error('_FutureWatcher: failed to deserialise direct result:\n'
                          + traceback.format_exc())
                result = [['retcode', -1]]
        else:  # 'file'
            try:
                with open(value, 'rb') as f:
                    result = _pickle.load(f)
            except Exception:
                log.error('_FutureWatcher: failed to read result file:\n'
                          + traceback.format_exc())
                result = [['retcode', -1]]
            finally:
                try:
                    _os.unlink(value)
                except Exception:
                    pass

        self._complete.emit(result)

    def _emit_stdout(self):
        if not self._stdout_path:
            return
        try:
            with open(self._stdout_path, 'r', encoding='utf-8', errors='replace') as stream:
                stream.seek(self._stdout_offset)
                text = stream.read()
                self._stdout_offset = stream.tell()
            if text:
                self._stdout.emit(text)
        except (FileNotFoundError, OSError):
            pass

    def cancel(self):
        self._future.cancel()


class _SpawnPTask(QtCore.QObject):
    '''Windows GPI_PROCESS execution via ProcessPoolExecutor.

    Submits _run_node_task() to the global executor.  A _FutureWatcher thread
    blocks on future.result() off the main thread, then emits _complete with
    the returned list.  No IPC queues, no dispatcher thread.
    '''

    finished   = gpi.Signal()
    terminated = gpi.Signal()

    def __init__(self, node, title, label):
        super(_SpawnPTask, self).__init__()
        self._node    = node
        self._title   = title
        self._label   = label
        self._watcher = None
        self._drained = []
        self._input_temp_paths = []  # temp memmap files created for large input arrays
        self._stdout_path = None

    def _relay_stdout(self, text):
        if text:
            message = (f"worker output ('{self._title}':'{self._label}'):\n"
                       + text.rstrip())
            canvas = getattr(self._node.graph, 'parent', None)
            worker_output = getattr(canvas, 'workerOutput', None)
            if worker_output is not None:
                worker_output.emit(message + '\n')
            else:
                print(message, flush=True)
            log.info(message)

    def _build_port_data(self):
        """Serialize large input arrays to temp memmaps; return port_data dict.

        Arrays >= 1 MB are written to temp files and replaced with lightweight
        _PortDataRef descriptors so they bypass the SimpleQueue entirely.
        np.memmap arrays that already have a backing file are referenced directly
        (no copy).  Paths of newly created files are stored in _input_temp_paths
        for cleanup after the worker finishes.
        """
        from .spawn_worker import _PortDataRef
        _THRESHOLD = 1024 * 1024  # 1 MB

        self._input_temp_paths = []
        port_data = {}
        for p in self._node.inportList:
            data = p.getUpstreamData()
            if isinstance(data, np.ndarray) and data.nbytes >= _THRESHOLD:
                fname = getattr(data, 'filename', None)  # set on np.memmap
                mmap_offset = int(getattr(data, 'offset', 0))
                if fname and os.path.exists(fname):
                    # Already a memmap — reference existing file directly (zero-copy).
                    # Pass the byte offset so the worker maps from the right position
                    # (non-zero for .npy files whose header precedes the array data).
                    port_data[p.portTitle] = _PortDataRef(fname, data.shape, data.dtype.str, mmap_offset)
                else:
                    # Plain ndarray — write to a new temp memmap
                    fd, path = tempfile.mkstemp(suffix='.gpi_in')
                    os.close(fd)
                    mm = np.memmap(path, dtype=data.dtype, mode='w+', shape=data.shape)
                    np.copyto(mm, data)
                    mm.flush()
                    del mm
                    port_data[p.portTitle] = _PortDataRef(path, data.shape, data.dtype.str, 0)
                    self._input_temp_paths.append(path)
            else:
                port_data[p.portTitle] = data
        return port_data

    def _cleanup_input_temps(self):
        for path in self._input_temp_paths:
            try:
                os.unlink(path)
            except Exception:
                pass
        self._input_temp_paths = []

    def start(self):
        from .spawn_worker import _run_node_task
        from concurrent.futures import BrokenExecutor
        parm_settings = self._node._nodeIF.parmSettings
        port_data     = self._build_port_data()
        events        = self._node._nodeIF.getEvents()
        fd, self._stdout_path = tempfile.mkstemp(suffix='.gpi_stdout')
        os.close(fd)

        args = (
            self._node._ext_filename,
            parm_settings, port_data, events,
            self._node.getID(), self._label,
            self._title, self._label,
            self._stdout_path,
        )
        try:
            future = _get_executor().submit(_run_node_task, *args)
        except BrokenExecutor:
            log.warn(f"_SpawnPTask: pool was broken, resetting and retrying '{self._title}'")
            _reset_executor()
            try:
                future = _get_executor().submit(_run_node_task, *args)
            except Exception:
                log.error(f"_SpawnPTask: pool still broken after reset for '{self._title}'")
                try:
                    os.unlink(self._stdout_path)
                except OSError:
                    pass
                self._stdout_path = None
                self._drained = [['retcode', -1]]
                self.finished.emit()
                return

        self._watcher = _FutureWatcher(
            future, self._title, self._label, self._stdout_path)
        self._watcher._stdout.connect(self._relay_stdout)
        self._watcher._complete.connect(self._on_complete)
        self._watcher.start()

    def _on_complete(self, drained):
        self._drained = drained
        self._cleanup_input_temps()
        if self._stdout_path:
            try:
                os.unlink(self._stdout_path)
            except OSError:
                pass
            self._stdout_path = None
        self._watcher = None  # drop our ref; _live_watchers keeps it alive until finished
        if any(item[0] == 'retcode' for item in drained):
            self.finished.emit()
        else:
            self.terminated.emit()

    def terminate(self):
        if self._watcher:
            self._watcher.cancel()
        self._cleanup_input_temps()

    def wait(self):
        if self._watcher:
            self._watcher.wait()

    def isRunning(self):
        return self._watcher.isRunning() if self._watcher else False


class _TTaskSignals(QtCore.QObject):
    '''Signals for TTask (QRunnable cannot own signals directly).'''
    finished = gpi.Signal()
    terminated = gpi.Signal()


class TTask(QtCore.QRunnable):
    '''QThreadPool-based node runner. Reuses pooled threads instead of
    creating a new OS thread per node execution.

    Keeps the same external interface as the old QThread-based TTask so
    GPIFunctor requires no changes.
    '''

    def __init__(self, func, title, label, proxy):
        super(TTask, self).__init__()
        self._func = func
        self._title = title
        self._label = label
        self._proxy = proxy
        self._retcode = None
        self._running = False
        self._done = threading.Event()

        self._signals = _TTaskSignals()
        self.finished = self._signals.finished
        self.terminated = self._signals.terminated

        self.setAutoDelete(False)  # GPIFunctor holds the reference

    def start(self):
        self._running = True
        self._done.clear()
        QtCore.QThreadPool.globalInstance().start(self)

    def run(self):
        try:
            self._retcode = self._func()
            log.info("TTask _func() finished")
        except Exception:
            log.error('THREAD: \''+str(self._title)+'\':\''+str(self._label)+'\' compute() failed.\n'+str(traceback.format_exc()))
            self._retcode = Return.ComputeError
        finally:
            self._running = False
            self._done.set()
        self._signals.finished.emit()

    def terminate(self):
        log.warn("WARNING: Terminated QRunnable-Node is backgrounded as a zombie.")

    def wait(self):
        self._done.wait()

    def isRunning(self):
        return self._running

    def quit(self):
        pass


class ATask(QtCore.QObject):
    '''App-Loop or Main-Loop executed task.  This will block GUI updates.  Data
    is communicated directly.

        NOTE: The apploop-type blocks until finished, obviating the need for
        signals or timer checks
    '''

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
        except Exception:
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
