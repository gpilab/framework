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

import importlib.util
import os as _os
import pickle as _pickle
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
        if isinstance(data, np.ndarray):
            buf = np.frombuffer(data.data, dtype=data.dtype)
            buf.shape = tuple(data.shape)
            return buf
        from gpi.mri_data import MRIData
        if isinstance(data, MRIData):
            return data.clone()
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


# Module-level cache: persists for the lifetime of the worker process.
# Each worker builds its own cache independently.  Second and subsequent
# runs of the same node type skip the importlib overhead entirely.
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
    _fh.enable()   # dump native C stack trace to stderr on crash

    # Limit threading in C extensions to avoid OpenMP/BLAS init crashes
    # in a freshly spawned process on Windows.  These must be set before the
    # first parallel C region runs (i.e. before the node module is imported).
    for _var in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        _os.environ.setdefault(_var, '1')

    proxy = _ListProxy()
    try:
        if module_path not in _module_cache:
            spec = importlib.util.spec_from_file_location('_gpi_node_worker', module_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _module_cache[module_path] = mod
        mod        = _module_cache[module_path]
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
            pass
        try:
            node_class.validate(stub)
        except Exception:
            pass

        retcode = node_class.compute(stub)
        proxy.put(['retcode', retcode])

    except BaseException:
        # BaseException catches SystemExit too (some nodes call sys.exit()).
        print(f"[GPI_PROCESS] ERROR in '{title}':'{label}':\n"
              + traceback.format_exc(), flush=True)
        proxy.put(['retcode', -1])

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
