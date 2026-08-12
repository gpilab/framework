"""
spawn_worker.py — worker function for GPI_PROCESS node execution.

Design (Option B):
  - _run_node_task() is submitted to a ProcessPoolExecutor.
  - _ListProxy collects compute() output into a plain Python list.
  - Results are written to a temp file; only the file path is returned
    through ProcessPoolExecutor's SimpleQueue.  SimpleQueue calls
    ForkingPickler.dumps() synchronously in the worker's main thread — if
    the result contains a C-extension object whose pickling segfaults, the
    worker process dies.  By writing to a temp file explicitly and returning
    only the path string (always safe to pickle), we isolate that risk.
  - No module-level gpi package imports so GPI_WORKER_MODE=1 is already set
    in os.environ before gpi.__init__ first runs in the worker.
"""

import collections as _collections
import importlib.util
import os as _os
import pickle as _pickle
import sys as _sys
import tempfile as _tempfile
import time
import traceback

import numpy as np


# ---------------------------------------------------------------------------
# Lightweight proxy — accumulates compute() output into a list
# ---------------------------------------------------------------------------

class _ListProxy:
    def __init__(self):
        self._items = []

    def put(self, item):
        self._items.append(item)


class _CaptureStream:
    """File-like tee: forwards writes to a real stream (or discards, if None)
    while also accumulating everything into an in-memory buffer so the text
    can be relayed back to the parent process afterward.
    """
    def __init__(self, real):
        self._real = real
        self._buf = []

    def write(self, s):
        if self._real is not None:
            try:
                self._real.write(s)
            except Exception:
                pass
        self._buf.append(s)

    def flush(self):
        if self._real is not None:
            try:
                self._real.flush()
            except Exception:
                pass

    def getvalue(self):
        return ''.join(self._buf)


# Resolved once per worker process (module persists across many
# _run_node_task calls in a ProcessPoolExecutor). sys.stdout/stderr get
# replaced with a _CaptureStream on every call, so on the 2nd+ call
# sys.stdout/stderr are no longer the real, fd-backed streams -- caching
# the originals here avoids wrapping a _CaptureStream in another one.
_REAL_STDOUT = None
_REAL_STDERR = None


def _get_real_streams():
    global _REAL_STDOUT, _REAL_STDERR
    if _REAL_STDOUT is None:
        import io as _io
        import sys as _sys
        # Under pythonw.exe (GUI-only launcher, e.g. Start Menu shortcut) the
        # worker inherits None streams. faulthandler needs a real fd-backed
        # file (it bypasses Python I/O on a crash), so fall back to devnull.
        _REAL_STDOUT = _sys.stdout if _sys.stdout is not None else _io.TextIOWrapper(open(_os.devnull, 'wb'))
        _REAL_STDERR = _sys.stderr if _sys.stderr is not None else _io.TextIOWrapper(open(_os.devnull, 'wb'))
    return _REAL_STDOUT, _REAL_STDERR


# Descriptor passed to the worker for a large input array stored in a
# temp memmap file.  Avoids pickling the array through the queue.
_PortDataRef = _collections.namedtuple('_PortDataRef', ['path', 'shape', 'dtype', 'offset'])


class _NativeFDCapture:
    """Redirect the process' OS-level stdout/stderr (fds 1 and 2) into a temp file.

    Reassigning sys.stdout only affects Python-level writes.  Output from C/C++ extensions
    (std::cout, printf, OpenMP/FFTW diagnostics) goes straight to the file descriptors and is
    therefore invisible to _CaptureStream -- and discarded entirely when GPI is launched via
    pythonw.exe, where the worker has no console attached.

    A temp file is used rather than a pipe: a pipe would deadlock as soon as a node wrote more
    than the OS buffer size while nothing was draining it.
    """

    def __init__(self):
        self._tmp = None
        self._saved = {}

    def start(self):
        try:
            self._tmp = _tempfile.TemporaryFile(mode='w+b')
        except Exception:
            self._tmp = None
            return

        for fd in (1, 2):
            try:
                self._saved[fd] = _os.dup(fd)
                _os.dup2(self._tmp.fileno(), fd)
            except OSError:
                # No valid fd (pythonw.exe) -- nothing to capture or restore for this one.
                self._saved.pop(fd, None)

    def saved_fd(self, fd):
        return self._saved.get(fd)

    def stop(self):
        """Restore the original fds and return everything written to them."""
        text = ''
        if self._tmp is not None:
            try:
                self._tmp.flush()
                _os.fsync(self._tmp.fileno())
            except Exception:
                pass

        for fd, saved in self._saved.items():
            try:
                _os.dup2(saved, fd)
                _os.close(saved)
            except OSError:
                pass
        self._saved.clear()

        if self._tmp is not None:
            try:
                self._tmp.seek(0)
                text = self._tmp.read().decode('utf-8', 'replace')
            except Exception:
                pass
            try:
                self._tmp.close()
            except Exception:
                pass
            self._tmp = None

        return text


# ---------------------------------------------------------------------------
# Stub objects that satisfy node.* / self.node.* calls inside compute()
# ---------------------------------------------------------------------------

class _ThreadStubProxy:
    def __init__(self, proxy):
        self._proxy = proxy

    def execType(self):
        from gpi.defines import GPI_PROCESS
        return GPI_PROCESS

    def addToQueue(self, item):
        self._proxy.put(item)


class _NodeStubProxy:
    def __init__(self, node_id, proxy):
        self._id = node_id
        self.nodeCompute_thread = _ThreadStubProxy(proxy)

    def inDisabledState(self):
        return False

    def getID(self):
        return self._id

    def getPortByNumOrTitle(self, pnumORtitle):
        return None


class NodeComputeStub:
    """Stand-in for NodeAPI passed as ``self`` to ExternalNode.compute()
    inside a worker process.  All gpi imports are deferred to method bodies
    so the class can be defined before gpi.__init__ runs in the worker.
    """

    def __init__(self, parm_settings, port_data, events,
                 node_id, node_label, proxy):
        self.parmSettings = parm_settings
        self._port_data = port_data
        self._events = events
        self._node_id = node_id
        self.label = node_label
        self._proxy = proxy
        self.shdmDict = {}
        import logging
        self.log = logging.getLogger('gpi.node')
        self.node = _NodeStubProxy(node_id, proxy)

    # --- widget reads ---

    def getVal(self, title):
        return self.getAttr(title, 'val')

    def getAttr(self, title, attr):
        for wdg in self.parmSettings.get('parms', []):
            if wdg.get('name') == title:
                return wdg.get('kwargs', {}).get(attr)
        raise ValueError(
            f"NodeComputeStub.getAttr(): widget '{title}' attr '{attr}' not found")

    # --- port reads ---

    def getData(self, title):
        data = self._port_data.get(title)
        if isinstance(data, _PortDataRef):
            # Large array was serialized to a memmap file to avoid queue overhead.
            # Return a plain ndarray view backed by the memmap's buffer rather than
            # the np.memmap object itself.  If compute() slices this and passes the
            # result to setData(), DataProxy.NDArray would otherwise see type==np.memmap
            # and store the INPUT temp file path as its shdf — but that file is deleted
            # by _cleanup_input_temps() before applyQueuedData_setData can read it.
            # Wrapping in frombuffer hides the filename, so DataProxy always copies the
            # output data into a fresh GPI-managed memmap file instead.
            # buf.base → memoryview → mm, so the file stays mapped while buf is alive.
            mm = np.memmap(data.path, dtype=data.dtype, mode='r', shape=data.shape, offset=data.offset)
            buf = np.frombuffer(mm.data, dtype=mm.dtype)
            buf.shape = mm.shape
            return buf
        if isinstance(data, np.ndarray):
            buf = np.frombuffer(data.data, dtype=data.dtype)
            buf.shape = tuple(data.shape)
            return buf
        from gpi.mri_data import MRIData
        if isinstance(data, MRIData):
            return data.clone()
        # Ensure any torch.Tensor arriving from a previous node is on CPU.
        # Inter-process transfer always moves tensors to CPU (see setData).
        try:
            import torch as _torch
            if isinstance(data, _torch.Tensor) and data.is_cuda:
                data = data.detach().cpu()
        except ImportError:
            pass
        return data

    # --- port / widget writes ---

    def setData(self, title, data):
        from gpi.dataproxy import DataProxy
        from gpi.mri_data import MRIData
        if isinstance(data, (np.memmap, np.ndarray)):
            shdf = self.shdmDict.get(str(id(data)))
            s = (DataProxy().NDArray(data, shdf=shdf, nodeID=self._node_id, portname=title)
                 if shdf else
                 DataProxy().NDArray(data, nodeID=self._node_id, portname=title))
            if isinstance(s, list):
                for seg in s:
                    self._proxy.put(['setData', title, seg])
            else:
                self._proxy.put(['setData', title, s])
        elif isinstance(data, MRIData):
            from gpi.dataproxy import DataProxy
            s = DataProxy().setMRIData(data, nodeID=self._node_id, portname=title)
            self._proxy.put(['setData', title, s])
        else:
            # torch.Tensor on CUDA cannot be pickled across spawned processes via
            # ProcessPoolExecutor — attempting to do so hangs because PyTorch tries
            # to set up CUDA IPC shared memory, which is not supported in this
            # executor context.  Synchronize the GPU and move to CPU so the tensor
            # travels cleanly between processes.  The downstream node is responsible
            # for moving it back to the desired device (e.g. tensor.cuda()).
            try:
                import torch as _torch
                if isinstance(data, _torch.Tensor) and data.is_cuda:
                    _torch.cuda.synchronize(data.device)
                    data = data.detach().cpu()
            except ImportError:
                pass
            self._proxy.put(['setData', title, data])

    def setAttr(self, title, **kwargs):
        self._proxy.put(['modifyWdg', title, kwargs])

    def setReQueue(self, val=False):
        self._proxy.put(['setReQueue', val])

    # --- array allocation ---

    def allocArray(self, shape=(1,), dtype=np.float32, name='local'):
        from gpi.dataproxy import DataProxy
        buf, shd = DataProxy()._genNDArrayMemmap(shape, dtype, self._node_id, name)
        if shd is not None:
            self.shdmDict[str(id(buf))] = shd.filename
        return buf

    # --- UI setup (no-ops in worker) ---

    def addWidget(self, *_a, **_kw):   pass
    def addInPort(self, *_a, **_kw):   pass
    def addOutPort(self, *_a, **_kw):  pass
    def setPortQueueMax(self, *_a, **_kw): pass
    def addMenuItem(self, *_a, **_kw): pass

    # --- status (no-ops) ---

    def setStatus(self, msg):          pass
    def setStatus_sys(self, msg):      pass
    def setDetailLabel(self, newDetailLabel='', elideMode='middle'): pass
    def getDetailLabel(self):          return ''
    def getLabel(self):                return self.label

    # --- events ---

    def getEvents(self):
        return self._events

    def portEvents(self):
        from gpi.defines import GPI_PORT_EVENT
        return self._events.get(GPI_PORT_EVENT, set())

    def widgetEvents(self):
        from gpi.defines import GPI_WIDGET_EVENT
        return self._events.get(GPI_WIDGET_EVENT, set())

    # --- module helpers ---

    def moduleExists(self, name):
        try:
            return importlib.util.find_spec(name) is not None
        except (ModuleNotFoundError, ValueError):
            return False

    def moduleValidated(self, name):
        if not self.moduleExists(name):
            self.log.error(f"The '{name}' module cannot be found, compute() aborted.")
            return 1
        return 0

    def starttime(self):
        self._starttime = time.time()

    def endtime(self, msg=''):
        pass

    def getInPort(self, pnumORtitle):  return None
    def getOutPort(self, pnumORtitle): return None


# ---------------------------------------------------------------------------
# Top-level worker function — submitted to ProcessPoolExecutor
# ---------------------------------------------------------------------------

def _noop():
    """Trivial no-op used to pre-warm executor workers at pool creation."""
    return []


def _add_pkg_root_to_syspath(module_path):
    """Make the node's enclosing package importable, as library.PKGroot does in the parent.

    Worker processes are spawned, not forked, so they never inherit the package roots the
    parent appends when scanning the node library.  Without this, a node that imports its
    own sibling package (e.g. a compiled extension) fails with ModuleNotFoundError.
    """
    path = _os.path.dirname(_os.path.abspath(module_path))

    if _os.path.basename(path) == 'GPI':
        path = _os.path.dirname(path)

    while _os.path.isfile(_os.path.join(path, '__init__.py')):
        parent = _os.path.dirname(path)
        if parent == path:
            break
        path = parent

    if path not in _sys.path:
        _sys.path.insert(0, path)


# Module-level cache: persists for the lifetime of the worker process.
# Each worker builds its own cache independently.  Second and subsequent
# runs of the same node type skip the importlib overhead entirely.
# Cache maps module_path -> (mtime, module) so edits invalidate the entry.
_module_cache: dict = {}


def _run_node_task(module_path, parm_settings, port_data, events,
                   node_id, node_label, title, label):
    """Execute ExternalNode.compute() and return all output as a list.

    Runs in a ProcessPoolExecutor worker process.  GPI_WORKER_MODE=1 is
    already in os.environ (inherited from parent) so gpi.__init__ imports
    only the lightweight layer when the node module first does ``import gpi``.

    Return value is a list of items: [['setData', port, data], ..., ['retcode', n]]
    The parent's _FutureWatcher receives this list via future.result().
    """
    import faulthandler as _fh
    import sys as _sys

    _real_stdout, _real_stderr = _get_real_streams()

    _fh.enable(file=_real_stderr)   # dump native C stack trace on crash

    # Capture of the OS-level fds (C/C++ extension output) is opt-in while it is being
    # validated; set GPI_CAPTURE_NATIVE_STDOUT=1 to enable.
    _native = _NativeFDCapture()
    if _os.environ.get('GPI_CAPTURE_NATIVE_STDOUT') == '1':
        _native.start()

        # fd 2 now points at the capture file, which is lost if the process dies outright, so
        # keep faulthandler pointed at the inherited stderr.
        _saved_err_fd = _native.saved_fd(2)
        if _saved_err_fd is not None:
            try:
                _fh.enable(file=_os.fdopen(_saved_err_fd, 'w', closefd=False))
            except Exception:
                pass

        _cap_out = _CaptureStream(None)
        _cap_err = _CaptureStream(None)
    else:
        # Tee stdout/stderr into an in-memory buffer too. Without this, all the
        # print() diagnostics/tracebacks below vanish silently under pythonw.exe:
        # the worker is a separate OS process with its own stdout/stderr, so the
        # parent's Tee-wrapped console widget (mainWindow.console()) never sees
        # them. Capturing here lets us relay the text back through the proxy so
        # the parent can display it regardless of how GPI was launched.
        _cap_out = _CaptureStream(_real_stdout)
        _cap_err = _CaptureStream(_real_stderr)

    _sys.stdout = _cap_out
    _sys.stderr = _cap_err

    # Limit threading in C extensions to avoid OpenMP/BLAS init crashes
    # in a freshly spawned process on Windows.  These must be set before the
    # first parallel C region runs (i.e. before the node module is imported).
    for _var in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        _os.environ.setdefault(_var, '1')

    proxy = _ListProxy()
    try:
        _add_pkg_root_to_syspath(module_path)

        mtime = _os.path.getmtime(module_path)
        cached = _module_cache.get(module_path)
        if cached is None or cached[0] != mtime:
            spec = importlib.util.spec_from_file_location('_gpi_node_worker', module_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _module_cache[module_path] = (mtime, mod)
        mod        = _module_cache[module_path][1]
        node_class = getattr(mod, 'ExternalNode')

        _framework = frozenset({
            'compute', 'initUI', 'validate', 'execType', 'execInternalType',
            '__init__', '__new__', '__dict__', '__weakref__', '__doc__',
        })
        _helpers = {
            name: func
            for name, func in vars(node_class).items()
            if callable(func) and name not in _framework
        }
        StubClass = (
            type('_NodeStub', (NodeComputeStub,), _helpers)
            if _helpers else NodeComputeStub
        )

        stub = StubClass(parm_settings, port_data, events, node_id, node_label, proxy)

        try:
            node_class.initUI(stub)
        except Exception:
            print(f"[GPI_PROCESS] '{title}':'{label}': initUI() raised (ignored):\n"
                  + traceback.format_exc(), flush=True)

        validate = getattr(node_class, 'validate', None)
        if validate is not None:
            try:
                validate(stub)
            except Exception:
                print(f"[GPI_PROCESS] '{title}':'{label}': validate() raised (ignored):\n"
                      + traceback.format_exc(), flush=True)

        retcode = node_class.compute(stub)
        proxy.put(['retcode', retcode])

    except BaseException:
        # BaseException catches SystemExit too (some nodes call sys.exit()).
        print(f"[GPI_PROCESS] ERROR in '{title}':'{label}':\n"
              + traceback.format_exc(), flush=True)
        proxy.put(['retcode', -1])

    _captured = _cap_out.getvalue() + _cap_err.getvalue() + _native.stop()
    if _captured.strip():
        proxy.put(['stdout', _captured])

    # Force GC so any np.memmap objects opened via _PortDataRef.getData() are
    # closed before this function returns.  The parent process deletes those
    # temp files after future.result() completes; on Windows a file cannot be
    # deleted while it is still mapped, so we must release handles first.
    import gc as _gc
    _gc.collect()

    # Serialize and return results.
    #
    # Fast path: if the pickled payload is small, return it as bytes directly
    # through the ProcessPoolExecutor queue — no disk I/O.  For typical nodes
    # (widget updates, DataProxy metadata, scalars) this is always the case
    # because numpy arrays are already stored in memmap files and only their
    # lightweight DataProxy descriptors travel through this path.
    #
    # Slow path: write to a temp file and return only the path string.  Used
    # for large payloads (avoids congesting the SimpleQueue) and as a fallback
    # if the first serialization attempt fails.
    # In practice proxy._items is always small: numpy arrays are stored in
    # memmap files and only their lightweight DataProxy descriptors travel here.
    # The temp file path is kept only as a fallback if pickling raises.
    _serialized = None
    try:
        _serialized = _pickle.dumps(proxy._items, protocol=4)
        return ('direct', _serialized)
    except Exception:
        print(f"[GPI_PROCESS] direct serialization failed for '{title}', "
              "falling back to temp file:\n" + traceback.format_exc(), flush=True)

    tmp_path = None
    try:
        fd, tmp_path = _tempfile.mkstemp(suffix='.gpi_res')
        _os.close(fd)
        with open(tmp_path, 'wb') as f:
            if _serialized is not None:
                f.write(_serialized)   # reuse the bytes already in memory
            else:
                _pickle.dump(proxy._items, f, protocol=4)
        return ('file', tmp_path)
    except BaseException:
        print(f"[GPI_PROCESS] result serialization failed for '{title}':\n"
              + traceback.format_exc(), flush=True)
        if tmp_path:
            try:
                _os.unlink(tmp_path)
            except Exception:
                pass
        return None
