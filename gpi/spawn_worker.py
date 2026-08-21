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
import threading as _threading
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
    def __init__(self, real, stream_file=None):
        self._real = real
        self._stream_file = stream_file
        self._buf = []

    def write(self, s):
        if self._real is not None:
            try:
                self._real.write(s)
            except Exception:
                pass
        if self._stream_file is not None:
            try:
                try:
                    self._stream_file.write(s)
                except TypeError:
                    self._stream_file.write(s.encode('utf-8', 'replace'))
                if '\n' in s:
                    self._stream_file.flush()
            except Exception:
                pass
        self._buf.append(s)

    def flush(self):
        if self._real is not None:
            try:
                self._real.flush()
            except Exception:
                pass
        if self._stream_file is not None:
            try:
                self._stream_file.flush()
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

# (node label, port title) pairs already warned about a GPU->CPU transfer,
# so the hint below prints once per node per worker process, not every call.
_gpu_cpu_transfer_warned = set()


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
        self._saved_std_handles = {}
        self._crt_redirects = []

    def _redirect_msvcrt_fds(self):
        if _os.name != 'nt' or self._tmp is None:
            return
        try:
            import ctypes as _ctypes
            import msvcrt as _msvcrt
        except (AttributeError, OSError, TypeError, ValueError):
            return

        for crt_name in ('msvcrt', 'ucrtbase'):
            try:
                crt = _ctypes.CDLL(crt_name)
                crt._dup.argtypes = [_ctypes.c_int]
                crt._dup.restype = _ctypes.c_int
                crt._dup2.argtypes = [_ctypes.c_int, _ctypes.c_int]
                crt._dup2.restype = _ctypes.c_int
                crt._close.argtypes = [_ctypes.c_int]
                crt._close.restype = _ctypes.c_int
                crt._open_osfhandle.argtypes = [_ctypes.c_void_p, _ctypes.c_int]
                crt._open_osfhandle.restype = _ctypes.c_int

                kernel32 = _ctypes.WinDLL('kernel32', use_last_error=True)
                kernel32.GetCurrentProcess.restype = _ctypes.c_void_p
                kernel32.DuplicateHandle.argtypes = [
                    _ctypes.c_void_p, _ctypes.c_void_p, _ctypes.c_void_p,
                    _ctypes.POINTER(_ctypes.c_void_p), _ctypes.c_uint32,
                    _ctypes.c_bool, _ctypes.c_uint32]
                kernel32.DuplicateHandle.restype = _ctypes.c_bool
                source = _msvcrt.get_osfhandle(self._tmp.fileno())
                duplicate = _ctypes.c_void_p()
                process = kernel32.GetCurrentProcess()
                if not kernel32.DuplicateHandle(
                        process, _ctypes.c_void_p(source), process,
                        _ctypes.byref(duplicate), 0, True, 2):
                    continue

                native_fd = crt._open_osfhandle(duplicate, 0x8001)
                if native_fd < 0:
                    continue
                saved_fds = {}
                for fd in (1, 2):
                    saved = crt._dup(fd)
                    if saved >= 0:
                        saved_fds[fd] = saved
                    if crt._dup2(native_fd, fd) != 0:
                        saved_fds.pop(fd, None)
                crt._close(native_fd)
                self._crt_redirects.append((crt, saved_fds))
            except (AttributeError, OSError, TypeError, ValueError):
                continue

    def _restore_msvcrt_fds(self):
        for crt, saved_fds in self._crt_redirects:
            for fd, saved in saved_fds.items():
                try:
                    crt._dup2(saved, fd)
                    crt._close(saved)
                except OSError:
                    pass
        self._crt_redirects.clear()

    def _redirect_windows_std_handles(self):
        if _os.name != 'nt':
            return
        try:
            import ctypes as _ctypes
            import msvcrt as _msvcrt
            kernel32 = _ctypes.WinDLL('kernel32', use_last_error=True)
            kernel32.GetStdHandle.argtypes = [_ctypes.c_uint32]
            kernel32.GetStdHandle.restype = _ctypes.c_void_p
            kernel32.SetStdHandle.argtypes = [_ctypes.c_uint32, _ctypes.c_void_p]
            kernel32.SetStdHandle.restype = _ctypes.c_bool
            os_handle = _msvcrt.get_osfhandle(self._tmp.fileno())
            for std_id in (0xFFFFFFF5, 0xFFFFFFF4):
                self._saved_std_handles[std_id] = kernel32.GetStdHandle(std_id)
                kernel32.SetStdHandle(std_id, os_handle)
        except (AttributeError, OSError, TypeError):
            self._saved_std_handles.clear()

    def _restore_windows_std_handles(self):
        if _os.name != 'nt':
            return
        try:
            import ctypes as _ctypes
            kernel32 = _ctypes.WinDLL('kernel32', use_last_error=True)
            kernel32.SetStdHandle.argtypes = [_ctypes.c_uint32, _ctypes.c_void_p]
            kernel32.SetStdHandle.restype = _ctypes.c_bool
            for std_id, handle in self._saved_std_handles.items():
                kernel32.SetStdHandle(std_id, handle)
        except (AttributeError, OSError, TypeError):
            pass
        self._saved_std_handles.clear()

    def start(self, stream_path=None):
        try:
            if stream_path:
                self._tmp = open(stream_path, 'a+b', buffering=0)
            else:
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
        self._redirect_msvcrt_fds()
        self._redirect_windows_std_handles()

    def saved_fd(self, fd):
        return self._saved.get(fd)

    def flush(self):
        try:
            self._tmp.flush()
            _os.fsync(self._tmp.fileno())
        except Exception:
            pass

    def stop(self):
        """Restore the original fds and return everything written to them."""
        text = ''
        if self._tmp is not None:
            try:
                self._tmp.flush()
                _os.fsync(self._tmp.fileno())
            except Exception:
                pass

        self._restore_windows_std_handles()
        self._restore_msvcrt_fds()
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


def _configure_native_output():
    """Make native printf output visible promptly through the worker spool file."""
    if _os.name != 'nt':
        return
    import ctypes as _ctypes
    for crt_name in ('msvcrt', 'ucrtbase'):
        try:
            crt = _ctypes.CDLL(crt_name)
            setvbuf = crt.setvbuf
            setvbuf.argtypes = [_ctypes.c_void_p, _ctypes.c_void_p,
                                _ctypes.c_int, _ctypes.c_size_t]
            setvbuf.restype = _ctypes.c_int
            stdout = _ctypes.c_void_p.in_dll(crt, 'stdout')
            stderr = _ctypes.c_void_p.in_dll(crt, 'stderr')
            setvbuf(stdout, None, 4, 0)  # _IONBF
            setvbuf(stderr, None, 4, 0)
            return
        except (AttributeError, OSError, TypeError, ValueError):
            continue


def _flush_native_output():
    if _os.name != 'nt':
        return
    import ctypes as _ctypes
    for crt_name in ('msvcrt', 'ucrtbase'):
        try:
            _ctypes.CDLL(crt_name).fflush(None)
            return
        except (AttributeError, OSError, TypeError, ValueError):
            continue


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
            if isinstance(data, _torch.Tensor) and data.device.type != 'cpu':
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
            # torch.Tensor on CUDA/MPS cannot be pickled across spawned processes via
            # ProcessPoolExecutor — attempting to do so hangs because PyTorch tries
            # to set up CUDA IPC (or fails outright for MPS) shared memory, neither of
            # which is supported in this executor context.  Synchronize the device and
            # move to CPU so the tensor travels cleanly between processes.  The
            # downstream node is responsible for moving it back to the desired device
            # (e.g. tensor.cuda() / tensor.to('mps')).
            try:
                import torch as _torch
                if isinstance(data, _torch.Tensor) and data.device.type != 'cpu':
                    dev_type = data.device.type
                    if dev_type == 'mps':
                        _torch.mps.synchronize()
                    else:
                        _torch.cuda.synchronize(data.device)
                    data = data.detach().cpu()
                    warn_key = (self.label, title)
                    if warn_key not in _gpu_cpu_transfer_warned:
                        _gpu_cpu_transfer_warned.add(warn_key)
                        print(f"[GPI_PROCESS] '{self.label}': output '{title}' is a {dev_type} "
                              f"tensor, moved to CPU to cross the process boundary. If neighboring "
                              f"nodes are also GPU-only, set this node's execType to GPI_THREAD to "
                              f"keep tensors on-device and skip this transfer.", flush=True)
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

def _worker_init(gpu_lock):
    """ProcessPoolExecutor initializer: run once per worker at pool creation,
    before any node task.

    Installs the parent's GPU-exclusivity lock (see gpi.gpu.exclusive()) so
    this worker and every other worker/the main process all serialize on the
    SAME lock object instead of one apiece.
    """
    try:
        from gpi.gpu import set_shared_lock
        set_shared_lock(gpu_lock)
    except Exception:
        pass


def _noop():
    """Trivial no-op used to pre-warm executor workers at pool creation."""
    return []


def _warm_device():
    """Best-effort CUDA/MPS context init, run once per worker at pool creation.

    Without this, a worker's CUDA/MPS context is only created lazily on its
    first GPU node call, so that first call in every worker pays the
    context-init cost individually. Never raises -- workers without a GPU
    (or without torch) just no-op.
    """
    try:
        import torch
        if torch.cuda.is_available():
            torch.empty(1, device='cuda:0') + 1
        elif getattr(torch.backends, 'mps', None) is not None and torch.backends.mps.is_available():
            torch.empty(1, device='mps') + 1
    except Exception:
        pass
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
                   node_id, node_label, title, label, stdout_path=None):
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
    _stream_file = None

    _fh.enable(file=_real_stderr)   # dump native C stack trace on crash

    # Capture OS-level output from C/C++ extensions into the same spool file as Python output.
    _native = _NativeFDCapture()
    _native.start(stdout_path)
    _configure_native_output()
    _flush_stop = _threading.Event()

    def _flush_native_output_loop():
        while not _flush_stop.wait(0.05):
            _flush_native_output()
            _native.flush()

    _flush_thread = _threading.Thread(target=_flush_native_output_loop,
                                      daemon=True)
    _flush_thread.start()

    # fd 2 now points at the capture file, which is lost if the process dies outright, so
    # keep faulthandler pointed at the inherited stderr.
    _saved_err_fd = _native.saved_fd(2)
    if _saved_err_fd is not None:
        try:
            _fh.enable(file=_os.fdopen(_saved_err_fd, 'w', closefd=False))
        except Exception:
            pass

    if _native._tmp is not None:
        _stream_file = _native._tmp
    _cap_out = _CaptureStream(None, _stream_file)
    _cap_err = _CaptureStream(None, _stream_file)

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

    except BaseException as _e:
        # BaseException catches SystemExit too (some nodes call sys.exit()).
        print(f"[GPI_PROCESS] ERROR in '{title}':'{label}':\n"
              + traceback.format_exc(), flush=True)
        try:
            from gpi.gpu import is_oom_error
            if is_oom_error(_e):
                print(f"[GPI_PROCESS] '{title}':'{label}': GPU ran out of memory -- clearing "
                      f"cached allocator blocks. Consider a smaller batch/array size or a 'cpu' "
                      f"device.", flush=True)
        except Exception:
            pass
        proxy.put(['retcode', -1])

    _flush_stop.set()
    _flush_thread.join(timeout=1.0)
    _flush_native_output()
    _native.flush()
    _captured = _cap_out.getvalue() + _cap_err.getvalue() + _native.stop()
    if _stream_file is not None:
        try:
            _stream_file.flush()
            _stream_file.close()
        except Exception:
            pass
    if _captured.strip() and not stdout_path:
        proxy.put(['stdout', _captured])

    # Force GC so any np.memmap objects opened via _PortDataRef.getData() are
    # closed before this function returns.  The parent process deletes those
    # temp files after future.result() completes; on Windows a file cannot be
    # deleted while it is still mapped, so we must release handles first.
    import gc as _gc
    _gc.collect()

    # Release torch's cached CUDA/MPS allocator blocks back to the driver now
    # rather than leaving them held by this (pooled, reused) worker process
    # indefinitely.  Safety net only -- nodes that need repeated GPU calls
    # without context-multiplication risk (this worker pool has multiple
    # processes) should use GPI_THREAD instead.
    try:
        from gpi.gpu import release_cached_memory
        release_cached_memory()
    except ImportError:
        pass

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
