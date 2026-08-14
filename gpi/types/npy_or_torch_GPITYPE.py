#!/usr/bin/env python

# GPI type extension accepting either a NumPy array or a PyTorch tensor.
# For nodes (e.g. display-only nodes) that just read array data and don't
# care which library produced it -- accept this type, then call to_numpy()
# once to convert internally, rather than special-casing torch everywhere.

import numpy as np
from gpi import GPIDefaultType, osuper

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

if _TORCH_AVAILABLE:
    # Bidirectional dtype map so a node author can specify either numpy or
    # torch dtypes and have it enforced against data of either kind.
    _NP_TO_TORCH = {
        np.dtype(np.float16):   torch.float16,
        np.dtype(np.float32):   torch.float32,
        np.dtype(np.float64):   torch.float64,
        np.dtype(np.complex64):  torch.complex64,
        np.dtype(np.complex128): torch.complex128,
        np.dtype(np.int8):  torch.int8,
        np.dtype(np.int16): torch.int16,
        np.dtype(np.int32): torch.int32,
        np.dtype(np.int64): torch.int64,
        np.dtype(np.uint8): torch.uint8,
        np.dtype(np.bool_): torch.bool,
    }
    _TORCH_TO_NP = {v: k for k, v in _NP_TO_TORCH.items()}
else:
    _NP_TO_TORCH = {}
    _TORCH_TO_NP = {}


def _normalize_dtypes(dtypes):
    """Expand raw numpy/torch dtype specifiers into (np.dtype set, torch.dtype
    set) covering both representations of each entry."""
    np_set, torch_set = set(), set()
    for d in dtypes:
        if _TORCH_AVAILABLE and isinstance(d, torch.dtype):
            torch_set.add(d)
            if d in _TORCH_TO_NP:
                np_set.add(_TORCH_TO_NP[d])
        else:
            nd = np.dtype(d)
            np_set.add(nd)
            if nd in _NP_TO_TORCH:
                torch_set.add(_NP_TO_TORCH[nd])
    return np_set, torch_set


def to_numpy(data):
    """Convert a NumPy array or PyTorch tensor to a plain NumPy array.

    torch.Tensor is moved to CPU first -- callers don't need to care whether
    the upstream node produced a GPU-resident tensor.
    """
    if _TORCH_AVAILABLE and isinstance(data, torch.Tensor):
        return data.detach().cpu().numpy()
    return data


class NPYorTorch(GPIDefaultType):
    """Port type accepting either a NumPy ndarray or a PyTorch tensor.

    Enforcement parms: dtype, ndim, drange, shape. dtype accepts numpy
    and/or torch dtypes interchangeably (e.g. dtype=np.complex64 also
    matches a torch.complex64 tensor) -- see _normalize_dtypes().

    kind='numpy' | 'torch' (optional): auto-converts data to that kind when
    the node calls getData(), regardless of which kind the upstream node
    produced -- so a numpy-only (or torch-only) node doesn't need to branch
    on the incoming type itself. Only takes effect for GPI_THREAD/GPI_APPLOOP
    nodes (nodeAPI.getData()); GPI_PROCESS nodes don't have the port-type
    object available across the process boundary, so call to_numpy() (or
    torch.tensor()) explicitly there instead.
    """

    _np_types = (np.ndarray, np.memmap)

    def __init__(self):
        super(NPYorTorch, self).__init__()
        self._dtype = []
        self._np_dtypes = set()
        self._torch_dtypes = set()
        self._ndim = None
        self._drange = None
        self._shape = None
        self._kind = None

    def _is_supported(self, data):
        if isinstance(data, self._np_types):
            return True
        return _TORCH_AVAILABLE and isinstance(data, torch.Tensor)

    def getDataAttr(self, data):
        if data is None:  # unconnected optional port -- nothing to convert
            return data
        if self._kind == 'numpy':
            return to_numpy(data)
        if self._kind == 'torch' and _TORCH_AVAILABLE and not isinstance(data, torch.Tensor):
            return torch.tensor(data)  # copies -- avoids share-memory/read-only warnings
        return data

    def edgeTip(self, data):
        if self._is_supported(data):
            return str(tuple(data.shape))
        return osuper(NPYorTorch, self).edgeTip(data)

    def toolTip_Data(self, data):
        if self._is_supported(data):
            kind = 'torch' if (_TORCH_AVAILABLE and isinstance(data, torch.Tensor)) else 'numpy'
            return f"{kind}: {data.dtype}\nshape: {tuple(data.shape)}"
        return osuper(NPYorTorch, self).toolTip_Data(data)

    def toolTip_Port(self):
        msg = ['NumPy ndarray or torch.Tensor']
        if self._dtype:
            msg.append(str(self._dtype))
        if self._ndim is not None:
            msg.append(f"ndim: {self._ndim}")
        elif self._drange is not None:
            msg.append(f"drange: {self._drange}")
        elif self._shape is not None:
            msg.append(f"shape: {self._shape}")
        return '\n'.join(msg)

    # Accept upstream connections from NPYarray, TorchTensor, or another
    # NPYorTorch port -- not just an exact-class match like other GPITypes.
    def matchesType(self, type_cls):
        if self.isFreeType(type_cls):
            return True

        if type(type_cls).__name__ not in ('NPYarray', 'TorchTensor', 'NPYorTorch'):
            return False

        if self._dtype and getattr(type_cls, '_dtype', None):
            up_np, up_torch = _normalize_dtypes(type_cls._dtype)
            if not (self._np_dtypes & up_np) and not (self._torch_dtypes & up_torch):
                return False

        if self._ndim is not None and getattr(type_cls, '_ndim', None) is not None:
            if self._ndim != type_cls._ndim:
                return False
        elif self._drange is not None and getattr(type_cls, '_drange', None) is not None:
            if self._drange != type_cls._drange:
                return False
        elif self._shape is not None and getattr(type_cls, '_shape', None) is not None:
            if self._shape != type_cls._shape:
                return False

        return True

    def matchesData(self, data):
        if not self._is_supported(data):
            return False

        if self._dtype:
            if isinstance(data, self._np_types):
                if np.dtype(data.dtype) not in self._np_dtypes:
                    return False
            elif data.dtype not in self._torch_dtypes:
                return False

        if self._ndim is not None:
            if self._ndim != data.ndim:
                return False
        elif self._drange is not None:
            if data.ndim < self._drange[0] or data.ndim > self._drange[1]:
                return False
        elif self._shape is not None and tuple(data.shape) != self._shape:
            return False

        return True

    def set_dtype(self, val):
        """np.dtype | torch.dtype | list of either -- either representation
        matches data of both kinds (see _normalize_dtypes)."""
        vals = val if isinstance(val, list) else [val]
        self._dtype = vals
        self._np_dtypes, self._torch_dtypes = _normalize_dtypes(vals)

    def set_kind(self, val):
        """'numpy' | 'torch' | None -- auto-convert data to this kind on
        getData(), regardless of what the upstream node produced."""
        if val not in (None, 'numpy', 'torch'):
            raise ValueError("'kind' must be 'numpy', 'torch', or None")
        self._kind = val

    def set_ndim(self, val):
        """int | Exact number of dimensions."""
        if not isinstance(val, int):
            raise ValueError("'ndim' requires an int")
        self._ndim = val

    def set_drange(self, val):
        """tuple(int, int) | Inclusive (min_ndim, max_ndim) range."""
        if not isinstance(val, tuple) or len(val) != 2:
            raise ValueError("'drange' requires a 2-tuple of ints")
        self._drange = val

    def set_shape(self, val):
        """tuple(int, ...) | Exact shape."""
        if not isinstance(val, tuple):
            raise ValueError("'shape' requires a tuple")
        self._shape = val
