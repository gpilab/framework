"""
spawn_worker.py — Qt-free worker process for GPI_PROCESS node execution.

This module is intentionally free of Qt imports.  When a spawned child
process unpickles a _PTaskWorker object it imports THIS module (not
functor.py), so gpi/__init__.py runs in lightweight worker mode and
no Qt / widget / parallel initialisation takes place in the child.
"""

import importlib.util
import multiprocessing
import platform
import time
import traceback

import numpy as np

from .dataproxy import DataProxy, MRIData
from .defines import (GPI_PROCESS, GPI_THREAD, GPI_APPLOOP,
                      GPI_PORT_EVENT, GPI_WIDGET_EVENT)

# Mirror the same context choice as functor.py so pickle round-trips cleanly.
if platform.system() == 'Windows':
    _mp_ctx = multiprocessing.get_context('spawn')
else:
    _mp_ctx = multiprocessing.get_context('fork')

_COMPUTE_ERROR = -1   # mirrors ReturnCodes.ComputeError without importing functor


# ---------------------------------------------------------------------------
# Lightweight stub objects that satisfy node.* / self.node.* calls inside
# compute() without any Qt dependency.
# ---------------------------------------------------------------------------

class _ThreadStubProxy:
    """Fake nodeCompute_thread — routes queue ops to the shared Manager list."""

    def __init__(self, proxy):
        self._proxy = proxy

    def execType(self):
        return GPI_PROCESS

    def addToQueue(self, item):
        self._proxy.put(item)


class _NodeStubProxy:
    """Fake node — satisfies self.node.* calls inside compute()."""

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
    """Picklable stand-in for NodeAPI passed as ``self`` to
    ExternalNode.compute() inside a spawned worker process.

    Implements every public NodeAPI method that compute() may call
    without any Qt dependency.
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
        if isinstance(data, MRIData):
            return data.clone()
        return data

    # --- port / widget writes (queued back to parent) ---

    def setData(self, title, data):
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
        buf, shd = DataProxy()._genNDArrayMemmap(shape, dtype, self._node_id, name)
        if shd is not None:
            self.shdmDict[str(id(buf))] = shd.filename
        return buf

    # --- UI setup (called by initUI; no-ops in worker) ---

    def addWidget(self, *_a, **_kw):
        pass

    def addInPort(self, *_a, **_kw):
        pass

    def addOutPort(self, *_a, **_kw):
        pass

    def setPortQueueMax(self, *_a, **_kw):
        pass

    def addMenuItem(self, *_a, **_kw):
        pass

    # --- status / UI (no-ops; no display in subprocess) ---

    def setStatus(self, msg):
        pass

    def setStatus_sys(self, msg):
        pass

    def setDetailLabel(self, newDetailLabel='', elideMode='middle'):
        pass

    def getDetailLabel(self):
        return ''

    def getLabel(self):
        return self.label

    # --- events ---

    def getEvents(self):
        return self._events

    def portEvents(self):
        return self._events.get(GPI_PORT_EVENT, set())

    def widgetEvents(self):
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

    # --- port object access (uncommon in compute; returns None gracefully) ---

    def getInPort(self, pnumORtitle):
        return None

    def getOutPort(self, pnumORtitle):
        return None


# ---------------------------------------------------------------------------
# Picklable worker process
# ---------------------------------------------------------------------------

class _PTaskWorker(_mp_ctx.Process):
    """Spawned worker process that executes ExternalNode.compute() via a
    NodeComputeStub — no Qt objects, no shared GIL with the parent.
    """

    def __init__(self, module_path, parm_settings, port_data, events,
                 node_id, node_label, proxy, title, label):
        super().__init__()
        self._module_path = module_path
        self._parm_settings = parm_settings
        self._port_data = port_data
        self._events = events
        self._node_id = node_id
        self._node_label = node_label
        self._proxy = proxy
        self._title = title
        self._label = label

    def run(self):
        try:
            spec = importlib.util.spec_from_file_location(
                '_gpi_node_worker', self._module_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            node_class = getattr(mod, 'ExternalNode')

            # Collect user-defined helper methods from ExternalNode (e.g. condition,
            # fft2, window2).  These are methods the node defined alongside compute()
            # and calls as self.helper(...).  We merge them into the stub class so
            # they resolve correctly when compute() runs with stub as self.
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

            stub = StubClass(
                self._parm_settings, self._port_data, self._events,
                self._node_id, self._node_label, self._proxy
            )

            # Reproduce the instance state that initUI() and validate() set on the
            # real node in the main process (e.g. self.ndim, self.op).  Both are
            # best-effort: failures are silently ignored so compute() still runs.
            try:
                node_class.initUI(stub)
            except Exception:
                pass
            try:
                node_class.validate(stub)
            except Exception:
                pass
            retcode = node_class.compute(stub)
            self._proxy.put(['retcode', retcode])
        except Exception:
            print(f"PROCESS: '{self._title}':'{self._label}' compute() failed.\n"
                  + traceback.format_exc())
            self._proxy.put(['retcode', _COMPUTE_ERROR])
